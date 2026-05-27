import json
import platform
import socket


SYSTEM_IDENTITY_TOOL_KEY = "system_identity"
MAX_OUTPUT_BYTES = 64 * 1024


class SystemIdentityError(Exception):
    pass


def collect_system_identity(params=None):
    if params:
        raise SystemIdentityError("system_identity does not accept parameters in Sprint 2.")

    output = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }
    size = len(json.dumps(output, separators=(",", ":"), default=str).encode("utf-8"))
    if size > MAX_OUTPUT_BYTES:
        raise SystemIdentityError("system_identity output exceeds the Sprint 2 size limit.")
    return output

