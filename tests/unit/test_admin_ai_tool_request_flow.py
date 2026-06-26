import io
import json
from datetime import timedelta
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.ai_chat.models import AdminChatMessage, AdminChatSession, AdminChatToolRequest, AdminLiveAIRequestLog
from apps.ai_chat.services import (
    approve_tool_request,
    create_admin_chat_session,
    create_chat_session,
    reject_tool_request,
    tool_followup_timeout_for_count,
    wait_for_tool_execution_result,
)
from apps.plans.models import Plan
from apps.servers.models import AgentJob, ScannerAgent, Server
from apps.subscriptions.models import Subscription
from apps.tools.models import PlanTool, ToolDefinition, ToolPolicy, ToolRun, ToolTemplate


LIVE_SETTINGS = {
    "ADMIN_LIVE_AI_ENABLED": True,
    "OPENAI_API_KEY": "server-only-test-key",
    "OPENAI_MODEL": "test-model",
    "OPENAI_CHATKIT_DOMAIN_KEY": "domain-test-key",
    "OPENAI_TIMEOUT_SECONDS": 3,
    "OPENAI_MAX_INPUT_TOKENS": 4000,
    "OPENAI_MAX_OUTPUT_TOKENS": 500,
    "ADMIN_LIVE_AI_RATE_LIMIT_PER_HOUR": 30,
}


class ProposalProvider:
    def __init__(self, text):
        self.text = text

    async def stream(self, *, instructions, input_text, state):
        state.provider_request_id = "response-tool-proposal"
        state.usage = {"input_units": 11, "output_units": 5}
        yield self.text


class AdminAIToolRequestFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.account = Account.objects.create(name="Acme")
        self.staff = User.objects.create_superuser(
            username="staff",
            email="staff@example.com",
            password="password",
        )
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.OWNER,
        )
        self.server = Server.objects.create(account=self.account, name="Production", status=Server.Status.ACTIVE)
        self.plan = Plan.objects.create(name="Pilot", max_servers=5, max_applications=20, max_users=5)
        Subscription.objects.create(
            account=self.account,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=timezone.now() - timedelta(days=1),
            current_period_end=timezone.now() + timedelta(days=30),
        )
        ScannerAgent.objects.create(
            account=self.account,
            server=self.server,
            token_hash="agent-token-hash-c109",
            status=ScannerAgent.Status.ACTIVE,
            registered_at=timezone.now(),
        )
        self.session = create_admin_chat_session(
            user=self.staff,
            account_id=self.account.id,
            title="Tool proposal",
            server_id=self.server.id,
        )
        self.client.force_login(self.staff)

    def create_tool(self, *, key="services_status", risk_level=ToolDefinition.RiskLevel.READ_ONLY, allow_admin=True, plan_enabled=True):
        template, _ = ToolTemplate.objects.update_or_create(
            key=f"{key}_template",
            defaults={
                "name": f"{key} template",
                "runtime_handler_key": key,
                "input_schema": {"fields": {}},
                "output_schema": {"summary": "object"},
                "is_active": True,
            },
        )
        definition, _ = ToolDefinition.objects.update_or_create(
            key=key,
            defaults={
                "template": template,
                "name": key,
                "status": ToolDefinition.Status.ENABLED,
                "risk_level": risk_level,
                "input_schema": {"fields": {}},
                "default_params": {},
                "timeout_seconds": 30,
                "max_output_bytes": 4096,
            },
        )
        ToolPolicy.objects.update_or_create(
            tool_definition=definition,
            defaults={
                "allow_customer_run": False,
                "allow_admin_run": allow_admin,
                "allow_agent_run": True,
                "allowed_roles": [User.CustomerRole.OWNER, User.CustomerRole.OPERATOR],
                "allowed_server_statuses": [Server.Status.ACTIVE],
                "is_active": True,
            },
        )
        PlanTool.objects.update_or_create(
            plan=self.plan,
            tool_definition=definition,
            defaults={"is_enabled": plan_enabled},
        )
        return definition

    def live_url(self):
        return reverse("admin_chat:session_live", args=[self.session.id])

    def live_payload(self, text="Check services"):
        return {
            "type": "threads.add_user_message",
            "params": {
                "thread_id": str(self.session.id),
                "input": {
                    "content": [{"type": "input_text", "text": text}],
                    "attachments": [],
                    "inference_options": {},
                },
            },
        }

    @staticmethod
    async def _consume_async(stream):
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        return b"".join(chunks)

    def consume_stream(self, response):
        if hasattr(response.streaming_content, "__aiter__"):
            return async_to_sync(self._consume_async)(response.streaming_content)
        return b"".join(response.streaming_content)

    def post_live_with_provider_text(self, text, *, request_text="What do you suggest?", wait_outcome=None, wait_side_effect=None):
        patches = [patch("apps.ai_chat.live_ai.get_live_ai_provider", return_value=ProposalProvider(text))]
        if wait_side_effect is not None:
            patches.append(patch("apps.ai_chat.services.wait_for_tool_execution_result", side_effect=wait_side_effect))
        elif wait_outcome is not None:
            patches.append(patch("apps.ai_chat.services.wait_for_tool_execution_result", return_value=wait_outcome))
        with patches[0]:
            if len(patches) > 1:
                patches[1].start()
            try:
                response = self.client.post(
                    self.live_url(),
                    data=json.dumps(self.live_payload(request_text)),
                    content_type="application/json",
                )
                content = self.consume_stream(response)
            finally:
                if len(patches) > 1:
                    patches[1].stop()
        self.assertEqual(response.status_code, 200)
        return content.decode(errors="ignore")

    def timeout_outcome(self):
        return {
            "state": "timeout",
            "status": ToolRun.Status.QUEUED,
            "summary": "Tool execution did not finish within the follow-up wait window.",
            "tool_run_id": "",
        }

    def success_outcome(self, summary="services_status completed successfully."):
        return {
            "state": "succeeded",
            "status": ToolRun.Status.SUCCEEDED,
            "summary": summary,
            "tool_run_id": "",
        }

    def failed_outcome(self, summary="services_status did not complete successfully."):
        return {
            "state": "failed",
            "status": ToolRun.Status.FAILED,
            "summary": summary,
            "tool_run_id": "",
        }

    @override_settings(**LIVE_SETTINGS)
    def test_valid_live_ai_tool_proposal_auto_creates_toolrun_without_raw_block(self):
        definition = self.create_tool()
        streamed = self.post_live_with_provider_text(
            'I recommend an approved read-only services check.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Check service state without changing anything","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>',
            wait_outcome=self.timeout_outcome(),
        )

        tool_request = AdminChatToolRequest.objects.get()
        assistant_message = AdminChatMessage.objects.filter(sender_type=AdminChatMessage.SenderType.ASSISTANT).order_by("created_at").first()
        self.assertEqual(tool_request.status, AdminChatToolRequest.Status.QUEUED)
        self.assertEqual(tool_request.tool_definition, definition)
        self.assertEqual(tool_request.message, assistant_message)
        self.assertIn("Check service state", tool_request.params_redacted["reason"])
        self.assertNotIn("TOOL_REQUEST_PROPOSAL", streamed)
        self.assertNotIn("TOOL_REQUEST_PROPOSAL", assistant_message.body_redacted)
        self.assertNotIn("tool_slug", assistant_message.body_redacted)
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)
        self.assertEqual(AdminLiveAIRequestLog.objects.count(), 1)

    @override_settings(**LIVE_SETTINGS)
    def test_invalid_or_unavailable_tool_proposal_does_not_create_request(self):
        self.create_tool()
        self.post_live_with_provider_text(
            'No approved check is available.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"restart_nginx","reason":"Unsafe write action","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>'
        )

        self.assertEqual(AdminChatToolRequest.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    @override_settings(**LIVE_SETTINGS)
    def test_non_read_only_allowlisted_tool_proposal_is_rejected_before_request(self):
        self.create_tool(key="services_status", risk_level=ToolDefinition.RiskLevel.WRITE_ACTION)
        self.post_live_with_provider_text(
            'This should not be allowed.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Would not be read-only","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>'
        )

        self.assertEqual(AdminChatToolRequest.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    @override_settings(**LIVE_SETTINGS)
    def test_invalid_tool_proposal_params_do_not_create_request(self):
        self.create_tool()
        self.post_live_with_provider_text(
            'I recommend a read-only check.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Check services","params":{"command":"systemctl status nginx"}}</TOOL_REQUEST_PROPOSAL>'
        )

        self.assertEqual(AdminChatToolRequest.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    @override_settings(**LIVE_SETTINGS)
    def test_free_text_tool_name_without_proposal_does_not_execute(self):
        self.create_tool()
        self.post_live_with_provider_text("بدأت فحص services_status وسأتابع النتيجة، لكن بدون proposal block.")

        self.assertEqual(AdminChatToolRequest.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    @override_settings(**LIVE_SETTINGS)
    def test_arabic_direct_log_sources_intent_executes_without_proposal(self):
        definition = self.create_tool(key="log_sources_discovery_v2")
        full_summary = (
            "اكتمل فحص مصادر السجلات بنجاح.\n\n"
            "الخلاصة:\n"
            "- تم فحص 5 مصادر سجلات.\n"
            "- يوجد 3 مصادر متاحة.\n"
            "- يوجد 2 مصادر غير موجودة.\n\n"
            "التفسير:\n"
            "الفحص اعتمد على الميتاداتا فقط ولم يقرأ محتوى السجلات الخام."
        )
        streamed = self.post_live_with_provider_text(
            "يمكنني اقتراح إعادة فحص مصادر السجلات. هل ترغب أن أقوم باقتراح تشغيلها؟",
            request_text="افحص مصادر السجلات باستخدام أداة read-only مناسبة، وبعد انتهاء التنفيذ اعرض النتيجة بالعربية.",
            wait_outcome=self.success_outcome(full_summary),
        )

        tool_request = AdminChatToolRequest.objects.get()
        transcript = "\n".join(AdminChatMessage.objects.values_list("body_redacted", flat=True))
        self.assertEqual(tool_request.tool_definition, definition)
        self.assertEqual(tool_request.status, AdminChatToolRequest.Status.SUCCEEDED)
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)
        self.assertIn("بدأت فحص قراءة فقط", streamed)
        self.assertNotIn("يمكنني اقتراح", streamed)
        self.assertNotIn("هل ترغب", streamed)
        self.assertNotIn("يمكنني اقتراح", transcript)
        self.assertNotIn("هل ترغب", transcript)
        followup = AdminChatMessage.objects.filter(metadata_redacted__source="tool_result_summary").get()
        self.assertEqual(followup.body_redacted.count("الخلاصة:"), 1)
        self.assertEqual(followup.body_redacted.count("التفسير:"), 1)

    @override_settings(**LIVE_SETTINGS)
    def test_arabic_execute_log_sources_intent_executes_without_proposal(self):
        self.create_tool(key="log_sources_discovery_v2")
        self.post_live_with_provider_text(
            "سأقترح الفحص فقط بدون proposal.",
            request_text="نفذ فحص مصادر السجلات الآن.",
            wait_outcome=self.success_outcome("اكتمل الفحص."),
        )

        self.assertEqual(AdminChatToolRequest.objects.get().tool_definition.key, "log_sources_discovery_v2")
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)

    @override_settings(**LIVE_SETTINGS)
    def test_continue_after_prior_log_sources_scope_executes_without_proposal(self):
        self.create_tool(key="log_sources_discovery_v2")
        AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="يمكن فحص مصادر السجلات كفحص قراءة فقط.",
            metadata_redacted={"source": "admin_live_chatkit"},
        )
        self.post_live_with_provider_text(
            "تمام، سأتابع الاقتراح.",
            request_text="متابعة",
            wait_outcome=self.success_outcome("اكتمل فحص مصادر السجلات."),
        )

        self.assertEqual(AdminChatToolRequest.objects.get().tool_definition.key, "log_sources_discovery_v2")
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)

    @override_settings(**LIVE_SETTINGS)
    def test_advice_question_does_not_direct_execute_without_proposal(self):
        self.create_tool(key="log_sources_discovery_v2")
        streamed = self.post_live_with_provider_text(
            "أقترح فحص مصادر السجلات لأنه قراءة فقط.",
            request_text="ماذا تقترح؟",
        )

        self.assertIn("أقترح فحص مصادر السجلات", streamed)
        self.assertEqual(AdminChatToolRequest.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    @override_settings(**LIVE_SETTINGS)
    def test_tool_success_within_followup_adds_safe_result_summary(self):
        self.create_tool()
        self.post_live_with_provider_text(
            'I recommend a read-only services check.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Check services","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>',
            wait_outcome=self.success_outcome("Services check completed successfully without exposing raw output."),
        )
        tool_request = AdminChatToolRequest.objects.get()
        followup = AdminChatMessage.objects.filter(metadata_redacted__source="tool_result_summary").get()

        self.assertEqual(tool_request.status, AdminChatToolRequest.Status.SUCCEEDED)
        self.assertEqual(tool_request.approved_by, self.staff)
        self.assertIsNotNone(tool_request.approved_at)
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)
        self.assertEqual(tool_request.tool_run.agent_job.tool_key, "services_status")
        self.assertEqual(tool_request.tool_run.requested_by_type, ToolRun.RequestedByType.ADMIN)
        self.assertIn("اكتمل الفحص بنجاح", followup.body_redacted)
        self.assertIn("Services check completed successfully", followup.body_redacted)
        self.assertTrue((followup.metadata_redacted or {}).get("chatkit_item_id"))

    @override_settings(**LIVE_SETTINGS)
    def test_tool_failure_adds_failure_explanation(self):
        self.create_tool()
        self.post_live_with_provider_text(
            'I recommend a read-only services check.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Check services","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>',
            wait_outcome=self.failed_outcome("Scanner agent reported a safe execution failure."),
        )
        tool_request = AdminChatToolRequest.objects.get()
        followup = AdminChatMessage.objects.filter(metadata_redacted__source="tool_result_failed").get()

        self.assertEqual(tool_request.status, AdminChatToolRequest.Status.FAILED)
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)
        self.assertIn("فشل تنفيذ الفحص", followup.body_redacted)
        self.assertIn("Scanner agent reported", followup.body_redacted)

    @override_settings(**LIVE_SETTINGS)
    def test_tool_timeout_adds_current_status_explanation(self):
        self.create_tool()
        self.post_live_with_provider_text(
            'I recommend a read-only services check.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Check services","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>',
            wait_outcome=self.timeout_outcome(),
        )
        followup = AdminChatMessage.objects.filter(metadata_redacted__source="tool_result_timeout").get()

        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertEqual(AgentJob.objects.count(), 1)
        self.assertIn("لم يكتمل خلال مدة الانتظار", followup.body_redacted)
        self.assertIn("queued", followup.body_redacted)

    @override_settings(**LIVE_SETTINGS)
    def test_tool_creation_failure_does_not_claim_running_or_wait(self):
        self.create_tool()
        ScannerAgent.objects.filter(server=self.server).delete()
        self.post_live_with_provider_text(
            'I recommend a read-only services check.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Check services","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>',
        )
        followup = AdminChatMessage.objects.filter(metadata_redacted__source="tool_result_not_started").get()

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)
        self.assertIn("لم أتمكن من بدء الفحص", followup.body_redacted)
        self.assertNotIn("wait", followup.body_redacted.lower())
        self.assertNotIn("running", followup.body_redacted.lower())

    @override_settings(**LIVE_SETTINGS)
    def test_result_messages_are_streamed_and_available_in_history(self):
        self.create_tool()
        streamed = self.post_live_with_provider_text(
            'I recommend a read-only services check.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Check services","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>',
            wait_outcome=self.success_outcome("Visible streamed result summary."),
        )
        response = self.client.post(
            self.live_url(),
            data=json.dumps({"type": "items.list", "params": {"thread_id": str(self.session.id), "limit": 20, "order": "asc"}}),
            content_type="application/json",
        )

        self.assertIn("بدأت فحص قراءة فقط", streamed)
        self.assertIn("Visible streamed result summary", streamed)
        self.assertIn("Visible streamed result summary", response.content.decode())
        self.assertEqual(AdminLiveAIRequestLog.objects.count(), 1)

    @override_settings(**LIVE_SETTINGS)
    def test_multiple_tool_proposals_create_combined_final_explanation(self):
        self.create_tool(key="services_status")
        self.create_tool(key="system_identity")
        self.post_live_with_provider_text(
            'I recommend two read-only checks.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Check services","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"system_identity","reason":"Check system identity","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>',
            wait_side_effect=[
                self.success_outcome("Services check completed."),
                self.failed_outcome("System identity check failed safely."),
            ],
        )
        combined = AdminChatMessage.objects.filter(metadata_redacted__mode="combined").get()

        self.assertEqual(ToolRun.objects.count(), 2)
        self.assertEqual(AgentJob.objects.count(), 2)
        self.assertIn("services_status: نجح", combined.body_redacted)
        self.assertIn("system_identity: فشل", combined.body_redacted)

    @override_settings(**LIVE_SETTINGS)
    def test_every_live_ai_toolrun_gets_final_result_message(self):
        self.create_tool()
        self.post_live_with_provider_text(
            'I recommend a read-only services check.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Check services","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>',
            wait_outcome=self.success_outcome("Final result exists."),
        )
        tool_run = ToolRun.objects.get()

        self.assertTrue(
            AdminChatMessage.objects.filter(
                metadata_redacted__tool_run_id=str(tool_run.id),
                metadata_redacted__source__in=["tool_result_summary", "tool_result_failed", "tool_result_timeout"],
            ).exists()
        )

    def test_single_tool_wait_window_allows_22_second_success_without_timeout(self):
        definition = self.create_tool()
        tool_run = ToolRun.objects.create(
            account=self.account,
            server=self.server,
            agent=ScannerAgent.objects.get(server=self.server),
            tool_definition=definition,
            requested_by=self.staff,
            requested_by_type=ToolRun.RequestedByType.ADMIN,
            status=ToolRun.Status.QUEUED,
        )

        def refresh_side_effect():
            if tool_run.refresh_from_db.call_count >= 2:
                tool_run.status = ToolRun.Status.SUCCEEDED
                tool_run.result_redacted = {"summary": "تم العثور على مصادر سجلات آمنة."}

        with patch("apps.ai_chat.services.time.monotonic", side_effect=[0, 22]), patch(
            "apps.ai_chat.services.time.sleep"
        ), patch.object(tool_run, "refresh_from_db", side_effect=refresh_side_effect):
            outcome = wait_for_tool_execution_result(tool_run, timeout_seconds=45, poll_interval_seconds=2)

        self.assertEqual(outcome["state"], "succeeded")
        self.assertNotEqual(outcome["state"], "timeout")
        self.assertIn("مصادر سجلات", outcome["summary"])

    def test_final_grace_check_catches_success_before_timeout(self):
        definition = self.create_tool()
        tool_run = ToolRun.objects.create(
            account=self.account,
            server=self.server,
            agent=ScannerAgent.objects.get(server=self.server),
            tool_definition=definition,
            requested_by=self.staff,
            requested_by_type=ToolRun.RequestedByType.ADMIN,
            status=ToolRun.Status.QUEUED,
        )
        refresh_count = {"value": 0}

        def refresh_side_effect():
            refresh_count["value"] += 1
            if refresh_count["value"] >= 2:
                tool_run.status = ToolRun.Status.SUCCEEDED
                tool_run.result_redacted = {"summary": "اكتمل خلال مهلة السماح النهائية."}

        with patch("apps.ai_chat.services.time.monotonic", return_value=99), patch(
            "apps.ai_chat.services.time.sleep"
        ) as sleep_mock, patch.object(tool_run, "refresh_from_db", side_effect=refresh_side_effect):
            outcome = wait_for_tool_execution_result(tool_run, timeout_seconds=0, poll_interval_seconds=2)

        self.assertEqual(outcome["state"], "succeeded")
        sleep_mock.assert_called_once_with(5)

    def test_log_sources_result_summary_uses_redacted_result_counts_and_paths(self):
        definition = self.create_tool(key="log_sources_discovery_v2")
        tool_run = ToolRun.objects.create(
            account=self.account,
            server=self.server,
            agent=ScannerAgent.objects.get(server=self.server),
            tool_definition=definition,
            requested_by=self.staff,
            requested_by_type=ToolRun.RequestedByType.ADMIN,
            status=ToolRun.Status.SUCCEEDED,
            result_redacted={
                "summary": {
                    "notes": ["metadata_only", "no_content_reads"],
                    "sources_total": 5,
                    "sources_missing": 2,
                    "sources_existing": 3,
                    "permission_denied": 0,
                },
                "log_sources": [
                    {"path": "/var/log/nginx", "type": "nginx_log_dir", "exists": True, "is_dir": True},
                    {"path": "/var/log/postgresql", "type": "postgresql_log_dir", "exists": True, "is_dir": True},
                    {"path": "/var/log/syslog", "type": "system_log_file", "exists": False},
                    {"path": "/var/log/messages", "type": "system_log_file", "exists": False},
                    {"path": "/opt/taskaai-suite/tos-translation/logs", "type": "app_logs_dir", "exists": True},
                ],
            },
        )

        outcome = wait_for_tool_execution_result(tool_run, timeout_seconds=0, poll_interval_seconds=1)

        self.assertEqual(outcome["state"], "succeeded")
        self.assertIn("تم فحص 5", outcome["summary"])
        self.assertIn("يوجد 3", outcome["summary"])
        self.assertIn("يوجد 2", outcome["summary"])
        self.assertIn("/var/log/nginx", outcome["summary"])
        self.assertIn("/var/log/syslog", outcome["summary"])
        self.assertIn("الميتاداتا", outcome["summary"])
        self.assertNotIn("{", outcome["summary"])
        self.assertNotIn("completed successfully", outcome["summary"])

    def test_log_sources_result_summary_redacts_secrets_and_raw_log_content(self):
        definition = self.create_tool(key="log_sources_discovery_v2")
        tool_run = ToolRun.objects.create(
            account=self.account,
            server=self.server,
            agent=ScannerAgent.objects.get(server=self.server),
            tool_definition=definition,
            requested_by=self.staff,
            requested_by_type=ToolRun.RequestedByType.ADMIN,
            status=ToolRun.Status.SUCCEEDED,
            result_redacted={
                "summary": {
                    "notes": ["metadata_only"],
                    "sources_total": 1,
                    "sources_missing": 0,
                    "sources_existing": 1,
                    "permission_denied": 0,
                },
                "log_sources": [
                    {"path": "/var/log/nginx/sk-test-secret-token", "exists": True},
                ],
                "raw_logs": "secret raw log content should not be displayed",
            },
        )

        outcome = wait_for_tool_execution_result(tool_run, timeout_seconds=0, poll_interval_seconds=1)

        self.assertIn("[REDACTED]", outcome["summary"])
        self.assertNotIn("sk-test-secret-token", outcome["summary"])
        self.assertNotIn("secret raw log content", outcome["summary"])

    def test_multi_tool_timeout_window_scales_to_cap(self):
        self.assertEqual(tool_followup_timeout_for_count(1), 45)
        self.assertEqual(tool_followup_timeout_for_count(2), 65)
        self.assertEqual(tool_followup_timeout_for_count(10), 120)

    def test_non_staff_cannot_approve_or_reject_tool_request(self):
        self.create_tool()
        message = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="Tool request proposed.",
            metadata_redacted={"source": "admin_live_chatkit"},
        )
        tool_request = AdminChatToolRequest.objects.create(
            session=self.session,
            message=message,
            tool_definition=ToolDefinition.objects.get(key="services_status"),
            params_redacted={"tool_params": {}, "scope": "selected_server", "source": "live_ai_tool_proposal"},
        )

        with self.assertRaises(Exception):
            approve_tool_request(user=self.owner, tool_request=tool_request)
        with self.assertRaises(Exception):
            reject_tool_request(user=self.owner, tool_request=tool_request)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    @override_settings(**LIVE_SETTINGS)
    def test_history_load_does_not_create_live_ai_audit(self):
        AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.USER,
            body_redacted="Stored user message",
            metadata_redacted={"source": "admin_live_chatkit", "chatkit_item_id": "ck_user"},
        )
        response = self.client.post(
            self.live_url(),
            data=json.dumps({"type": "items.list", "params": {"thread_id": str(self.session.id), "limit": 20, "order": "asc"}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(AdminLiveAIRequestLog.objects.exists())

    def test_legacy_pending_audit_cleanup_dry_run_and_apply(self):
        old_pending = AdminLiveAIRequestLog.objects.create(
            user=self.staff,
            session=self.session,
            account=self.account,
            server=self.server,
            model="test-model",
        )
        recent_pending = AdminLiveAIRequestLog.objects.create(
            user=self.staff,
            session=self.session,
            account=self.account,
            server=self.server,
            model="test-model",
        )
        succeeded = AdminLiveAIRequestLog.objects.create(
            user=self.staff,
            session=self.session,
            account=self.account,
            server=self.server,
            model="test-model",
            status=AdminLiveAIRequestLog.Status.SUCCEEDED,
            latency_ms=1,
        )
        AdminLiveAIRequestLog.objects.filter(id=old_pending.id).update(created_at=timezone.now() - timedelta(days=3))
        stdout = io.StringIO()

        call_command("cleanup_live_ai_legacy_test_data", "--dry-run", stdout=stdout)
        old_pending.refresh_from_db()
        self.assertEqual(old_pending.status, AdminLiveAIRequestLog.Status.PENDING)
        self.assertIn("found 1", stdout.getvalue())

        call_command("cleanup_live_ai_legacy_test_data", "--apply", stdout=io.StringIO())
        old_pending.refresh_from_db()
        recent_pending.refresh_from_db()
        succeeded.refresh_from_db()
        self.assertEqual(old_pending.status, AdminLiveAIRequestLog.Status.FAILED)
        self.assertEqual(old_pending.error_class, AdminLiveAIRequestLog.ErrorClass.UNKNOWN_ERROR)
        self.assertEqual(recent_pending.status, AdminLiveAIRequestLog.Status.PENDING)
        self.assertEqual(succeeded.status, AdminLiveAIRequestLog.Status.SUCCEEDED)

    @override_settings(**LIVE_SETTINGS)
    def test_portal_customer_deterministic_chat_unchanged(self):
        portal_session = create_chat_session(user=self.owner, title="Portal deterministic", server_id=self.server.id)
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("portal:chat_session_detail", args=[portal_session.id]),
            data={"body": "server status"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AdminLiveAIRequestLog.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    @override_settings(**LIVE_SETTINGS)
    def test_live_ai_header_reflects_auto_execution_copy(self):
        response = self.client.get(reverse("admin_chat:session_detail", args=[self.session.id]))

        self.assertContains(response, "Approved read-only tools may run automatically")
        self.assertNotContains(response, "Read-only tools require explicit approval")

    @override_settings(**LIVE_SETTINGS)
    def test_secret_like_proposal_reason_is_redacted_from_transcript_and_request(self):
        self.create_tool()
        self.post_live_with_provider_text(
            'I recommend a read-only check.\n'
            '<TOOL_REQUEST_PROPOSAL>{"tool_slug":"services_status","reason":"Check sk-test-secret-token safely","params":{"scope":"selected_server"}}</TOOL_REQUEST_PROPOSAL>',
            wait_outcome=self.success_outcome("Completed without exposing sk-test-secret-output."),
        )

        transcript = "\n".join(AdminChatMessage.objects.values_list("body_redacted", flat=True))
        request_payload = str(AdminChatToolRequest.objects.get().params_redacted)
        self.assertNotIn("sk-test-secret-token", transcript)
        self.assertNotIn("sk-test-secret-token", request_payload)
        self.assertNotIn("sk-test-secret-output", transcript)
        self.assertIn("[REDACTED]", request_payload)
