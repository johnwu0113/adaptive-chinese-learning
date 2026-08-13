import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "test_artifacts"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def backend_url():
    port = _find_free_port()
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "mas_backend:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.2)
    else:
        stdout, stderr = proc.communicate(timeout=10)
        raise RuntimeError(f"Failed to start MAS backend on port {port}.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")

    yield f"http://127.0.0.1:{port}"

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def artifacts_dir(tmp_path):
    target = tmp_path / "artifacts"
    target.mkdir(parents=True, exist_ok=True)
    return target


@pytest.fixture
def browser_page(backend_url, artifacts_dir):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(backend_url)
        yield page
        browser.close()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    if call.when != "call" or call.excinfo is None:
        return

    artifacts = item.funcargs.get("artifacts_dir")
    if artifacts is None:
        return

    item_name = item.name.replace("/", "_")
    artifact_dir = artifacts / item_name
    artifact_dir.mkdir(parents=True, exist_ok=True)

    log_path = artifact_dir / "failure.log"
    with log_path.open("w", encoding="utf-8") as fh:
        fh.write(f"test: {item.nodeid}\n")
        fh.write(f"exception: {call.excinfo.value}\n")

    page = item.funcargs.get("browser_page")
    if page is not None:
        try:
            page.screenshot(path=str(artifact_dir / "failure.png"), full_page=True)
        except Exception:
            pass
