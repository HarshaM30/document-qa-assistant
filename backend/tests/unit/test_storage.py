from __future__ import annotations

from docqa.config import Settings
from docqa.storage import safe_display_name
from docqa.worker.tasks import retry_delay_seconds


def test_safe_display_name() -> None:
    assert safe_display_name("../../etc/passwd.pdf") == "passwd.pdf"
    assert safe_display_name("C:\\Users\\me\\Annual Report.pdf") == "Annual Report.pdf"
    assert safe_display_name("bad\x00name\n.pdf") == "badname.pdf"
    assert safe_display_name("") == "document.pdf"
    assert len(safe_display_name("a" * 500 + ".pdf")) == 200


def test_retry_backoff_is_exponential() -> None:
    settings = Settings(ingest_retry_base_delay_seconds=5)
    assert [retry_delay_seconds(settings, n) for n in (1, 2, 3)] == [5, 10, 20]
