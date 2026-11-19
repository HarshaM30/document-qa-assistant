"""Shared helpers for the benchmark scripts: machine specs and benchmarks/results.md sections.

Each script owns one section of results.md, delimited by HTML comments
(`<!-- loadtest:start -->` ... `<!-- loadtest:end -->`), and rewrites only that section.
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RESULTS = Path(__file__).resolve().parent / "results.md"


def _run(*cmd: str) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def machine_specs() -> dict[str, str]:
    chip = _run("sysctl", "-n", "machdep.cpu.brand_string") or platform.processor()
    cores = _run("sysctl", "-n", "hw.ncpu")
    mem = _run("sysctl", "-n", "hw.memsize")
    os_version = _run("sw_vers", "-productVersion")
    docker = _run("docker", "info", "--format", "{{json .}}")
    docker_mem = ""
    if docker:
        try:
            info = json.loads(docker)
            docker_mem = f"{int(info['MemTotal']) / 2**30:.1f} GiB, {info['NCPU']} CPUs"
        except (ValueError, KeyError):
            pass
    return {
        "chip": f"{chip} ({cores} cores)" if cores else chip,
        "ram": f"{int(mem) / 2**30:.0f} GiB" if mem.isdigit() else "unknown",
        "os": f"macOS {os_version}" if os_version else platform.platform(),
        "docker": docker_mem or "unknown",
        "python": platform.python_version(),
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
    }


def specs_line(m: dict[str, str]) -> str:
    return (
        f"{m['chip']}, {m['ram']} RAM, {m['os']}; Docker Desktop VM {m['docker']} "
        f"(Postgres and Redis only); Python {m['python']}; run {m['date']}."
    )


def write_section(name: str, body: str) -> None:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    content = RESULTS.read_text()
    block = f"{start}\n{body.rstrip()}\n{end}"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(content):
        raise SystemExit(f"{RESULTS.name} has no {start} ... {end} section")
    RESULTS.write_text(pattern.sub(lambda _: block, content))


def _ms(value: str) -> str:
    try:
        return f"{float(value):,.0f}"
    except ValueError:
        return value or "-"


def loadtest_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"Machine: {specs_line(summary['machine'])}",
        "",
        f"Corpus: {summary['corpus']}. Fake LLM streaming one word every "
        f"{summary['token_delay_ms']} ms; {summary['duration']} per row; think time 1-3 s "
        "per user; one uvicorn process. Latencies in ms.",
        "",
        "| Users | Request | Count | p50 | p95 | p99 | Errors | Req/s |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    order = [
        "/auth/login",
        "/workspaces/:id/documents",
        "/workspaces/:id/ask (headers)",
        "ask: first token",
        "ask: full answer",
    ]
    for level in summary["levels"]:
        rows = {r["Name"]: r for r in level["rows"]}
        for name in order:
            r = rows.get(name)
            if r is None:
                continue
            count, failures = int(r["Request Count"]), int(r["Failure Count"])
            rate = f"{failures / count:.1%}" if count else "-"
            lines.append(
                f"| {level['users']} | {name} | {count} | {_ms(r['50%'])} | {_ms(r['95%'])} "
                f"| {_ms(r['99%'])} | {rate} | {float(r['Requests/s']):.1f} |"
            )
    lines += [
        "",
        "| Users | All HTTP requests | Error rate | API peak RSS |",
        "|---:|---:|---:|---:|",
    ]
    for level in summary["levels"]:
        http = [r for r in level["rows"] if r["Type"] in ("GET", "POST")]
        count = sum(int(r["Request Count"]) for r in http)
        failures = sum(int(r["Failure Count"]) for r in http)
        sse = {r["Name"]: r for r in level["rows"]}.get("ask: full answer")
        failures += int(sse["Failure Count"]) if sse else 0
        rate = f"{failures / count:.2%}" if count else "-"
        lines.append(f"| {level['users']} | {count} | {rate} | {level['api_peak_rss_mb']:.0f} MB |")
    logs = summary["logs"]
    lines += [
        "",
        f"Logs during the run: {logs['error_records']} ERROR/CRITICAL records, "
        f"{logs['tracebacks']} tracebacks (API and worker).",
    ]
    return "\n".join(lines)


def ingest_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"Machine: {specs_line(summary['machine'])}",
        "",
        "| Set | Documents | Pages | Worker concurrency | Wall time | Pages/min | "
        "Chunks | Worker peak RSS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary["runs"]:
        lines.append(
            f"| {r['set']} | {r['documents']} | {r['pages']} | {r['concurrency']} "
            f"| {r['seconds']:.0f} s | {r['pages_per_minute']:.0f} | {r['chunks']} "
            f"| {r['peak_rss_mb']:.0f} MB |"
        )
    stages = summary.get("stage_share")
    if stages:
        parts = ", ".join(f"{k} {v:.0%}" for k, v in stages.items())
        lines += ["", f"Share of job time by stage (all runs): {parts}."]
    return "\n".join(lines)
