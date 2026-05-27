import io
import tarfile


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
    files = {
        "scanner_runtime/__init__.py": b'"""Matrix Scanner Runtime."""\n',
        "scanner_runtime/agent_service.py": _agent_service_source().encode("utf-8"),
    }
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _agent_service_source():
    return r'''
import argparse
import json
import socket
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


AGENT_VERSION = "sprint3-bootstrap-runtime"


def request_json(method, base_url, path, payload=None, agent_token=""):
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if agent_token:
        headers["Authorization"] = f"Bearer {agent_token}"
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_config(path, config):
    Path(path).write_text(json.dumps(config, indent=2), encoding="utf-8")


def ensure_registered(config, config_path):
    if config.get("agent_token"):
        return config["agent_token"]
    payload = request_json(
        "POST",
        config["base_url"],
        "/api/agent/register/",
        {
            "registration_token": config["registration_token"],
            "hostname": socket.gethostname(),
            "agent_version": AGENT_VERSION,
        },
    )
    config["agent_token"] = payload["agent_token"]
    config["registration_token"] = ""
    save_config(config_path, config)
    return config["agent_token"]


def heartbeat(config, agent_token):
    request_json(
        "POST",
        config["base_url"],
        "/api/agent/heartbeat/",
        {"agent_version": AGENT_VERSION},
        agent_token=agent_token,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    while True:
        try:
            token = ensure_registered(config, args.config)
            heartbeat(config, token)
        except (HTTPError, URLError, OSError, KeyError, ValueError):
            pass
        time.sleep(int(config.get("poll_interval_seconds", 30)))


if __name__ == "__main__":
    main()
'''
