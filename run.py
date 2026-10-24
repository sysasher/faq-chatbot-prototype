#!/usr/bin/env python3
"""One-command setup and launch for the FAQ chatbot prototype.

Run this with `python run.py` (or double-click start.bat / start.sh).
On first run it creates the backend virtual environment, installs
backend and frontend dependencies, then every run it starts both
servers and opens the chat page in your browser. Press Ctrl+C to stop.
"""

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"


def log(message: str) -> None:
    print(f"[setup] {message}", flush=True)


def fail(message: str) -> None:
    print(f"[setup] ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def venv_python() -> Path:
    if IS_WINDOWS:
        return BACKEND / "venv" / "Scripts" / "python.exe"
    return BACKEND / "venv" / "bin" / "python"


def ensure_backend() -> None:
    venv_dir = BACKEND / "venv"
    if not venv_dir.exists():
        log("Creating backend virtual environment (first run only)...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

    log("Checking backend dependencies...")
    subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "-q", "-r", "requirements.txt"],
        cwd=BACKEND,
        check=True,
    )

    env_file = BACKEND / ".env"
    if not env_file.exists():
        shutil.copy(BACKEND / ".env.example", env_file)


def run_npm(args: list, cwd: Path) -> None:
    if IS_WINDOWS:
        subprocess.run(["cmd", "/c", "npm", *args], cwd=cwd, check=True)
    else:
        subprocess.run(["npm", *args], cwd=cwd, check=True)


def ensure_frontend() -> None:
    if not shutil.which("node"):
        fail("Node.js was not found. Install Node.js 18+ from https://nodejs.org and run this again.")

    env_file = FRONTEND / ".env"
    if not env_file.exists():
        shutil.copy(FRONTEND / ".env.example", env_file)

    if not (FRONTEND / "node_modules").exists():
        log("Installing frontend dependencies (first run only, this can take a minute)...")
        run_npm(["install"], FRONTEND)
    else:
        log("Frontend dependencies already installed.")


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def find_free_port(candidates) -> int:
    for port in candidates:
        if is_port_free(port):
            return port
    fail("Could not find a free port to run the backend on.")


def set_frontend_api_url(port: int) -> None:
    env_file = FRONTEND / ".env"
    url_line = f"VITE_API_URL=http://127.0.0.1:{port}"
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    found = False
    for i, line in enumerate(lines):
        if line.startswith("VITE_API_URL="):
            lines[i] = url_line
            found = True
    if not found:
        lines.append(url_line)
    env_file.write_text("\n".join(lines) + "\n")


def wait_for_http(port: int, path: str, timeout: float) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}{path}"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as res:
                if res.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def main() -> None:
    ensure_backend()
    ensure_frontend()

    backend_port = find_free_port([8000, *range(8010, 8030)])
    set_frontend_api_url(backend_port)
    log(f"Backend will run on http://127.0.0.1:{backend_port}")

    log("Starting backend...")
    backend_proc = subprocess.Popen(
        [str(venv_python()), "-m", "uvicorn", "main:app", "--port", str(backend_port)],
        cwd=BACKEND,
    )

    if not wait_for_http(backend_port, "/api/health", timeout=20):
        log("Warning: backend did not respond in time; continuing anyway.")

    frontend_port = 5173
    log("Starting frontend...")
    node = shutil.which("node")
    vite_entry = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    frontend_proc = subprocess.Popen(
        [node, str(vite_entry), "--host", "127.0.0.1", "--port", str(frontend_port), "--strictPort"],
        cwd=FRONTEND,
    )

    frontend_url = f"http://127.0.0.1:{frontend_port}"
    if wait_for_http(frontend_port, "/", timeout=20):
        log(f"Opening {frontend_url} in your browser...")
        webbrowser.open(frontend_url)
    else:
        log(f"Frontend did not respond in time. Try opening {frontend_url} manually.")

    log("Both servers are running. Press Ctrl+C here to stop them.")
    try:
        while True:
            if backend_proc.poll() is not None:
                fail("Backend process exited unexpectedly. Check the output above.")
            if frontend_proc.poll() is not None:
                fail("Frontend process exited unexpectedly. Check the output above.")
            time.sleep(1)
    except KeyboardInterrupt:
        log("Stopping...")
    finally:
        for proc in (backend_proc, frontend_proc):
            if proc.poll() is None:
                proc.terminate()
        for proc in (backend_proc, frontend_proc):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
