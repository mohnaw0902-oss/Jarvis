from __future__ import annotations

import typer

from jarvis.web.api import create_api

app = typer.Typer(help="JARVIS assistant service commands.")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the local JARVIS API."""
    import uvicorn

    uvicorn.run(create_api(), host=host, port=port)
