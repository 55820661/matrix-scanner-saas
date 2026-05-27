import json
from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from apps.accounts.models import Account
from apps.audit.models import AuditLog
from apps.servers.models import AgentJob, AgentRegistrationToken, ScannerAgent, Server
from scanner_runtime.system_identity import collect_system_identity


class Sprint2AgentFoundationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = Account.objects.create(name="Acme")
        self.server = Server.objects.create(account=self.account, name="Production")

    def _register_agent(self):
        registration_token, raw_registration_token = AgentRegistrationToken.create_for_server(self.server)
        response = self.client.post(
            "/api/agent/register/",
            data=json.dumps(
                {
                    "registration_token": raw_registration_token,
                    "server_id": "ignored-client-value",
                    "hostname": "web-01",
                    "agent_version": "test-agent",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        agent = ScannerAgent.objects.get(server=self.server)
        registration_token.refresh_from_db()
        self.assertIsNotNone(registration_token.used_at)
        return agent, payload["agent_token"]

    def _auth(self, agent_token):
        return {"HTTP_AUTHORIZATION": f"Bearer {agent_token}"}

    def test_registration_token_is_hashed_and_one_time_use(self):
        registration_token, raw_registration_token = AgentRegistrationToken.create_for_server(self.server)

        self.assertNotEqual(registration_token.token_hash, raw_registration_token)
        self.assertNotIn(raw_registration_token, registration_token.token_hash)

        response = self.client.post(
            "/api/agent/register/",
            data=json.dumps({"registration_token": raw_registration_token, "hostname": "web-01"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        agent = ScannerAgent.objects.get(server=self.server)
        payload = response.json()
        self.assertEqual(agent.status, ScannerAgent.Status.ACTIVE)
        self.assertEqual(agent.server_id, self.server.id)
        self.assertNotEqual(agent.token_hash, payload["agent_token"])
        self.assertNotIn(payload["agent_token"], agent.token_hash)

        repeat = self.client.post(
            "/api/agent/register/",
            data=json.dumps({"registration_token": raw_registration_token}),
            content_type="application/json",
        )
        self.assertEqual(repeat.status_code, 400)

    def test_expired_registration_token_is_rejected(self):
        registration_token, raw_registration_token = AgentRegistrationToken.create_for_server(self.server)
        registration_token.expires_at = timezone.now() - timedelta(minutes=1)
        registration_token.save(update_fields=["expires_at", "updated_at"])

        response = self.client.post(
            "/api/agent/register/",
            data=json.dumps({"registration_token": raw_registration_token}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ScannerAgent.objects.exists())

    def test_heartbeat_requires_valid_agent_token(self):
        agent, agent_token = self._register_agent()

        invalid = self.client.post(
            "/api/agent/heartbeat/",
            data=json.dumps({"agent_version": "test-agent"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer invalid",
        )
        self.assertEqual(invalid.status_code, 401)

        response = self.client.post(
            "/api/agent/heartbeat/",
            data=json.dumps({"agent_version": "test-agent-2"}),
            content_type="application/json",
            **self._auth(agent_token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        agent.refresh_from_db()
        self.assertEqual(agent.agent_version, "test-agent-2")
        self.assertIsNotNone(agent.last_seen_at)

    def test_poll_claims_one_allowlisted_job_atomically(self):
        agent, agent_token = self._register_agent()
        first = AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_key="system_identity",
        )
        second = AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_key="system_identity",
        )

        response = self.client.get("/api/agent/jobs/next/", **self._auth(agent_token))

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["job"]["job_id"], str(first.id))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, AgentJob.Status.CLAIMED)
        self.assertIsNotNone(first.claimed_at)
        self.assertIsNotNone(first.claim_expires_at)
        self.assertEqual(second.status, AgentJob.Status.PENDING)

    def test_non_allowlisted_job_is_rejected_before_delivery(self):
        agent, agent_token = self._register_agent()
        job = AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_key="arbitrary_command",
        )

        response = self.client.get("/api/agent/jobs/next/", **self._auth(agent_token))

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()["job"])
        job.refresh_from_db()
        self.assertEqual(job.status, AgentJob.Status.REJECTED)

    def test_job_result_updates_terminal_status_and_rejects_repeat_submit(self):
        agent, agent_token = self._register_agent()
        job = AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_key="system_identity",
        )
        self.client.get("/api/agent/jobs/next/", **self._auth(agent_token))

        response = self.client.post(
            f"/api/agent/jobs/{job.id}/result/",
            data=json.dumps({"status": "succeeded", "output": {"hostname": "web-01"}}),
            content_type="application/json",
            **self._auth(agent_token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        job.refresh_from_db()
        self.assertEqual(job.status, AgentJob.Status.SUCCEEDED)
        self.assertEqual(job.result, {"hostname": "web-01"})

        repeat = self.client.post(
            f"/api/agent/jobs/{job.id}/result/",
            data=json.dumps({"status": "succeeded", "output": {"hostname": "web-01"}}),
            content_type="application/json",
            **self._auth(agent_token),
        )
        self.assertEqual(repeat.status_code, 400)

    def test_job_result_requires_current_claim(self):
        agent, agent_token = self._register_agent()
        job = AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_key="system_identity",
        )

        response = self.client.post(
            f"/api/agent/jobs/{job.id}/result/",
            data=json.dumps({"status": "succeeded", "output": {"hostname": "web-01"}}),
            content_type="application/json",
            **self._auth(agent_token),
        )

        self.assertEqual(response.status_code, 400)
        job.refresh_from_db()
        self.assertEqual(job.status, AgentJob.Status.PENDING)

    def test_job_result_rejects_expired_claim(self):
        agent, agent_token = self._register_agent()
        job = AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_key="system_identity",
            status=AgentJob.Status.CLAIMED,
            claimed_at=timezone.now() - timedelta(minutes=10),
            claim_expires_at=timezone.now() - timedelta(minutes=5),
        )

        response = self.client.post(
            f"/api/agent/jobs/{job.id}/result/",
            data=json.dumps({"status": "succeeded", "output": {"hostname": "web-01"}}),
            content_type="application/json",
            **self._auth(agent_token),
        )

        self.assertEqual(response.status_code, 400)
        job.refresh_from_db()
        self.assertEqual(job.status, AgentJob.Status.TIMEOUT)

    def test_job_result_rejects_output_above_limit(self):
        agent, agent_token = self._register_agent()
        job = AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_key="system_identity",
        )
        self.client.get("/api/agent/jobs/next/", **self._auth(agent_token))

        response = self.client.post(
            f"/api/agent/jobs/{job.id}/result/",
            data=json.dumps({"status": "succeeded", "output": {"data": "x" * (64 * 1024)}}),
            content_type="application/json",
            **self._auth(agent_token),
        )

        self.assertEqual(response.status_code, 400)
        job.refresh_from_db()
        self.assertEqual(job.status, AgentJob.Status.CLAIMED)

    def test_agent_cannot_submit_another_agents_job(self):
        agent, _agent_token = self._register_agent()
        other_server = Server.objects.create(account=self.account, name="Worker")
        other_token, other_raw_registration_token = AgentRegistrationToken.create_for_server(other_server)
        other_response = self.client.post(
            "/api/agent/register/",
            data=json.dumps({"registration_token": other_raw_registration_token}),
            content_type="application/json",
        )
        self.assertEqual(other_response.status_code, 201, other_response.content)
        other_agent_token = other_response.json()["agent_token"]
        job = AgentJob.objects.create(
            account=self.account,
            server=self.server,
            agent=agent,
            tool_key="system_identity",
            status=AgentJob.Status.CLAIMED,
            claimed_at=timezone.now(),
            claim_expires_at=timezone.now() + timedelta(minutes=5),
        )

        response = self.client.post(
            f"/api/agent/jobs/{job.id}/result/",
            data=json.dumps({"status": "succeeded", "output": {"hostname": "wrong-agent"}}),
            content_type="application/json",
            **self._auth(other_agent_token),
        )

        self.assertEqual(response.status_code, 400)
        other_token.refresh_from_db()
        self.assertIsNotNone(other_token.used_at)

    def test_system_identity_runtime_output_is_structured_and_capped(self):
        output = collect_system_identity()
        encoded = json.dumps(output, separators=(",", ":")).encode("utf-8")

        self.assertIn("hostname", output)
        self.assertLessEqual(len(encoded), 64 * 1024)

    def test_agent_audit_metadata_does_not_store_tokens(self):
        _agent, _agent_token = self._register_agent()

        for audit_log in AuditLog.objects.filter(action__startswith="agent."):
            serialized = json.dumps(audit_log.metadata)
            self.assertNotIn("agent_token", serialized)
            self.assertNotIn("registration_token", serialized)
