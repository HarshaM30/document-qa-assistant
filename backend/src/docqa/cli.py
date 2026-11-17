"""`docqa` command-line interface for offline jobs."""

from __future__ import annotations

import typer

app = typer.Typer(help="Document Q&A assistant command-line tools.", no_args_is_help=True)


@app.command()
def version() -> None:
    """Print the package version."""
    from docqa import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()
