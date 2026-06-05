import subprocess
import time

from apps.core.redaction import redact_secrets


class SafeExecError(Exception):
    pass


class SafeExecTimeout(SafeExecError):
    pass


class SafeExecOutputTooLarge(SafeExecError):
    pass


class SafeExecResult:
    def __init__(self, *, returncode, stdout, stderr, execution_time_seconds=0.0, truncated=False):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.execution_time_seconds = execution_time_seconds
        self.truncated = truncated


def _truncate_output(stdout, stderr, max_output_bytes):
    stdout_bytes = stdout.encode("utf-8")
    stderr_bytes = stderr.encode("utf-8")
    if len(stdout_bytes) >= max_output_bytes:
        return stdout_bytes[:max_output_bytes].decode("utf-8", errors="replace"), ""
    remaining = max_output_bytes - len(stdout_bytes)
    return stdout, stderr_bytes[:remaining].decode("utf-8", errors="replace")


def run_fixed_command(argv, *, timeout_seconds=10, max_output_bytes=64 * 1024, truncate_output=False):
    if not isinstance(argv, (list, tuple)) or not argv or not all(isinstance(part, str) and part for part in argv):
        raise SafeExecError("Runtime commands must be fixed argv lists.")
    if timeout_seconds <= 0:
        raise SafeExecError("Runtime command timeout must be positive.")
    if max_output_bytes <= 0:
        raise SafeExecError("Runtime command output cap must be positive.")

    started_at = time.monotonic()
    try:
        completed = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = redact_secrets(exc.stderr or "")
        raise SafeExecTimeout(f"Runtime command timed out. {stderr}".strip()) from exc
    except OSError as exc:
        raise SafeExecError(redact_secrets(str(exc))) from exc
    execution_time_seconds = time.monotonic() - started_at

    stdout = completed.stdout or ""
    stderr = redact_secrets(completed.stderr or "")
    encoded_size = len(stdout.encode("utf-8")) + len(stderr.encode("utf-8"))
    truncated = False
    if encoded_size > max_output_bytes:
        if not truncate_output:
            raise SafeExecOutputTooLarge("Runtime command output exceeded the configured cap.")
        stdout, stderr = _truncate_output(stdout, stderr, max_output_bytes)
        truncated = True

    return SafeExecResult(
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        execution_time_seconds=execution_time_seconds,
        truncated=truncated,
    )
