import io
import json
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.ai_chat.diagnostic_bundles import get_diagnostic_bundle
from apps.ai_chat.diagnostic_summaries import summarize_diagnostic_bundle_results as build_diagnostic_bundle_summary
from apps.ai_chat.models import AdminChatMessage, AdminChatSession, AdminChatToolRequest, AdminLiveAIRequestLog
from apps.ai_chat.diagnostic_bundles import resolve_diagnostic_bundle_intent
from apps.ai_chat.services import (
    approve_tool_request,
    create_admin_chat_session,
    create_chat_session,
    execute_diagnostic_bundle_for_item,
    finalize_diagnostic_bundle_if_ready,
    reject_tool_request,
    sync_chat_tool_requests_for_tool_run,
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

    def bundle_status_url(self):
        return reverse("admin_chat:bundle_status", args=[self.session.id])

    def bundle_execution_status_url(self, bundle_execution_id):
        return reverse("admin_chat:bundle_execution_status", args=[self.session.id, bundle_execution_id])

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

    def create_server_health_tools(self, *, include_gunicorn=True, include_postgres=False, plan_enabled=True, allow_admin=True):
        keys = ["log_sources_discovery_v2", "systemd_services_discovery", "nginx_sites_discovery"]
        if include_gunicorn:
            keys.append("gunicorn_uvicorn_services_discovery")
        if include_postgres:
            keys.append("postgres_status_discovery")
        for key in keys:
            self.create_tool(key=key, plan_enabled=plan_enabled, allow_admin=allow_admin)
        return keys

    def log_sources_result(self):
        return {
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

    def test_diagnostic_bundle_resolver_prefers_broad_server_health_not_specific_log_sources(self):
        self.assertEqual(resolve_diagnostic_bundle_intent("افحص حالة السيرفر").slug, "server_health")
        self.assertEqual(resolve_diagnostic_bundle_intent("اعمل فحص شامل للسيرفر").slug, "server_health")
        self.assertIsNone(resolve_diagnostic_bundle_intent("افحص مصادر السجلات"))

    @override_settings(**LIVE_SETTINGS)
    def test_broad_server_health_request_runs_bundle_with_combined_messages(self):
        self.create_server_health_tools()
        progress_call = {"count": 0}

        def progress_side_effect(bundle_execution_id):
            progress_call["count"] += 1
            running = AdminChatMessage.objects.get(
                metadata_redacted__source="diagnostic_bundle",
                metadata_redacted__state="running",
                metadata_redacted__bundle_execution_id=bundle_execution_id,
            )
            return {
                "bundle_execution_id": bundle_execution_id,
                "running_message": running,
                "all_terminal": progress_call["count"] > 1,
                "pending_tool_keys": [] if progress_call["count"] > 1 else ["log_sources_discovery_v2", "nginx_sites_discovery"],
                "completed_tool_keys": [] if progress_call["count"] == 1 else ["log_sources_discovery_v2"],
            }

        def finalize_side_effect(bundle_execution_id, *, caller="background"):
            self.assertEqual(caller, "stream")
            running = AdminChatMessage.objects.get(
                metadata_redacted__source="diagnostic_bundle",
                metadata_redacted__state="running",
                metadata_redacted__bundle_execution_id=bundle_execution_id,
            )
            metadata = running.metadata_redacted or {}
            return AdminChatMessage.objects.create(
                session=self.session,
                sender_type=AdminChatMessage.SenderType.ASSISTANT,
                body_redacted=(
                    "اكتمل فحص صحة السيرفر.\n\n"
                    "نتائج الفحوصات:\n"
                    "- مصادر السجلات: نجح.\n"
                    "- إعدادات Nginx: نجح.\n"
                    "- خدمات Gunicorn/Uvicorn: لم يكتمل خلال المهلة.\n\n"
                    "الخلاصة العامة:\n"
                    "اكتمل جزء من الفحوصات، وتحتاج الفحوصات المتأخرة إلى مراجعة."
                ),
                metadata_redacted={
                    "source": "diagnostic_bundle",
                    "bundle_slug": metadata.get("bundle_slug"),
                    "bundle_execution_id": bundle_execution_id,
                    "state": "partial",
                    "chatkit_item_id": f"bundle_result_{bundle_execution_id}",
                },
            )

        with patch("apps.ai_chat.services.wait_for_tool_execution_result") as wait_for_result, patch(
            "apps.ai_chat.live_ai.get_diagnostic_bundle_progress",
            side_effect=progress_side_effect,
        ), patch(
            "apps.ai_chat.live_ai.finalize_diagnostic_bundle_if_ready",
            side_effect=finalize_side_effect,
        ), patch(
            "apps.ai_chat.live_ai.asyncio.sleep",
            new=AsyncMock(return_value=None),
        ):
            streamed = self.post_live_with_provider_text(
                "يمكنني اقتراح فحص صحة السيرفر.",
                request_text="افحص حالة السيرفر باستخدام الأدوات المناسبة read-only ونفذ الفحوصات تلقائيًا.",
            )
        wait_for_result.assert_not_called()
        running = AdminChatMessage.objects.get(
            metadata_redacted__source="diagnostic_bundle", metadata_redacted__state="running"
        )
        self.assertIn("بدأت فحص صحة السيرفر", streamed)
        self.assertIn("جاري تنفيذ الفحوصات", running.body_redacted)
        self.assertEqual(AdminChatToolRequest.objects.count(), 4)
        self.assertEqual(ToolRun.objects.count(), 4)
        self.assertEqual(AgentJob.objects.count(), 4)
        self.assertTrue((running.metadata_redacted or {}).get("stream_managed"))
        self.assertTrue(all((tool_request.params_redacted or {}).get("stream_managed") is True for tool_request in AdminChatToolRequest.objects.all()))
        response = self.client.post(
            self.live_url(),
            data=json.dumps({"type": "items.list", "params": {"thread_id": str(self.session.id), "limit": 30, "order": "asc"}}),
            content_type="application/json",
        )
        transcript = "\n".join(AdminChatMessage.objects.values_list("body_redacted", flat=True))
        chatkit_ids = [
            (message.metadata_redacted or {}).get("chatkit_item_id")
            for message in AdminChatMessage.objects.filter(metadata_redacted__has_key="chatkit_item_id")
        ]
        populated_ids = [item_id for item_id in chatkit_ids if item_id]

        self.assertEqual(AdminChatMessage.objects.filter(metadata_redacted__source="diagnostic_bundle", metadata_redacted__state="running").count(), 1)
        self.assertEqual(AdminChatMessage.objects.filter(metadata_redacted__source="diagnostic_bundle").exclude(metadata_redacted__state="running").count(), 1)
        self.assertEqual(AdminChatMessage.objects.filter(metadata_redacted__source="tool_orchestrator").count(), 0)
        self.assertEqual(AdminChatMessage.objects.filter(metadata_redacted__source="tool_result_summary").count(), 0)
        self.assertIn("نتائج الفحوصات", streamed)
        self.assertIn("جاري تنفيذ الفحوصات", streamed)
        self.assertIn("اكتمل فحص صحة السيرفر", streamed)
        self.assertIn("Gunicorn/Uvicorn", transcript)
        self.assertIn("لم يكتمل خلال المهلة", transcript)
        self.assertIn("فحص صحة السيرفر", response.content.decode())
        final_status = self.client.get(self.bundle_status_url()).json()
        self.assertFalse(final_status["running"])
        self.assertEqual(final_status["latest_result_execution_id"], (running.metadata_redacted or {}).get("bundle_execution_id"))
        self.assertEqual(final_status["latest_result_state"], "partial")
        explicit_final_status = self.client.get(
            self.bundle_execution_status_url((running.metadata_redacted or {}).get("bundle_execution_id"))
        ).json()
        self.assertEqual(explicit_final_status["state"], "partial")
        self.assertEqual(explicit_final_status["bundle_execution_id"], (running.metadata_redacted or {}).get("bundle_execution_id"))
        self.assertIsNotNone(explicit_final_status["final_message"])
        self.assertIn("فحص صحة السيرفر", explicit_final_status["final_message"]["body"])
        self.assertNotIn("{", explicit_final_status["final_message"]["body"])
        self.assertFalse((AdminChatMessage.objects.exclude(metadata_redacted__state="running").get().metadata_redacted or {}).get("suppress_from_history", False))
        self.assertTrue((AdminChatMessage.objects.exclude(metadata_redacted__state="running").get().metadata_redacted or {}).get("chatkit_item_id"))
        self.assertEqual(len(populated_ids), len(set(populated_ids)))
        self.assertNotIn("completed successfully", transcript)
        self.assertNotIn("TOOL_REQUEST_PROPOSAL", transcript)
        self.assertNotIn("{", transcript)

    @override_settings(**LIVE_SETTINGS)
    def test_stream_managed_bundle_sync_does_not_finalize_or_emit_individual_messages(self):
        self.create_tool(key="log_sources_discovery_v2")
        AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="ابدأ الفحص",
            metadata_redacted={"source": "admin_live_chatkit", "chatkit_item_id": "bundle_seed_guard"},
        )
        execute_diagnostic_bundle_for_item(
            user=self.staff,
            session=self.session,
            item_id="bundle_seed_guard",
            bundle_slug="server_health",
        )
        tool_run = ToolRun.objects.get()
        tool_run.status = ToolRun.Status.SUCCEEDED
        tool_run.result_redacted = {"summary": "اكتمل الفحص بأمان."}
        tool_run.started_at = timezone.now() - timedelta(seconds=4)
        tool_run.finished_at = timezone.now()
        tool_run.save(update_fields=["status", "result_redacted", "started_at", "finished_at", "updated_at"])

        with patch("apps.ai_chat.services.finalize_diagnostic_bundle_if_ready") as finalize_bundle:
            sync_chat_tool_requests_for_tool_run(tool_run)

        finalize_bundle.assert_not_called()
        self.assertEqual(AdminChatMessage.objects.filter(metadata_redacted__source="diagnostic_bundle", metadata_redacted__state="running").count(), 1)
        self.assertEqual(AdminChatMessage.objects.filter(metadata_redacted__source="tool_result_summary").count(), 0)

    @override_settings(**LIVE_SETTINGS)
    def test_bundle_execution_status_endpoint_rejects_other_session_access(self):
        self.create_server_health_tools()
        AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="ابدأ الفحص",
            metadata_redacted={"source": "admin_live_chatkit", "chatkit_item_id": "bundle_seed_other"},
        )
        execute_diagnostic_bundle_for_item(
            user=self.staff,
            session=self.session,
            item_id="bundle_seed_other",
            bundle_slug="server_health",
        )
        running = AdminChatMessage.objects.get(
            metadata_redacted__source="diagnostic_bundle", metadata_redacted__state="running"
        )
        other_session = create_admin_chat_session(
            user=self.staff,
            account_id=self.account.id,
            title="Other bundle session",
            server_id=self.server.id,
        )
        response = self.client.get(
            reverse(
                "admin_chat:bundle_execution_status",
                args=[other_session.id, (running.metadata_redacted or {}).get("bundle_execution_id")],
            )
        )

        self.assertEqual(response.status_code, 404)

    @override_settings(**LIVE_SETTINGS)
    def test_bundle_skips_unavailable_and_disallowed_tools_in_summary(self):
        self.create_tool(key="log_sources_discovery_v2")
        self.create_tool(key="systemd_services_discovery", plan_enabled=False)
        AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="ابدأ الفحص",
            metadata_redacted={"source": "admin_live_chatkit", "chatkit_item_id": "bundle_seed_skip"},
        )
        execute_diagnostic_bundle_for_item(
            user=self.staff,
            session=self.session,
            item_id="bundle_seed_skip",
            bundle_slug="server_health",
        )
        tool_run = ToolRun.objects.get()
        tool_run.status = ToolRun.Status.SUCCEEDED
        tool_run.result_redacted = {"summary": "اكتمل الفحص بأمان."}
        tool_run.save(update_fields=["status", "result_redacted", "updated_at"])
        sync_chat_tool_requests_for_tool_run(tool_run)
        running = AdminChatMessage.objects.get(
            metadata_redacted__source="diagnostic_bundle",
            metadata_redacted__state="running",
        )
        final_message = finalize_diagnostic_bundle_if_ready(
            (running.metadata_redacted or {}).get("bundle_execution_id"),
            caller="recovery",
        )

        self.assertEqual(AdminChatToolRequest.objects.count(), 1)
        self.assertEqual(ToolRun.objects.count(), 1)
        self.assertIn("تم تخطيه", final_message.body_redacted)
        self.assertIn("systemd", final_message.body_redacted)
        self.assertIn("\u0627\u0644\u0641\u062d\u0648\u0635\u0627\u062a \u0627\u0644\u0645\u0646\u0641\u0630\u0629", final_message.body_redacted)
        self.assertIn("\u0627\u0644\u0641\u062d\u0648\u0635\u0627\u062a \u0627\u0644\u0645\u062a\u062e\u0637\u0627\u0629 \u0623\u0648 \u063a\u064a\u0631 \u0627\u0644\u0645\u0643\u062a\u0645\u0644\u0629", final_message.body_redacted)
        self.assertIn("\u0627\u0644\u062a\u0642\u064a\u064a\u0645 \u0627\u0644\u0639\u0627\u0645", final_message.body_redacted)
        self.assertIn("\u0627\u0644\u062e\u0637\u0648\u0629 \u0627\u0644\u0645\u0642\u062a\u0631\u062d\u0629", final_message.body_redacted)
        self.assertNotIn("['", final_message.body_redacted)
        self.assertEqual((final_message.metadata_redacted or {}).get("summary_quality"), "structured_v1")
        self.assertEqual((final_message.metadata_redacted or {}).get("executed_count"), 1)
        self.assertEqual((final_message.metadata_redacted or {}).get("skipped_count"), 4)
        self.assertEqual((final_message.metadata_redacted or {}).get("failed_count"), 0)
        self.assertEqual((final_message.metadata_redacted or {}).get("timeout_count"), 0)
        self.assertEqual((final_message.metadata_redacted or {}).get("total_count"), 5)

    @override_settings(**LIVE_SETTINGS)
    def test_structured_bundle_summary_includes_duration_when_available(self):
        bundle = get_diagnostic_bundle("server_health")

        class StubToolRun:
            def __init__(self):
                self.started_at = timezone.now() - timedelta(seconds=4)
                self.finished_at = timezone.now()
                self.created_at = self.started_at

        summary = build_diagnostic_bundle_summary(
            bundle,
            [
                {
                    "kind": "tool",
                    "tool_key": "log_sources_discovery_v2",
                    "state": "succeeded",
                    "status": ToolRun.Status.SUCCEEDED,
                    "tool_run": StubToolRun(),
                    "summary": "Safe summary",
                },
                {
                    "kind": "tool",
                    "tool_key": "systemd_services_discovery",
                    "state": "skipped",
                    "reason": "Tool is not available to this role, plan, policy, and server.",
                },
            ],
        )

        self.assertIn("\u062e\u0644\u0627\u0644 4 \u062b\u0648\u0627\u0646\u064d", summary)
        self.assertIn("\u062a\u0645 \u062a\u062e\u0637\u064a\u0647 \u0644\u0623\u0646\u0647 \u063a\u064a\u0631 \u0645\u062a\u0627\u062d", summary)
        self.assertNotIn("['", summary)
        self.assertNotIn("{", summary)

    @override_settings(**LIVE_SETTINGS)
    def test_structured_bundle_summary_uses_created_at_fallback_as_approximate_duration(self):
        bundle = get_diagnostic_bundle("server_health")

        class StubToolRun:
            def __init__(self):
                self.started_at = None
                self.created_at = timezone.now() - timedelta(seconds=19)
                self.finished_at = timezone.now()

        summary = build_diagnostic_bundle_summary(
            bundle,
            [
                {
                    "kind": "tool",
                    "tool_key": "log_sources_discovery_v2",
                    "state": "succeeded",
                    "status": ToolRun.Status.SUCCEEDED,
                    "tool_run": StubToolRun(),
                    "summary": "Safe summary",
                }
            ],
        )

        self.assertIn("\u062e\u0644\u0627\u0644 \u062d\u0648\u0627\u0644\u064a 19 \u062b\u0627\u0646\u064a\u0629", summary)
        self.assertNotIn("\u0644\u0645 \u062a\u062a\u0648\u0641\u0631 \u0645\u062f\u0629 \u0627\u0644\u062a\u0646\u0641\u064a\u0630", summary)
        self.assertNotIn("['", summary)
        self.assertNotIn("{", summary)

    @override_settings(**LIVE_SETTINGS)
    def test_structured_bundle_summary_reports_missing_duration_when_no_time_fields_exist(self):
        bundle = get_diagnostic_bundle("server_health")

        summary = build_diagnostic_bundle_summary(
            bundle,
            [
                {
                    "kind": "tool",
                    "tool_key": "log_sources_discovery_v2",
                    "state": "succeeded",
                    "status": ToolRun.Status.SUCCEEDED,
                    "summary": "Safe summary",
                }
            ],
        )

        self.assertIn("\u0644\u0645 \u062a\u062a\u0648\u0641\u0631 \u0645\u062f\u0629 \u0627\u0644\u062a\u0646\u0641\u064a\u0630", summary)
        self.assertNotIn("['", summary)
        self.assertNotIn("{", summary)

    @override_settings(**LIVE_SETTINGS)
    def test_bundle_timeout_uses_normalized_status_and_safe_metadata(self):
        self.create_tool(key="log_sources_discovery_v2")
        AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="Ø§Ø¨Ø¯Ø£ Ø§Ù„ÙØ­Øµ",
            metadata_redacted={"source": "admin_live_chatkit", "chatkit_item_id": "bundle_seed_timeout"},
        )
        execute_diagnostic_bundle_for_item(
            user=self.staff,
            session=self.session,
            item_id="bundle_seed_timeout",
            bundle_slug="server_health",
        )
        tool_run = ToolRun.objects.get()
        tool_run.status = ToolRun.Status.TIMEOUT
        tool_run.started_at = timezone.now() - timedelta(seconds=31)
        tool_run.finished_at = timezone.now()
        tool_run.save(update_fields=["status", "started_at", "finished_at", "updated_at"])
        sync_chat_tool_requests_for_tool_run(tool_run)
        running = AdminChatMessage.objects.get(
            metadata_redacted__source="diagnostic_bundle",
            metadata_redacted__state="running",
        )
        final_message = finalize_diagnostic_bundle_if_ready(
            (running.metadata_redacted or {}).get("bundle_execution_id"),
            caller="recovery",
        )

        self.assertIn("\u0627\u0646\u062a\u0647\u062a \u0627\u0644\u0645\u0647\u0644\u0629", final_message.body_redacted)
        self.assertIn("\u062e\u0644\u0627\u0644 31 \u062b\u0627\u0646\u064a\u0629", final_message.body_redacted)
        self.assertEqual((final_message.metadata_redacted or {}).get("timeout_count"), 1)
        self.assertEqual((final_message.metadata_redacted or {}).get("executed_count"), 1)
        self.assertNotIn("{", final_message.body_redacted)

    @override_settings(**LIVE_SETTINGS)
    def test_bundle_advice_question_does_not_execute(self):
        self.create_server_health_tools()
        streamed = self.post_live_with_provider_text(
            "أقترح فحص صحة السيرفر كحزمة قراءة فقط.",
            request_text="ماذا تقترح؟",
        )

        self.assertIn("أقترح فحص صحة السيرفر", streamed)
        self.assertEqual(AdminChatToolRequest.objects.count(), 0)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AdminChatMessage.objects.filter(metadata_redacted__source="diagnostic_bundle").count(), 0)

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

    @override_settings(**LIVE_SETTINGS)
    def test_tool_result_sync_does_not_add_generic_success_after_detailed_summary(self):
        self.create_tool(key="log_sources_discovery_v2")
        detailed_summary = (
            "اكتمل فحص مصادر السجلات بنجاح.\n\n"
            "الخلاصة:\n"
            "- تم فحص 5 مصادر سجلات.\n"
            "- يوجد 3 مصادر متاحة.\n"
            "- يوجد 2 مصادر غير موجودة.\n\n"
            "المصادر الموجودة:\n"
            "- /var/log/nginx\n\n"
            "المصادر غير الموجودة:\n"
            "- /var/log/syslog\n\n"
            "التفسير:\n"
            "الفحص اعتمد على الميتاداتا فقط ولم يقرأ محتوى السجلات الخام."
        )
        self.post_live_with_provider_text(
            "يمكنني اقتراح فحص مصادر السجلات. هل ترغب؟",
            request_text="افحص مصادر السجلات",
            wait_outcome=self.success_outcome(detailed_summary),
        )
        tool_run = ToolRun.objects.get()
        tool_run.status = ToolRun.Status.SUCCEEDED
        tool_run.result_redacted = self.log_sources_result()
        tool_run.save(update_fields=["status", "result_redacted", "updated_at"])

        sync_chat_tool_requests_for_tool_run(tool_run)
        sync_chat_tool_requests_for_tool_run(tool_run)
        response = self.client.post(
            self.live_url(),
            data=json.dumps({"type": "items.list", "params": {"thread_id": str(self.session.id), "limit": 20, "order": "asc"}}),
            content_type="application/json",
        )
        transcript = "\n".join(AdminChatMessage.objects.values_list("body_redacted", flat=True))
        history = response.content.decode()

        self.assertEqual(
            AdminChatMessage.objects.filter(
                metadata_redacted__source="tool_result_summary",
                metadata_redacted__tool_run_id=str(tool_run.id),
                metadata_redacted__tool_request_id=str(AdminChatToolRequest.objects.get().id),
            ).count(),
            1,
        )
        self.assertEqual(
            AdminChatMessage.objects.filter(
                metadata_redacted__source="tool_orchestrator",
                metadata_redacted__tool_request_id=str(AdminChatToolRequest.objects.get().id),
            ).count(),
            1,
        )
        chatkit_ids = [
            (message.metadata_redacted or {}).get("chatkit_item_id")
            for message in AdminChatMessage.objects.filter(metadata_redacted__has_key="chatkit_item_id")
        ]
        populated_ids = [item_id for item_id in chatkit_ids if item_id]
        self.assertEqual(len(populated_ids), len(set(populated_ids)))
        self.assertNotIn("log_sources_discovery_v2 completed successfully.", transcript)
        self.assertNotIn("log_sources_discovery_v2 completed successfully.", history)
        self.assertIn("اكتمل فحص مصادر السجلات بنجاح", history)
        self.assertNotIn("{", transcript)

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

    def test_cleanup_removes_only_legacy_generic_duplicate_tool_messages(self):
        generic = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="log_sources_discovery_v2 completed successfully.",
            metadata_redacted={
                "source": "tool_result_summary",
                "tool_run_id": "run-legacy",
                "tool_key": "log_sources_discovery_v2",
            },
        )
        detailed = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="اكتمل فحص مصادر السجلات بنجاح.\n\nالخلاصة:\n- تم فحص 5 مصادر سجلات.",
            metadata_redacted={
                "source": "tool_result_summary",
                "tool_run_id": "run-legacy",
                "tool_key": "log_sources_discovery_v2",
                "chatkit_item_id": "tool_result_legacy",
            },
        )
        unrelated_without_pair = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="services_status completed successfully.",
            metadata_redacted={
                "source": "tool_result_summary",
                "tool_run_id": "run-other",
                "tool_key": "services_status",
            },
        )
        generic_with_chatkit_id = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="log_sources_discovery_v2 completed successfully.",
            metadata_redacted={
                "source": "tool_result_summary",
                "tool_run_id": "run-kept",
                "tool_key": "log_sources_discovery_v2",
                "chatkit_item_id": "tool_result_kept",
            },
        )
        AdminChatMessage.objects.filter(id=generic.id).update(created_at=timezone.now() - timedelta(minutes=5))
        stdout = io.StringIO()

        call_command("cleanup_live_ai_legacy_test_data", "--dry-run", stdout=stdout)
        self.assertIn("found 1 legacy generic duplicate tool result message", stdout.getvalue())
        self.assertTrue(AdminChatMessage.objects.filter(id=generic.id).exists())

        call_command("cleanup_live_ai_legacy_test_data", "--apply", stdout=io.StringIO())

        self.assertFalse(AdminChatMessage.objects.filter(id=generic.id).exists())
        self.assertTrue(AdminChatMessage.objects.filter(id=detailed.id).exists())
        self.assertTrue(AdminChatMessage.objects.filter(id=unrelated_without_pair.id).exists())
        self.assertTrue(AdminChatMessage.objects.filter(id=generic_with_chatkit_id.id).exists())

    def test_cleanup_removes_duplicate_detailed_tool_messages_and_keeps_best_metadata(self):
        older_duplicate = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="اكتمل فحص مصادر السجلات بنجاح.\n\nالخلاصة:\n- تم فحص 5 مصادر سجلات.",
            metadata_redacted={
                "source": "tool_result_summary",
                "tool_run_id": "run-detailed",
                "tool_request_id": "request-detailed",
                "tool_key": "log_sources_discovery_v2",
                "chatkit_item_id": "tool_result_request-detailed",
            },
        )
        best = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="اكتمل فحص مصادر السجلات بنجاح.\n\nالخلاصة:\n- تم فحص 5 مصادر سجلات.\n\nالتفسير:\nقراءة فقط.",
            metadata_redacted={
                "source": "tool_result_summary",
                "tool_run_id": "run-detailed",
                "tool_request_id": "request-detailed",
                "tool_key": "log_sources_discovery_v2",
                "chatkit_item_id": "tool_result_request-detailed",
                "state": "succeeded",
                "status": "succeeded",
            },
        )
        unique = AdminChatMessage.objects.create(
            session=self.session,
            sender_type=AdminChatMessage.SenderType.ASSISTANT,
            body_redacted="اكتمل فحص مصادر السجلات بنجاح.\n\nالخلاصة:\n- تم فحص 1 مصادر سجلات.",
            metadata_redacted={
                "source": "tool_result_summary",
                "tool_run_id": "run-unique",
                "tool_request_id": "request-unique",
                "tool_key": "log_sources_discovery_v2",
                "chatkit_item_id": "tool_result_request-unique",
            },
        )
        AdminChatMessage.objects.filter(id=older_duplicate.id).update(created_at=timezone.now() - timedelta(minutes=5))
        stdout = io.StringIO()

        call_command("cleanup_live_ai_legacy_test_data", "--dry-run", stdout=stdout)
        self.assertIn("found 1 duplicate detailed tool result message", stdout.getvalue())
        self.assertTrue(AdminChatMessage.objects.filter(id=older_duplicate.id).exists())

        call_command("cleanup_live_ai_legacy_test_data", "--apply", stdout=io.StringIO())

        self.assertFalse(AdminChatMessage.objects.filter(id=older_duplicate.id).exists())
        self.assertTrue(AdminChatMessage.objects.filter(id=best.id).exists())
        self.assertTrue(AdminChatMessage.objects.filter(id=unique.id).exists())

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
