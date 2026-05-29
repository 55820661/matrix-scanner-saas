import subprocess

from apps.core.redaction import redact_secrets


class SafeExecError(Exception):
    pass


class SafeExecTimeout(SafeExecError):
    pass


class SafeExecOutputTooLarge(SafeExecError):
    pass


class SafeExecResult:
    def __init__(self, *, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run_fixed_command(argv, *, timeout_seconds=10, max_output_bytes=64 * 1024):
    if not isinstance(argv, (list, tuple)) or not argv or not all(isinstance(part, str) and part for part in argv):
        raise SafeExecError("Runtime commands must be fixed argv lists.")
    if timeout_seconds <= 0:
        raise SafeExecError("Runtime command timeout must be positive.")
    if max_output_bytes <= 0:
        raise SafeExecError("Runtime command output cap must be positive.")

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

    stdout = completed.stdout or ""
    stderr = redact_secrets(completed.stderr or "")
    encoded_size = len(stdout.encode("utf-8")) + len(stderr.encode("utf-8"))
    if encoded_size > max_output_bytes:
        raise SafeExecOutputTooLarge("Runtime command output exceeded the configured cap.")

    return SafeExecResult(returncode=completed.returncode, stdout=stdout, stderr=stderr)
