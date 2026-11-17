"""`docqa` command-line interface for offline jobs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from docqa.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]

app = typer.Typer(help="Document Q&A assistant command-line tools.", no_args_is_help=True)


def _setup_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


@app.command()
def version() -> None:
    """Print the package version."""
    from docqa import __version__

    typer.echo(__version__)


@app.command("download-edgar")
def download_edgar(
    resolve: Annotated[
        bool,
        typer.Option(
            "--resolve",
            help="Look up the latest 10-Ks on EDGAR and rewrite the lockfile "
            "(otherwise download exactly what the lockfile lists).",
        ),
    ] = False,
) -> None:
    """Download the locked 10-K filings from SEC EDGAR into RAW_DATA_DIR."""
    from docqa.ingestion import edgar

    _setup_logging()
    log = logging.getLogger("docqa.edgar")
    settings = get_settings()
    if not settings.sec_user_agent_is_set:
        typer.secho(
            "SEC_USER_AGENT is unset or still the placeholder. SEC requires a real contact, "
            'e.g. SEC_USER_AGENT="Your Name you@example.org" in .env.',
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    raw_dir = settings.raw_data_dir
    log.info("User-Agent: %s", settings.sec_user_agent)
    log.info("Rate limit: %.1f requests/second", settings.sec_max_requests_per_second)
    with edgar.EdgarClient(settings.sec_user_agent, settings.sec_max_requests_per_second) as client:
        if resolve:
            companies = edgar.load_companies(settings.companies_file)
            lock = edgar.resolve(
                client, companies, raw_dir, per_company=settings.sec_filings_per_company
            )
            settings.filings_lock_file.write_text(lock.to_json())
            log.info("wrote %s (%d filings)", settings.filings_lock_file, len(lock.filings))
        else:
            if not settings.filings_lock_file.exists():
                typer.secho("No lockfile found; run with --resolve first.", fg=typer.colors.RED)
                raise typer.Exit(2)
            lock = edgar.Lockfile.load(settings.filings_lock_file)
            report = edgar.download(client, lock, raw_dir)
            log.info(
                "%d downloaded, %d already present and verified",
                len(report.downloaded),
                len(report.skipped),
            )
        edgar.write_manifest(lock, raw_dir)
        log.info(
            "%d requests (%d retries), average %.2f requests/second",
            client.stats.requests,
            client.stats.retries,
            client.stats.rate(),
        )


@app.command("ingest-filings")
def ingest_filings_cmd(
    ticker: Annotated[
        list[str] | None, typer.Option("--ticker", "-t", help="Only these tickers (repeatable).")
    ] = None,
    force: Annotated[bool, typer.Option(help="Re-ingest filings that are already ready.")] = False,
) -> None:
    """Parse, chunk, embed and index the downloaded 10-Ks into the shared filings library."""
    import asyncio

    from docqa.db.session import create_engine, create_sessionmaker
    from docqa.ingestion.edgar import Lockfile
    from docqa.ingestion.embedding import get_embedder
    from docqa.ingestion.library import ingest_filings

    _setup_logging()
    settings = get_settings()
    lock = Lockfile.load(settings.filings_lock_file)

    async def run() -> None:
        engine = create_engine(settings)
        try:
            outcomes = await ingest_filings(
                create_sessionmaker(engine),
                settings,
                get_embedder(settings),
                lock,
                tickers={t.upper() for t in ticker} if ticker else None,
                force=force,
            )
        finally:
            await engine.dispose()
        for o in outcomes:
            line = f"{o.entry.ticker:5s} FY{o.entry.fiscal_year}  {o.status}"
            if o.result:
                line += (
                    f"  {o.result.pages} pages, {o.result.chunks} chunks, "
                    f"{o.result.seconds:.0f}s, {o.result.pages_per_minute:.0f} pages/min"
                )
            typer.echo(line)
        if any(o.status == "missing" for o in outcomes):
            raise typer.Exit(1)

    asyncio.run(run())


@app.command("check-llm")
def check_llm() -> None:
    """Send one tiny completion to the answer and judge models and print their rate limits."""
    from docqa.generation.llm import answer_llm, judge_llm, probe

    settings = get_settings()
    failed = False
    for role, spec in (("answer", answer_llm(settings)), ("judge", judge_llm(settings))):
        typer.echo(f"{role}: {spec.litellm_model}")
        result = probe(spec)
        if result.error:
            failed = True
            typer.secho(f"  FAILED: {result.error}", fg=typer.colors.RED)
            continue
        typer.secho(f"  ok ({result.latency_ms} ms): {result.reply!r}", fg=typer.colors.GREEN)
        for name, value in sorted(result.rate_limits.items()):
            typer.echo(f"  {name}: {value}")
    if failed:
        raise typer.Exit(1)


@app.command("reset-db")
def reset_db(
    yes: Annotated[bool, typer.Option("--yes", help="Confirm dropping the database.")] = False,
) -> None:
    """Drop and recreate DATABASE_URL's database, then apply migrations (APP_ENV=test only).

    Used to give the end-to-end tests a clean database on every run.
    """
    import asyncio

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import make_url

    from docqa.db.admin import recreate_database

    settings = get_settings()
    if settings.app_env != "test":
        typer.secho("reset-db only runs with APP_ENV=test.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    if not yes:
        typer.secho("Pass --yes to drop the database.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    asyncio.run(recreate_database(settings.database_url))
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["db_url"] = settings.database_url
    command.upgrade(cfg, "head")
    typer.echo(f"Recreated and migrated database {make_url(settings.database_url).database}")


if __name__ == "__main__":
    app()
