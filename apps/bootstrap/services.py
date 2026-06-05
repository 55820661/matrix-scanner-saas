import json
import time

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.redaction import redact_secrets
from apps.servers.models import AgentRegistrationToken, ScannerAgent

from .crypto import decrypt_payload, encrypt_payload
from .models import (
    AgentInstallation,
    BootstrapCredential,
    BootstrapSession,
    BootstrapStep,
    DEFAULT_INSTALL_PATH,
    DEFAULT_SERVICE_NAME,
)
from .policy import BootstrapPolicyError, package_install_template, reject_raw_command, render_command
from .runtime_bundle import SERVICE_FILE, build_runtime_archive
from .ssh import ParamikoSSHClient


class BootstrapError(Exception):
    pass


def is_matrix_admin(user):
    return bool(user and user.is_staff and user.is_superuser)


def audit_bootstrap(session, action, result=AuditLog.Result.INFO, metadata=None):
    AuditLog.objects.create(
        actor_user=session.created_by,
        actor_type=AuditLog.ActorType.ADMIN,
        account=session.account,
        action=action,
        target_type="BootstrapSession",
        target_id=str(session.id),
        result=result,
        metadata=metadata or {},
    )


def create_bootstrap_session(
    *,
    user,
    server,
    ssh_user,
    auth_method,
    secret,
    target_host="",
    ssh_port=22,
    confirm_package_install=False,
):
    if not is_matrix_admin(user):
        raise PermissionDenied("Remote bootstrap is restricted to Matrix Admin users.")

    resolved_host = target_host or server.hostname or str(server.public_ip or "")
    if not resolved_host:
        raise ValidationError("Bootstrap target host is required.")
    if auth_method not in BootstrapSession.AuthMethod.values:
        raise ValidationError("Unsupported bootstrap authentication method.")
    if not secret:
        raise ValidationError("Bootstrap credential secret is required.")

    session = BootstrapSession.objects.create(
        account=server.account,
        server=server,
        created_by=user,
        target_host=resolved_host,
        ssh_port=ssh_port,
        ssh_user=ssh_user,
        auth_method=auth_method,
        confirm_package_install=confirm_package_install,
        install_path=DEFAULT_INSTALL_PATH,
        service_name=DEFAULT_SERVICE_NAME,
    )
    credential_type = (
        BootstrapCredential.CredentialType.SSH_PASSWORD
        if auth_method == BootstrapSession.AuthMethod.PASSWORD
        else BootstrapCredential.CredentialType.SSH_PRIVATE_KEY
    )
    BootstrapCredential.objects.create(
        session=session,
        credential_type=credential_type,
        encrypted_payload=encrypt_payload(secret),
        expires_at=BootstrapCredential.default_expiry(),
    )
    audit_bootstrap(session, "bootstrap.session_created", AuditLog.Result.SUCCESS, metadata={"auth_method": auth_method})
    return session


def cleanup_session_credentials(session):
    for credential in session.credentials.all():
        if credential.encrypted_payload or credential.destroyed_at is None:
            credential.cleanup()


def expire_stale_credentials(now=None):
    now = now or timezone.now()
    expired = BootstrapCredential.objects.filter(destroyed_at__isnull=True, expires_at__lte=now)
    session_ids = list(expired.values_list("session_id", flat=True).distinct())
    for credential in expired:
        credential.cleanup()
    BootstrapSession.objects.filter(id__in=session_ids, status=BootstrapSession.Status.PENDING).update(
        status=BootstrapSession.Status.EXPIRED,
        finished_at=now,
        failure_reason="Bootstrap credentials expired before use.",
        updated_at=now,
    )
    return len(session_ids)


def _usable_credential(session):
    credential = session.credentials.order_by("-created_at").first()
    if credential is None:
        raise BootstrapError("Bootstrap credential is missing.")
    if not credential.is_usable:
        session.status = BootstrapSession.Status.EXPIRED
        session.finished_at = timezone.now()
        session.failure_reason = "Bootstrap credential is expired or destroyed."
        session.save(update_fields=["status", "finished_at", "failure_reason", "updated_at"])
        cleanup_session_credentials(session)
        raise BootstrapError("Bootstrap credential is expired or destroyed.")
    return credential


def _set_session_status(session, status):
    session.status = status
    fields = ["status", "updated_at"]
    if status == BootstrapSession.Status.CONNECTING and session.started_at is None:
        session.started_at = timezone.now()
        fields.append("started_at")
    session.save(update_fields=fields)


def _finish_session(session, status, reason=""):
    session.status = status
    session.finished_at = timezone.now()
    session.failure_reason = reason
    session.save(update_fields=["status", "finished_at", "failure_reason", "updated_at"])


def _run_step(session, ssh, *, step_key, template_key, status=None, confirmed=False, timeout=30):
    if status:
        _set_session_status(session, status)
    command = render_command(template_key, confirmed=confirmed)
    reject_raw_command(command)
    template_requires_confirmation = template_key.endswith("_package_install")
    step = BootstrapStep.objects.create(
        session=session,
        step_key=step_key,
        status=BootstrapStep.Status.RUNNING,
        started_at=timezone.now(),
        command_template_key=template_key,
        requires_confirmation=template_requires_confirmation,
        confirmed_at=timezone.now() if template_requires_confirmation and confirmed else None,
    )
    result = ssh.run(command, timeout=timeout)
    step.exit_code = result["exit_code"]
    step.stdout_redacted = redact_secrets(result.get("stdout", ""))[:8000]
    step.stderr_redacted = redact_secrets(result.get("stderr", ""))[:8000]
    step.finished_at = timezone.now()
    if step.exit_code == 0:
        step.status = BootstrapStep.Status.SUCCEEDED
        step.summary = f"{step_key} completed."
    else:
        step.status = BootstrapStep.Status.FAILED
        step.error_message = f"{step_key} failed."
    step.save()
    audit_bootstrap(
        session,
        "bootstrap.step_completed" if step.status == BootstrapStep.Status.SUCCEEDED else "bootstrap.step_failed",
        AuditLog.Result.SUCCESS if step.status == BootstrapStep.Status.SUCCEEDED else AuditLog.Result.FAILURE,
        metadata={"step": step_key, "status": step.status},
    )
    if step.status == BootstrapStep.Status.FAILED:
        raise BootstrapError(step.error_message)
    return result, step


def _upload_runtime_files(ssh, config):
    ssh.put_bytes("/tmp/matrix_scanner_runtime.tar.gz", build_runtime_archive())
    ssh.put_bytes("/tmp/matrix_scanner_config.json", json.dumps(config, indent=2).encode("utf-8"))
    ssh.put_bytes("/tmp/matrix-scanner-agent.service", SERVICE_FILE.encode("utf-8"))


def _detect_package_manager(stdout):
    for line in stdout.splitlines():
        if line.endswith("apt-get"):
            return "apt"
        if line.endswith("dnf"):
            return "dnf"
        if line.endswith("yum"):
            return "yum"
    raise BootstrapError("Supported package manager was not found.")


def _verify_heartbeat(session, timeout_seconds=None):
    timeout_seconds = timeout_seconds or settings.BOOTSTRAP_HEARTBEAT_TIMEOUT_SECONDS
    deadline = time.monotonic() + timeout_seconds
    started_at = session.started_at or timezone.now()
    while time.monotonic() <= deadline:
        agent = ScannerAgent.objects.filter(server=session.server, account=session.account).first()
        if agent and agent.last_seen_at and agent.last_seen_at >= started_at:
            return agent
        time.sleep(1)
    raise BootstrapError("Agent heartbeat was not observed within 60 seconds.")


def run_bootstrap_session(session, *, ssh_client_cls=ParamikoSSHClient, heartbeat_checker=None):
    if not is_matrix_admin(session.created_by):
        raise PermissionDenied("Remote bootstrap is restricted to Matrix Admin users.")
    if session.is_terminal:
        raise BootstrapError("Terminal bootstrap sessions cannot be reused.")
    if not session.confirm_package_install:
        session.status = BootstrapSession.Status.AWAITING_PACKAGE_CONFIRMATION
        session.save(update_fields=["status", "updated_at"])
        raise BootstrapError("Package installation requires explicit confirmation.")

    registration_token = None
    try:
        credential = _usable_credential(session)
        secret = decrypt_payload(credential.encrypted_payload)
        _set_session_status(session, BootstrapSession.Status.CONNECTING)
        audit_bootstrap(session, "bootstrap.started", AuditLog.Result.SUCCESS, metadata={"target_host": session.target_host})

        with ssh_client_cls(
            session.target_host,
            session.ssh_port,
            session.ssh_user,
            session.auth_method,
            secret,
            timeout=10,
        ) as ssh:
            _run_step(session, ssh, step_key="ssh_connectivity_check", template_key="remote_os_probe")
            _run_step(
                session,
                ssh,
                step_key="systemd_detector",
                template_key="systemd_detector",
                status=BootstrapSession.Status.PROBING,
            )
            _run_step(session, ssh, step_key="privilege_check", template_key="privilege_check")
            package_result, package_step = _run_step(
                session,
                ssh,
                step_key="package_manager_detector",
                template_key="package_manager_detector",
            )
            package_manager = _detect_package_manager(package_result["stdout"])
            package_step.structured_output = {"package_manager": package_manager}
            package_step.save(update_fields=["structured_output", "updated_at"])

            _run_step(
                session,
                ssh,
                step_key="scanner_dependencies_install",
                template_key=package_install_template(package_manager),
                status=BootstrapSession.Status.INSTALLING,
                confirmed=True,
                timeout=120,
            )
            python_result, python_step = _run_step(
                session,
                ssh,
                step_key="python_runtime_detector",
                template_key="python_runtime_detector",
            )
            python_path = python_result["stdout"].strip().splitlines()[0] if python_result["stdout"].strip() else ""
            if not python_path:
                raise BootstrapError("Python path was not detected after package installation.")
            python_step.structured_output = {"python_path": python_path}
            python_step.save(update_fields=["structured_output", "updated_at"])

            _run_step(
                session,
                ssh,
                step_key="bootstrap_directory_prepare",
                template_key="bootstrap_directory_prepare",
                status=BootstrapSession.Status.DEPLOYING,
            )
            registration_token, raw_registration_token = AgentRegistrationToken.create_for_server(
                session.server,
                created_by=session.created_by,
            )
            config = {
                "base_url": settings.PUBLIC_BASE_URL,
                "registration_token": raw_registration_token,
                "poll_interval_seconds": 30,
                "runtime_mode": "polling_agent",
            }
            _upload_runtime_files(ssh, config)
            _run_step(session, ssh, step_key="scanner_code_deploy", template_key="scanner_archive_extract")
            _run_step(
                session,
                ssh,
                step_key="scanner_config_write",
                template_key="scanner_config_install",
                status=BootstrapSession.Status.CONFIGURING,
            )
            _run_step(session, ssh, step_key="systemd_service_install", template_key="systemd_service_install")
            _run_step(
                session,
                ssh,
                step_key="systemd_service_start",
                template_key="systemd_service_start",
                status=BootstrapSession.Status.STARTING,
            )

        _set_session_status(session, BootstrapSession.Status.VERIFYING_HEARTBEAT)
        heartbeat_step = BootstrapStep.objects.create(
            session=session,
            step_key="agent_heartbeat_verify",
            status=BootstrapStep.Status.RUNNING,
            started_at=timezone.now(),
        )
        try:
            agent = heartbeat_checker(session) if heartbeat_checker else _verify_heartbeat(session)
        except Exception as exc:
            heartbeat_step.status = BootstrapStep.Status.FAILED
            heartbeat_step.finished_at = timezone.now()
            heartbeat_step.error_message = redact_secrets(str(exc))[:4000]
            heartbeat_step.save()
            raise
        heartbeat_step.status = BootstrapStep.Status.SUCCEEDED
        heartbeat_step.finished_at = timezone.now()
        heartbeat_step.summary = "Agent heartbeat verified."
        heartbeat_step.structured_output = {"agent_id": str(agent.id)}
        heartbeat_step.save()
        audit_bootstrap(
            session,
            "bootstrap.heartbeat_verified",
            AuditLog.Result.SUCCESS,
            metadata={"step": "agent_heartbeat_verify", "status": heartbeat_step.status},
        )
        AgentInstallation.objects.create(
            account=session.account,
            server=session.server,
            agent=agent,
            bootstrap_session=session,
            install_path=session.install_path,
            service_name=session.service_name,
            agent_version=agent.agent_version,
            status=AgentInstallation.Status.INSTALLED,
            installed_at=timezone.now(),
            last_verified_at=timezone.now(),
        )
        _finish_session(session, BootstrapSession.Status.COMPLETED)
        cleanup_session_credentials(session)
        audit_bootstrap(session, "bootstrap.completed", AuditLog.Result.SUCCESS, metadata={"status": session.status})
        return session
    except Exception as exc:
        if registration_token and registration_token.used_at is None:
            registration_token.revoked_at = timezone.now()
            registration_token.save(update_fields=["revoked_at", "updated_at"])
        reason = redact_secrets(str(exc))[:4000]
        if session.status != BootstrapSession.Status.EXPIRED:
            _finish_session(session, BootstrapSession.Status.FAILED, reason)
        else:
            session.failure_reason = reason
            session.save(update_fields=["failure_reason", "updated_at"])
        cleanup_session_credentials(session)
        AgentInstallation.objects.get_or_create(
            account=session.account,
            server=session.server,
            bootstrap_session=session,
            defaults={
                "install_path": session.install_path,
                "service_name": session.service_name,
                "status": AgentInstallation.Status.FAILED,
            },
        )
        audit_bootstrap(session, "bootstrap.failed", AuditLog.Result.FAILURE, metadata={"status": session.status})
        raise
