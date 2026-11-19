"""`docqa eval ...` commands. Only `generate` calls an LLM."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from docqa.config import get_settings

eval_app = typer.Typer(help="Evaluation: dataset checks, retrieval, ablations, generation.")

DatasetOption = Annotated[Path | None, typer.Option(help="Dataset JSONL (default: qa_v1).")]
PlanOption = Annotated[
    Path | None,
    typer.Option(help="Plan YAML in evals/configs (default: ablations.yaml; tuning.yaml for 5b)."),
]
RetrievalConfigOption = Annotated[
    Path | None,
    typer.Option(help="YAML with a `retrieval` mapping (default: the ablations base config)."),
]


def _plan(path: Path | None) -> Any:
    from docqa.evals.configs import CONFIG_DIR, load_ablations

    return load_ablations(path or CONFIG_DIR / "ablations.yaml")


def _plan_dataset(plan: Any, dataset: Path | None) -> Any:
    """The plan's pinned dataset (tuning runs on the dev set only); refuse any other."""
    from docqa.evals.dataset import DATASET_DIR

    if plan.dataset is None:
        return _dataset(dataset)
    pinned = DATASET_DIR / plan.dataset
    if dataset is not None and dataset.resolve() != pinned.resolve():
        typer.secho(
            f"{plan.name} is pinned to {plan.dataset}; tuning must not see other datasets.",
            fg="red",
            err=True,
        )
        raise typer.Exit(2)
    return _dataset(pinned)


def _setup_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    for noisy in ("httpx", "LiteLLM", "litellm"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _dataset(path: Path | None) -> Any:
    from docqa.evals.dataset import DEFAULT_DATASET, load_dataset

    return load_dataset(path or DEFAULT_DATASET)


@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    from docqa.db.session import create_engine, create_sessionmaker

    engine = create_engine(get_settings())
    try:
        async with create_sessionmaker(engine)() as db:
            yield db
    finally:
        await engine.dispose()


def _run[T](fn: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(fn())


def _echo_report(paths: tuple[Path, Path]) -> None:
    typer.echo(f"Report: {paths[0]}\n        {paths[1]}")


@eval_app.command("index")
def index(
    force: Annotated[bool, typer.Option(help="Rebuild variants that already exist.")] = False,
    plan_file: PlanOption = None,
) -> None:
    """Build the chunk variants listed in an eval plan (default ablations.yaml) into the library."""
    from docqa.db.session import create_engine, create_sessionmaker
    from docqa.evals.configs import load_ablations
    from docqa.ingestion.edgar import Lockfile
    from docqa.ingestion.embedding import get_embedder
    from docqa.ingestion.library import build_library_index

    _setup_logging()
    settings = get_settings()
    plan = load_ablations(plan_file) if plan_file else load_ablations()

    async def run() -> None:
        engine = create_engine(settings)
        try:
            outcomes = await build_library_index(
                create_sessionmaker(engine),
                get_embedder(settings),
                Lockfile.load(settings.filings_lock_file),
                settings,
                plan.indexes,
                force=force,
            )
        finally:
            await engine.dispose()
        for o in outcomes:
            typer.echo(
                f"{o.entry.ticker:5s} FY{o.entry.fiscal_year}  {o.config_key:18s} "
                f"{o.status:8s} {o.chunks} chunks"
            )
        if any(o.status == "missing" for o in outcomes):
            typer.secho("Some filings are not ingested; run `make ingest-filings` first.", err=True)
            raise typer.Exit(1)

    _run(run)


@eval_app.command("verify")
def verify(dataset: DatasetOption = None) -> None:
    """Check every source quote against the parsed filings, and that it maps to gold chunks."""
    from docqa.evals.configs import load_ablations
    from docqa.evals.dataset import load_filing_texts, verify_quotes
    from docqa.evals.retrieval_eval import GoldIndex, library_documents
    from docqa.ingestion.edgar import Lockfile

    settings = get_settings()
    ds = _dataset(dataset)
    needed = {s.doc for i in ds.items for s in i.sources}
    texts = load_filing_texts(
        settings.raw_data_dir, Lockfile.load(settings.filings_lock_file), needed
    )
    missing_docs = needed - set(texts)
    if missing_docs:
        typer.secho(
            f"Filings not downloaded: {sorted(missing_docs)}; run `make download`.", fg="red"
        )
        raise typer.Exit(1)

    checks = verify_quotes(ds.items, texts)
    bad = [c for c in checks if not c.ok]
    for c in bad:
        where = f" (found in: {', '.join(c.found_elsewhere)})" if c.found_elsewhere else ""
        typer.secho(
            f"{c.item_id}: quote not in {c.source.doc} Item {c.source.section}{where}\n"
            f"    {c.source.quote!r}",
            fg="red",
        )
    typer.echo(
        f"{ds.version}: {len(ds.items)} questions, {len(checks) - len(bad)}/{len(checks)} "
        "source quotes found in their filing and Item."
    )

    async def gold_coverage() -> list[str]:
        problems = []
        async with _session() as db:
            documents = await library_documents(db)
            for config in load_ablations().indexes:
                gold = GoldIndex(documents, config.key)
                counts = [len(g) for item in ds.answerable for g in await gold.for_item(db, item)]
                empty = sum(1 for n in counts if n == 0)
                typer.echo(
                    f"  {config.key:18s} gold chunks per source: "
                    f"min {min(counts)}, max {max(counts)}; sources without a gold chunk: {empty}"
                )
                if empty:
                    problems.append(config.key)
        return problems

    try:
        problems = _run(gold_coverage)
    except OSError as exc:  # database not running: quotes are still verified
        typer.secho(f"Skipped gold-chunk check (database unavailable: {exc})", fg="yellow")
        problems = []
    if bad or problems:
        raise typer.Exit(1)


@eval_app.command("xbrl")
def xbrl(dataset: DatasetOption = None) -> None:
    """Compare numeric gold answers with SEC XBRL companyfacts (cached in RAW_DATA_DIR/xbrl)."""
    from docqa.evals.reports import table, write_report
    from docqa.evals.xbrl_check import Status, cached_companyfacts, check_dataset
    from docqa.ingestion.edgar import EdgarClient, Lockfile

    _setup_logging()
    settings = get_settings()
    if not settings.sec_user_agent_is_set:
        typer.secho("SEC_USER_AGENT is unset or still the placeholder; set it in .env.", fg="red")
        raise typer.Exit(2)
    ds = _dataset(dataset)
    with EdgarClient(settings.sec_user_agent, settings.sec_max_requests_per_second) as client:
        results = check_dataset(
            ds,
            Lockfile.load(settings.filings_lock_file),
            cached_companyfacts(client, settings.raw_data_dir / "xbrl"),
        )
    counts = {s.value: sum(1 for r in results if r.status == s) for s in Status}
    attention = [r for r in results if r.needs_attention]
    rows = [
        [
            r.item_id,
            r.fact.company,
            f"FY{r.fact.fiscal_year}",
            f"{r.fact.value:,g} {r.fact.unit}",
            r.fact.xbrl_concept or "—",
            f"{r.xbrl.value:,.0f}"
            if r.xbrl and abs(r.xbrl.value) >= 1000
            else (f"{r.xbrl.value:g}" if r.xbrl else "—"),
            r.status.value,
            (r.detail or r.fact.xbrl_note or "").replace("|", "/"),
        ]
        for r in results
    ]
    markdown = "\n".join(
        [
            "# XBRL cross-check",
            "",
            f"{len(results)} numeric gold values: "
            + ", ".join(f"{n} {s}" for s, n in counts.items() if n)
            + f". Unexplained: {len(attention)}.",
            "",
            table(
                ["Question", "Company", "Year", "Gold", "Concept", "XBRL", "Status", "Note"],
                rows,
            ),
            "",
        ]
    )
    data = {
        "counts": counts,
        "unexplained": [r.item_id for r in attention],
        "results": [
            {
                "id": r.item_id,
                "fact": r.fact.model_dump(),
                "status": r.status.value,
                "xbrl": None if r.xbrl is None else r.xbrl.__dict__,
                "detail": r.detail,
            }
            for r in results
        ],
    }
    _echo_report(write_report("xbrl", ds, data, markdown))
    typer.echo(", ".join(f"{n} {s}" for s, n in counts.items() if n))
    for r in attention:
        got = f"XBRL {r.xbrl.value:,g}" if r.xbrl else r.detail
        typer.secho(
            f"  {r.item_id} {r.fact.company} FY{r.fact.fiscal_year}: "
            f"gold {r.fact.value:,g} {r.fact.unit} vs {got}",
            fg="red",
        )
    if attention:
        raise typer.Exit(1)


def _retriever() -> Any:
    from docqa.ingestion.embedding import get_embedder
    from docqa.retrieval.rerank import get_reranker
    from docqa.retrieval.retriever import RetrievalConfig, Retriever

    settings = get_settings()
    return Retriever(
        get_embedder(settings), get_reranker(settings), RetrievalConfig.from_settings(settings)
    )


@eval_app.command("retrieval")
def retrieval(dataset: DatasetOption = None, config_file: RetrievalConfigOption = None) -> None:
    """Recall@5/10 and MRR for one retrieval config, overall and per category."""
    from docqa.evals.ablations import render_retrieval, run_summary
    from docqa.evals.configs import load_ablations
    from docqa.evals.reports import write_report
    from docqa.evals.retrieval_eval import (
        GoldIndex,
        ensure_eval_workspace,
        evaluate_retrieval,
        library_documents,
    )

    _setup_logging()
    ds = _dataset(dataset)
    config = load_ablations().base
    if config_file is not None:
        from docqa.evals.configs import retrieval_config

        values = yaml.safe_load(config_file.read_text())["retrieval"]
        config = retrieval_config(values | {"top_n": max(values.get("top_n", 0), 10)})

    async def run() -> Any:
        async with _session() as db:
            workspace_id = await ensure_eval_workspace(db)
            gold = GoldIndex(await library_documents(db), config.index_config)
            return await evaluate_retrieval(db, _retriever(), workspace_id, ds, config, gold)

    result = _run(run)
    markdown = render_retrieval(result)
    _echo_report(write_report("retrieval", ds, run_summary(result), markdown))
    typer.echo(markdown)


@eval_app.command("ablations")
def ablations(dataset: DatasetOption = None, plan_file: PlanOption = None) -> None:
    """Run every retrieval variant in an eval plan (default ablations.yaml; no LLM calls)."""
    from docqa.evals.ablations import (
        GoldCache,
        ablations_summary,
        render_ablations,
        run_ablations,
    )
    from docqa.evals.reports import write_report
    from docqa.evals.retrieval_eval import ensure_eval_workspace, library_documents

    _setup_logging()
    plan = _plan(plan_file)
    ds = _plan_dataset(plan, dataset)

    async def run() -> Any:
        async with _session() as db:
            workspace_id = await ensure_eval_workspace(db)
            gold = GoldCache(await library_documents(db))
            return await run_ablations(db, _retriever(), workspace_id, ds, plan, gold)

    runs = _run(run)
    heading = "Retrieval ablations" if plan.dataset is None else f"Retrieval tuning ({plan.name})"
    markdown = render_ablations(runs, plan.titles, heading)
    _echo_report(write_report(plan.name, ds, ablations_summary(runs), markdown))
    typer.echo(markdown)


def _generation_setup(dataset: Path | None) -> Any:
    """Dataset, config, model specs (judge != answer enforced), run hash, checkpoint."""
    from docqa.evals.configs import load_generation_config
    from docqa.evals.generation_eval import Checkpoint, checkpoint_path, run_hash
    from docqa.evals.judge import SameModelError, assert_distinct_models
    from docqa.generation.llm import answer_llm, judge_llm

    settings = get_settings()
    ds = _dataset(dataset)
    config = load_generation_config()
    answer, judge = answer_llm(settings), judge_llm(settings)
    try:
        assert_distinct_models(answer, judge)
    except SameModelError as exc:
        typer.secho(str(exc), fg="red", err=True)
        raise typer.Exit(2) from exc
    hash_ = run_hash(config, answer, judge)
    return ds, config, answer, judge, hash_, Checkpoint(checkpoint_path(ds, config, hash_))


def _write_generation_report(
    ds: Any, checkpoint: Any, config: Any, hash_: str, answer: Any, judge: Any
) -> None:
    from docqa.evals.generation_eval import generation_report
    from docqa.evals.reports import write_report

    data, markdown = generation_report(
        ds, checkpoint, config, hash_, answer.litellm_model, judge.litellm_model
    )
    _echo_report(write_report("generation", ds, data, markdown))
    typer.echo(markdown.split("## By category")[0])


@eval_app.command("generate")
def generate(
    dataset: DatasetOption = None,
    report_only: Annotated[
        bool, typer.Option("--report-only", help="Score the checkpoint without calling an LLM.")
    ] = False,
) -> None:
    """Answer and judge every question with the final config; resumable and budgeted."""
    from docqa.evals.budget import Ledger, Limits, ModelBudget
    from docqa.evals.client import BudgetedClient
    from docqa.evals.generation_eval import Generator, is_complete, run_generation
    from docqa.evals.retrieval_eval import GoldIndex, ensure_eval_workspace, library_documents

    _setup_logging()
    settings = get_settings()
    ds, config, answer, judge, hash_, checkpoint = _generation_setup(dataset)
    rel = checkpoint.path.relative_to(checkpoint.path.parents[2])
    typer.echo(f"Answer model {answer.litellm_model}, judge {judge.litellm_model}")
    typer.echo(f"Run {hash_}; checkpoint {rel}")
    if report_only:
        _write_generation_report(ds, checkpoint, config, hash_, answer, judge)
        return

    ledger, limits = Ledger(), Limits.from_settings(settings)
    budgets = {
        s.litellm_model: ModelBudget(s.litellm_model, limits, ledger) for s in (answer, judge)
    }
    for model, budget in budgets.items():
        requests, tokens = budget.remaining()
        typer.echo(f"  {model}: {requests} requests and {tokens:,} tokens left today")
    done_before = sum(1 for i in ds.items if is_complete(checkpoint.get(f"{i.id}:{hash_}")))
    typer.echo(f"{done_before}/{len(ds.items)} questions already complete")

    def show(record: dict[str, Any]) -> None:
        stage = "judged" if record.get("judge") else "answered"
        detail = (
            "refused" + (" (gate)" if record["gate_refused"] else "")
            if record["refused"]
            else (record["judge"]["verdict"] if record.get("judge") else "awaiting judge")
        )
        typer.echo(f"  {record['item_id']}: {stage}, {detail}")

    async def run() -> Any:
        async with _session() as db:
            workspace_id = await ensure_eval_workspace(db)
            gold = GoldIndex(await library_documents(db), config.retrieval.index_config)
            gen = Generator(
                db=db,
                retriever=_retriever(),
                config=config,
                client=BudgetedClient(budgets),
                answer_spec=answer,
                judge_spec=judge,
                workspace_id=workspace_id,
                gold=gold,
                hash=hash_,
            )
            try:
                return await run_generation(gen, ds.items, checkpoint, show)
            except KeyboardInterrupt:  # pragma: no cover - interactive
                return None

    outcome = _run(run)
    _write_generation_report(ds, checkpoint, config, hash_, answer, judge)
    if outcome is None:
        typer.secho(
            "Interrupted. Progress is saved; run `make eval-generate` to resume.", fg="yellow"
        )
        return
    if outcome.finished:
        typer.secho(f"All {outcome.total} questions answered and judged.", fg="green")
        return
    for model, reason in outcome.stopped.items():
        typer.secho(f"Stopped {model}: {reason}", fg="yellow")
    typer.secho(
        f"{outcome.completed}/{outcome.total} questions complete. Today's budget is used up; "
        "resume tomorrow (after 00:00 UTC) with `make eval-generate`.",
        fg="yellow",
    )


def _human_check_path(ds: Any, hash_: str) -> Path:
    from docqa.evals.human_check import HUMAN_CHECK_DIR

    return HUMAN_CHECK_DIR / f"{ds.name}-{hash_}.md"


@eval_app.command("human-export")
def human_export(
    dataset: DatasetOption = None,
    n: Annotated[int, typer.Option(help="Number of judged answers to export.")] = 20,
    force: Annotated[bool, typer.Option(help="Overwrite even if boxes are marked.")] = False,
) -> None:
    """Export judged answers to markdown for a manual agree/disagree check of the judge."""
    from docqa.evals.human_check import export_markdown, parse_marks, select_records

    ds, _, _, _, hash_, checkpoint = _generation_setup(dataset)
    path = _human_check_path(ds, hash_)
    if (
        path.exists()
        and not force
        and any(m.agree is not None for m in parse_marks(path.read_text()))
    ):
        typer.secho(f"{path} already has marks; pass --force to overwrite.", fg="red", err=True)
        raise typer.Exit(1)
    records = [r for r in checkpoint.records.values() if r.get("run_hash") == hash_]
    picked = select_records(records, n)
    if len(picked) < n:
        typer.secho(f"Only {len(picked)} judged answers so far (wanted {n}).", fg="yellow")
    if not picked:
        raise typer.Exit(1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(export_markdown(picked, ds.version, hash_))
    typer.echo(f"Wrote {len(picked)} answers to {path}")


@eval_app.command("agreement")
def agreement_cmd(
    dataset: DatasetOption = None,
    file: Annotated[Path | None, typer.Option(help="Marked human-check file.")] = None,
) -> None:
    """Judge-human agreement rate and Cohen's kappa from a marked human-check file."""
    from docqa.evals.human_check import agreement, parse_marks
    from docqa.evals.reports import pct, table, write_report

    ds, _, _, judge, hash_, _ = _generation_setup(dataset)
    path = file or _human_check_path(ds, hash_)
    if not path.exists():
        typer.secho(f"{path} not found; run `make eval-human` first.", fg="red", err=True)
        raise typer.Exit(1)
    marks = parse_marks(path.read_text())
    result = agreement(marks)
    if not result.marked:
        typer.secho("No answers are marked yet.", fg="red", err=True)
        raise typer.Exit(1)
    confusion = result.confusion.items()
    kappa = "undefined" if result.kappa is None else f"{result.kappa:.2f}"
    markdown = "\n".join(
        [
            "# Judge-human agreement",
            "",
            f"Judge `{judge.litellm_model}`, run `{hash_}`, file `{path.name}`.",
            "",
            table(
                ["Marked", "Agreed", "Agreement", "Cohen's kappa", "Unmarked"],
                [[result.marked, result.agreed, pct(result.rate), kappa,
                  len(result.unmarked)]],
            ),
            "",
            table(["Judge / human", "Count"], [[k, v] for k, v in sorted(confusion)]),
            "",
        ]
    )  # fmt: skip
    data = {
        "file": path.name,
        "run_hash": hash_,
        "judge_model": judge.litellm_model,
        "marked": result.marked,
        "agreed": result.agreed,
        "agreement": result.rate,
        "kappa": result.kappa,
        "unmarked": result.unmarked,
        "confusion": result.confusion,
    }
    _echo_report(write_report("human-agreement", ds, data, markdown))
    typer.echo(markdown)


@eval_app.command("compare")
def compare(
    before_retrieval: Annotated[Path, typer.Option(help="Baseline retrieval report JSON.")],
    after_retrieval: Annotated[Path, typer.Option(help="Final retrieval report JSON.")],
    before_generation: Annotated[
        Path | None, typer.Option(help="Baseline generation report JSON.")
    ] = None,
    after_generation: Annotated[
        Path | None, typer.Option(help="Final generation report JSON.")
    ] = None,
    tuning: Annotated[
        str | None, typer.Option(help="Tuning report name, cited in the text.")
    ] = None,
    dataset: DatasetOption = None,
) -> None:
    """Before/after report from saved retrieval (and generation) report JSONs. No LLM calls."""
    import json

    from docqa.evals.compare import render_comparison
    from docqa.evals.reports import write_report

    def load(path: Path) -> Any:
        return json.loads(path.read_text())

    ds = _dataset(dataset)
    retrieval_pair = (load(before_retrieval), load(after_retrieval))
    generation_pair = (
        (load(before_generation), load(after_generation))
        if before_generation and after_generation
        else None
    )
    for report in (*retrieval_pair, *(generation_pair or ())):
        if report.get("dataset") != ds.version:
            typer.secho(
                f"Report is for {report.get('dataset')}, not {ds.version}.", fg="red", err=True
            )
            raise typer.Exit(1)
    markdown = render_comparison(retrieval_pair, generation_pair, tuning)
    data = {
        "inputs": {
            "before_retrieval": before_retrieval.name,
            "after_retrieval": after_retrieval.name,
            "before_generation": before_generation.name if before_generation else None,
            "after_generation": after_generation.name if after_generation else None,
        }
    }
    _echo_report(write_report("before-after", ds, data, markdown))
    typer.echo(markdown)
