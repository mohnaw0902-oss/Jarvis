from pathlib import Path

from jarvis.config.settings import Settings
from jarvis.core.application import create_application


async def test_application_starts_with_unconfigured_provider(tmp_path: Path) -> None:
    application = create_application(
        Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    )
    await application.start()
    response = await application.brain.respond("Hello")
    assert "not configured" in response.message
    await application.stop()


async def test_brain_selects_calculator(tmp_path: Path) -> None:
    application = create_application(
        Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    )
    await application.start()
    response = await application.brain.respond("calculate 2 * (3 + 4)")
    assert response.message == "14"
    assert response.tools_used == ["calculator"]
    await application.stop()
