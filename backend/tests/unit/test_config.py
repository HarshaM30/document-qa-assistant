from __future__ import annotations

from pathlib import Path

from docqa.config import REPO_ROOT, SEC_USER_AGENT_PLACEHOLDER, Settings


def test_relative_paths_resolve_against_repo_root() -> None:
    s = Settings(upload_dir=Path("data/uploads"))
    assert s.upload_dir == REPO_ROOT / "data" / "uploads"
    assert (REPO_ROOT / "backend" / "pyproject.toml").exists()


def test_absolute_paths_kept() -> None:
    assert Settings(upload_dir=Path("/tmp/x")).upload_dir == Path("/tmp/x")


def test_sec_user_agent_placeholder_detected() -> None:
    assert not Settings(sec_user_agent="").sec_user_agent_is_set
    assert not Settings(sec_user_agent=SEC_USER_AGENT_PLACEHOLDER).sec_user_agent_is_set
    assert Settings(sec_user_agent="Jane Doe jane@university.edu").sec_user_agent_is_set
