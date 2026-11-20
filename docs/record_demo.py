"""`make demo-gif`: record docs/demo.gif from a scripted browser session.

Steps:
1. Clone the dev database (with the ingested filings library) into a throwaway
   `docqa_demo` database, as the load test does, so the demo asks real questions over
   the 15 filings without touching dev data.
2. Start the API on port 8003 with the answer model from .env (DEMO_LLM_PROVIDER=fake
   records with the deterministic fake model instead, with no LLM calls).
3. Warm up off camera: one question loads the embedding and reranker models, so the
   recording doesn't open on a cold start.
4. Build the frontend against that API, serve it on port 4174, and run
   frontend/e2e/demo.record.ts with Playwright's video recording on.
5. Convert the video to an optimized GIF with ffmpeg (two-pass palette).

Needs `make deps`, the filings library (`make ingest-filings`), ffmpeg, and Playwright's
Chromium (`npx --prefix frontend playwright install chromium`). With the real model the
run makes about four answer-model requests.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from docqa.config import Settings

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "benchmarks"))
from loadtest import prepare_database  # noqa: E402

BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"
OUT = REPO / "docs" / "out"
GIF = REPO / "docs" / "demo.gif"

API_PORT = 8003
WEB_PORT = 4174
DEMO_DB = "docqa_demo"
REDIS_DB = 4
GIF_FPS = os.environ.get("DEMO_GIF_FPS", "10")
GIF_WIDTH = os.environ.get("DEMO_GIF_WIDTH", "960")
WARMUP_QUESTION = "What was Tesla's total revenue in fiscal 2025?"


def _wait_for(url: str, proc: subprocess.Popen[bytes], what: str, timeout: float = 180) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"the {what} exited during startup; see {OUT}")
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"the {what} did not start")


def warm_up(api: str) -> None:
    """Load the models off camera by asking one question as a throwaway user."""
    headers = {"X-Requested-With": "fetch"}
    with httpx.Client(base_url=api, headers=headers, timeout=180) as client:
        creds = {"email": "warmup@example.org", "password": "warm-up password"}
        client.post("/auth/signup", json=creds).raise_for_status()
        ws = client.post("/workspaces", json={"name": "Warm-up"}).json()["id"]
        client.post(f"/workspaces/{ws}/library", json={}).raise_for_status()
        with client.stream(
            "POST", f"/workspaces/{ws}/ask", json={"question": WARMUP_QUESTION}
        ) as r:
            r.raise_for_status()
            for _ in r.iter_bytes():
                pass


def to_gif(video: Path) -> None:
    palette = OUT / "palette.png"
    filters = f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos"
    use = "paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vf", f"{filters},palettegen=stats_mode=diff", str(palette)],
        check=True,
    )  # fmt: skip
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(palette),
         "-lavfi", f"{filters} [x]; [x][1:v] {use}", str(GIF)],
        check=True,
    )  # fmt: skip


def main() -> int:
    if not shutil.which("ffmpeg"):
        print("ffmpeg is required (brew install ffmpeg).", file=sys.stderr)
        return 1
    settings = Settings()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    db_url, filings = asyncio.run(prepare_database(settings, DEMO_DB))
    if not filings:
        print("The demo needs the filings library: run `make ingest-filings`.", file=sys.stderr)
        return 1

    api_origin = f"http://localhost:{API_PORT}"
    web_origin = f"http://localhost:{WEB_PORT}"
    redis = urlsplit(settings.test_redis_url)._replace(path=f"/{REDIS_DB}").geturl()
    env = os.environ | {
        "DATABASE_URL": db_url,
        "REDIS_URL": redis,
        "FRONTEND_ORIGIN": web_origin,
        "SESSION_COOKIE_SECURE": "false",
        "LOG_LEVEL": "WARNING",
        "UPLOAD_DIR": str(OUT / "uploads"),
    }
    if os.environ.get("DEMO_LLM_PROVIDER"):
        env["LLM_PROVIDER"] = os.environ["DEMO_LLM_PROVIDER"]
    provider = env.get("LLM_PROVIDER", settings.llm_provider)
    print(f"Recording with LLM provider {provider!r} over {filings} filings", flush=True)

    from redis import Redis

    Redis.from_url(redis).flushdb()

    with (OUT / "api.log").open("wb") as alog, (OUT / "web.log").open("wb") as wlog:
        api = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "docqa.main:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(API_PORT), "--no-access-log"],
            cwd=BACKEND, env=env, stdout=alog, stderr=subprocess.STDOUT,
        )  # fmt: skip
        web: subprocess.Popen[bytes] | None = None
        try:
            _wait_for(f"{api_origin}/health", api, "API")
            print("Warming up the models ...", flush=True)
            warm_up(api_origin)

            print("Building the frontend ...", flush=True)
            subprocess.run(
                ["npm", "run", "build"], cwd=FRONTEND, check=True, stdout=subprocess.DEVNULL,
                env=os.environ | {"VITE_API_BASE_URL": api_origin},
            )  # fmt: skip
            web = subprocess.Popen(
                ["npx", "vite", "preview", "--port", str(WEB_PORT), "--strictPort"],
                cwd=FRONTEND, stdout=wlog, stderr=subprocess.STDOUT,
            )  # fmt: skip
            _wait_for(web_origin, web, "frontend")

            print("Recording ...", flush=True)
            demo_env = {"DEMO_BASE_URL": web_origin, "DEMO_OUTPUT_DIR": str(OUT / "video")}
            subprocess.run(
                ["npx", "playwright", "test", "-c", "e2e/demo.config.ts"],
                cwd=FRONTEND, check=True, env=os.environ | demo_env,
            )  # fmt: skip
        finally:
            for proc in (web, api):
                if proc is not None:
                    proc.send_signal(signal.SIGTERM)
            for proc in (web, api):
                if proc is not None:
                    try:
                        proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        proc.kill()

    videos = sorted((OUT / "video").rglob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not videos:
        print("Playwright produced no video.", file=sys.stderr)
        return 1
    to_gif(videos[-1])
    print(f"Wrote {GIF.relative_to(REPO)} ({GIF.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
