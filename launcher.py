import argparse
import importlib.util
import socket
import subprocess
import sys
import time
from pathlib import Path


def _terminate_process(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launcher para API FastAPI + GUI PyQt6 do MIO400."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host da API")
    parser.add_argument("--port", type=int, default=8000, help="Porta da API")
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Nao sobe a API; abre apenas a GUI conectando na URL informada.",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="URL da API usada pela GUI. Se omitida, usa host/port.",
    )
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent
    python_exe = sys.executable
    api_url = args.api_url or f"http://{args.host}:{args.port}"

    if importlib.util.find_spec("PyQt6") is None:
        print("[Launcher] Dependencia ausente: PyQt6")
        print("[Launcher] Instale com:")
        print(f"  \"{python_exe}\" -m pip install PyQt6")
        return 2

    api_proc = None
    try:
        if not args.no_api:
            if _is_port_in_use(args.host, args.port):
                print(
                    f"[Launcher] API ja em execucao em http://{args.host}:{args.port}. "
                    "Nao vou iniciar outro processo."
                )
            else:
                api_cmd = [
                    python_exe,
                    "-m",
                    "uvicorn",
                    "main:app",
                    "--host",
                    args.host,
                    "--port",
                    str(args.port),
                ]
                api_proc = subprocess.Popen(api_cmd, cwd=root_dir)
                time.sleep(2.0)

        gui_cmd = [
            python_exe,
            str(root_dir / "app" / "gui" / "main_window.py"),
            "--api-url",
            api_url,
        ]
        gui_proc = subprocess.Popen(gui_cmd, cwd=root_dir)
        gui_proc.wait()
        return gui_proc.returncode
    finally:
        _terminate_process(api_proc)


if __name__ == "__main__":
    raise SystemExit(main())
