import io
import tarfile
from pathlib import Path


SERVICE_FILE = """[Unit]
Description=Matrix Scanner Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/matrix_scanner
ExecStart=/usr/bin/python3 /opt/matrix_scanner/scanner_runtime/agent_service.py --config /opt/matrix_scanner/config.json
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
"""


def build_runtime_archive():
    buffer = io.BytesIO()
    files = _runtime_files()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _runtime_files():
    runtime_dir = Path(__file__).resolve().parents[2] / "scanner_runtime"
    files = {}
    for path in sorted(runtime_dir.glob("*.py")):
        if path.name == "__pycache__":
            continue
        files[f"scanner_runtime/{path.name}"] = path.read_bytes()
    files["scanner_runtime/agent_service.py"] = _agent_service_source().encode("utf-8")
    return files


def _agent_service_source():
    return r'''
import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError

from scanner_runtime.prototype import (
    RuntimeApiError,
    heartbeat,
    poll_execute_submit_once,
    register,
)

DEFAULT_POLL_INTERVAL_SECONDS = 30
RUNTIME_MODE = "polling_agent"


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_config(path, config):
    Path(path).write_text(json.dumps(config, indent=2), encoding="utf-8")


def ensure_registered(config, config_path):
    if config.get("agent_token"):
        return config["agent_token"]
    payload = register(config["base_url"], config["registration_token"])
    config["agent_token"] = payload["agent_token"]
    config["registration_token"] = ""
    config["runtime_mode"] = RUNTIME_MODE
    if payload.get("poll_interval_seconds"):
        config["poll_interval_seconds"] = int(payload["poll_interval_seconds"])
    save_config(config_path, config)
    return config["agent_token"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    config["runtime_mode"] = config.get("runtime_mode") or RUNTIME_MODE
    while True:
        try:
            token = ensure_registered(config, args.config)
            heartbeat(config["base_url"], token)
            poll_execute_submit_once(config["base_url"], token)
        except (RuntimeApiError, HTTPError, URLError, OSError, KeyError, ValueError):
            pass
        time.sleep(int(config.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)))


if __name__ == "__main__":
    main()
'''
