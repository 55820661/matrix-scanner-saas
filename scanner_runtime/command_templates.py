from apps.core.redaction import redact_secrets

from .safe_exec import SafeExecError, SafeExecTimeout, run_fixed_command


COMMAND_TEMPLATE_EXECUTION_TYPE = "command_template"


class CommandTemplateRuntimeError(Exception):
    pass


def execute_command_template_payload(payload):
    if not isinstance(payload, dict) or payload.get("execution_type") != COMMAND_TEMPLATE_EXECUTION_TYPE:
        raise CommandTemplateRuntimeError("Unsupported command template payload.")
    argv = payload.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) and part for part in argv):
        raise CommandTemplateRuntimeError("Command template payload must contain a fixed argv list.")
    timeout_seconds = int(payload.get("timeout_seconds") or 10)
    max_output_bytes = int(payload.get("max_output_bytes") or 64 * 1024)
    try:
        result = run_fixed_command(
            argv,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
            truncate_output=True,
        )
    except SafeExecTimeout as exc:
        return {
            "status": "timeout",
            "output": {
                "command": {
                    "exit_code": None,
                    "stdout_redacted": "",
                    "stderr_redacted": redact_secrets(str(exc)),
                    "execution_time_seconds": timeout_seconds,
                    "truncated": False,
                }
            },
            "error": redact_secrets(str(exc)),
        }
    except SafeExecError as exc:
        return {
            "status": "failed",
            "output": {
                "command": {
                    "exit_code": None,
                    "stdout_redacted": "",
                    "stderr_redacted": redact_secrets(str(exc)),
                    "execution_time_seconds": 0,
                    "truncated": False,
                }
            },
            "error": redact_secrets(str(exc)),
        }

    command_output = {
        "command": {
            "exit_code": result.returncode,
            "stdout_redacted": redact_secrets(result.stdout),
            "stderr_redacted": redact_secrets(result.stderr),
            "execution_time_seconds": round(result.execution_time_seconds, 4),
            "truncated": result.truncated,
        }
    }
    return {
        "status": "succeeded" if result.returncode == 0 else "failed",
        "output": command_output,
        "error": "" if result.returncode == 0 else "Command exited with a non-zero status.",
    }
