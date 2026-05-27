import json
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.audit.models import AuditLog
from apps.bootstrap.models import AgentInstallation, BootstrapCredential, BootstrapSession, BootstrapStep
from apps.bootstrap.policy import BootstrapPolicyError, reject_raw_command, render_command
from apps.bootstrap.services import BootstrapError, create_bootstrap_session, run_bootstrap_session
from apps.core.tokens import hash_token
from apps.servers.models import AgentJob, BaselineScan, ScannerAgent, Server


class FakeSSHClient:
    commands = []
    uploads = []

    def __init__(self, hostname, port, username, auth_method, secret, timeout=10):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.auth_method = auth_method
        self.secret = secret

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def run(self, command, timeout=30):
        self.commands.append(command)
        if command == "cat /etc/os-release":
            return {"exit_code": 0, "stdout": "ID=ubuntu\nID_LIKE=debian\n", "stderr": ""}
        if "command -v apt-get" in command:
            return {"exit_code": 0, "stdout": "/usr/bin/apt-get\n", "stderr": ""}
        if command == "command -v python3":
            return {"exit_code": 0, "stdout": "/usr/bin/python3\n", "stderr": ""}
        return {"exit_code": 0, "stdout": "ok\n", "stderr": ""}

    def put_bytes(self, remote_path, data):
        self.uploads.append((remote_path, data))


class FailingSSHClient(FakeSSHClient):
    def __enter__(self):
        raise BootstrapError("SSH connection failed")


@override_settings(
    BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY="unit-test-bootstrap-encryption-key",
    BOOTSTRAP_HEARTBEAT_TIMEOUT_SECONDS=1,
    PUBLIC_BASE_URL="https://scanner.example.test",
)
class Sprint3BootstrapTests(TestCase):
    def setUp(self):
        FakeSSHClient.commands = []
        FakeSSHClient.uploads = []
        self.account = Account.objects.create(name="Acme")
        self.server = Server.objects.create(
            account=self.account,
            name="Production",
            hostname="web-01.example.test",
        )
        self.admin = User.objects.create_superuser(
            username="matrix-admin",
            email="admin@example.com",
            password="password",
        )

    def _create_session(self, secret="SuperSecretPassword123", confirm=True):
        return create_bootstrap_session(
            user=self.admin,
            server=self.server,
            ssh_user="root",
            auth_method=BootstrapSession.AuthMethod.PASSWORD,
            secret=secret,
            confirm_package_install=confirm,
        )

    def _heartbeat_checker(self, session):
        now = timezone.now()
        agent, _created = ScannerAgent.objects.get_or_create(
            server=session.server,
            defaults={
                "account": session.account,
                "token_hash": hash_token("runtime-agent-token"),
                "status": ScannerAgent.Status.ACTIVE,
                "registered_at": now,
                "last_seen_at": now,
                "agent_version": "sprint3-bootstrap-runtime",
            },
        )
        agent.account = session.account
        agent.status = ScannerAgent.Status.ACTIVE
        agent.last_seen_at = now
        agent.agent_version = "sprint3-bootstrap-runtime"
        agent.save()
        return agent

    def test_matrix_admin_can_create_and_run_bootstrap(self):
        session = self._create_session()

        run_bootstrap_session(session, ssh_client_cls=FakeSSHClient, heartbeat_checker=self._heartbeat_checker)

        session.refresh_from_db()
        self.assertEqual(session.status, BootstrapSession.Status.COMPLETED)
        self.assertTrue(
            BootstrapStep.objects.filter(
                session=session,
                step_key="agent_heartbeat_verify",
                status=BootstrapStep.Status.SUCCEEDED,
            ).exists()
        )
        self.assertTrue(session.steps.filter(step_key="systemd_service_start", status=BootstrapStep.Status.SUCCEEDED).exists())
        self.assertTrue(session.credentials.filter(destroyed_at__isnull=False, encrypted_payload="").exists())
        installation = AgentInstallation.objects.get(bootstrap_session=session)
        self.assertEqual(installation.status, AgentInstallation.Status.INSTALLED)
        self.assertEqual(installation.install_path, "/opt/matrix_scanner")
        self.assertEqual(installation.service_name, "matrix-scanner-agent.service")

    def test_customer_roles_cannot_create_or_run_bootstrap(self):
        for role in User.CustomerRole.values:
            user = User.objects.create_user(
                username=f"user-{role}",
                email=f"{role}@example.com",
                password="password",
                account=self.account,
                role=role,
            )
            with self.assertRaises(PermissionDenied):
                create_bootstrap_session(
                    user=user,
                    server=self.server,
                    ssh_user="root",
                    auth_method=BootstrapSession.AuthMethod.PASSWORD,
                    secret="password",
                    confirm_package_install=True,
                )

        session = self._create_session()
        session.created_by = User.objects.create_user(
            username="bootstrap-owner",
            email="bootstrap-owner@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.OWNER,
        )
        session.save(update_fields=["created_by", "updated_at"])
        with self.assertRaises(PermissionDenied):
            run_bootstrap_session(session, ssh_client_cls=FakeSSHClient, heartbeat_checker=self._heartbeat_checker)

    def test_credential_payload_does_not_store_raw_password_or_private_key(self):
        raw_password = "SuperSecretPassword123"
        password_session = self._create_session(secret=raw_password)
        password_credential = password_session.credentials.get()

        self.assertNotIn(raw_password, password_credential.encrypted_payload)

        raw_private_key = "-----BEGIN OPENSSH PRIVATE KEY-----\nabc123\n-----END OPENSSH PRIVATE KEY-----"
        key_session = create_bootstrap_session(
            user=self.admin,
            server=self.server,
            ssh_user="root",
            auth_method=BootstrapSession.AuthMethod.PRIVATE_KEY,
            secret=raw_private_key,
            confirm_package_install=True,
        )
        key_credential = key_session.credentials.get()
        self.assertNotIn(raw_private_key, key_credential.encrypted_payload)
        self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", key_credential.encrypted_payload)

    def test_credential_expiry_blocks_use_and_cleans_payload(self):
        session = self._create_session()
        credential = session.credentials.get()
        credential.expires_at = timezone.now() - timedelta(minutes=1)
        credential.save(update_fields=["expires_at", "updated_at"])

        with self.assertRaises(BootstrapError):
            run_bootstrap_session(session, ssh_client_cls=FakeSSHClient, heartbeat_checker=self._heartbeat_checker)

        session.refresh_from_db()
        credential.refresh_from_db()
        self.assertEqual(session.status, BootstrapSession.Status.EXPIRED)
        self.assertEqual(credential.encrypted_payload, "")
        self.assertIsNotNone(credential.destroyed_at)

    def test_bootstrap_policy_rejects_unknown_template_and_raw_shell(self):
        with self.assertRaises(BootstrapPolicyError):
            render_command("unknown_template")
        with self.assertRaises(BootstrapPolicyError):
            reject_raw_command("rm -rf /")

    def test_package_install_requires_confirmation(self):
        with self.assertRaises(BootstrapPolicyError):
            render_command("apt_package_install", confirmed=False)

        session = self._create_session(confirm=False)
        with self.assertRaises(BootstrapError):
            run_bootstrap_session(session, ssh_client_cls=FakeSSHClient, heartbeat_checker=self._heartbeat_checker)
        session.refresh_from_db()
        self.assertEqual(session.status, BootstrapSession.Status.AWAITING_PACKAGE_CONFIRMATION)

    def test_step_status_values_are_locked(self):
        self.assertEqual(
            BootstrapStep.Status.values,
            ["pending", "running", "succeeded", "failed", "skipped", "cancelled"],
        )

    def test_paramiko_mocked_success_path_reaches_heartbeat_verification(self):
        session = self._create_session()

        run_bootstrap_session(session, ssh_client_cls=FakeSSHClient, heartbeat_checker=self._heartbeat_checker)

        session.refresh_from_db()
        self.assertEqual(session.status, BootstrapSession.Status.COMPLETED)
        self.assertTrue(FakeSSHClient.uploads)
        config_upload = [upload for upload in FakeSSHClient.uploads if upload[0] == "/tmp/matrix_scanner_config.json"][0]
        uploaded_config = json.loads(config_upload[1].decode("utf-8"))
        self.assertEqual(uploaded_config["base_url"], "https://scanner.example.test")
        self.assertIn("registration_token", uploaded_config)

    def test_paramiko_mocked_ssh_failure_marks_failed_and_cleans_credentials(self):
        session = self._create_session()

        with self.assertRaises(BootstrapError):
            run_bootstrap_session(session, ssh_client_cls=FailingSSHClient, heartbeat_checker=self._heartbeat_checker)

        session.refresh_from_db()
        credential = session.credentials.get()
        self.assertEqual(session.status, BootstrapSession.Status.FAILED)
        self.assertEqual(credential.encrypted_payload, "")
        self.assertIsNotNone(credential.destroyed_at)

    def test_sprint3_workflow_creates_no_baseline_or_diagnostic_jobs(self):
        session = self._create_session()

        run_bootstrap_session(session, ssh_client_cls=FakeSSHClient, heartbeat_checker=self._heartbeat_checker)

        self.assertEqual(BaselineScan.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_audit_log_metadata_contains_no_secrets(self):
        raw_password = "SuperSecretPassword123"
        session = self._create_session(secret=raw_password)

        run_bootstrap_session(session, ssh_client_cls=FakeSSHClient, heartbeat_checker=self._heartbeat_checker)

        for audit_log in AuditLog.objects.filter(action__startswith="bootstrap."):
            serialized = json.dumps(audit_log.metadata)
            self.assertNotIn(raw_password, serialized)
            self.assertNotIn("registration_token", serialized)
            self.assertNotIn("private_key", serialized)
