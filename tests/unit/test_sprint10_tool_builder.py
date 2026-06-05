from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.accounts.models import Account, User
from apps.audit.models import AuditLog
from apps.plans.models import Plan
from apps.servers.models import AgentJob
from apps.tools.models import (
    PlanTool,
    ToolBuildProposal,
    ToolBuildRequest,
    ToolBuildReview,
    ToolDefinition,
    ToolRun,
)
from apps.tools.services import (
    ToolBuildValidationError,
    convert_tool_build_proposal,
    generate_tool_build_proposal,
    review_tool_build_proposal,
    validate_tool_build_proposal,
)
from apps.tools.setup import ensure_system_identity_tool
from apps.tools.validation import ToolParamValidationError, validate_params, validate_path_policy


class Sprint10ToolBuilderTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = get_user_model().objects.create_superuser(
            username="matrix-admin",
            email="admin@example.com",
            password="password",
        )
        self.account = Account.objects.create(name="Customer")
        self.customer = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="password",
            account=self.account,
            role=User.CustomerRole.OWNER,
        )
        self.plan = Plan.objects.create(name="Starter")
        ensure_system_identity_tool()

    def make_request(self, *, key="custom_identity_check", handler="system_identity", description="Check host identity."):
        return ToolBuildRequest.objects.create(
            requested_by=self.admin,
            title="Custom identity check",
            description_redacted=description,
            desired_tool_key=key,
            desired_handler_key=handler,
        )

    def make_command_request(
        self,
        *,
        key="apache_5xx_summary",
        argv=None,
        allowed_binaries=None,
        blocked_tokens=None,
        description="Count Apache 5xx responses safely.",
    ):
        return ToolBuildRequest.objects.create(
            requested_by=self.admin,
            title="Apache 5xx summary",
            description_redacted=description,
            desired_tool_key=key,
            desired_handler_key="",
            desired_execution_type="command_template",
            command_argv_template=argv or ["apachectl", "-S"],
            allowed_binaries=allowed_binaries or ["apachectl"],
            blocked_tokens=blocked_tokens or [";", "&&", "||", "|", ">", "<", "`", "$"],
            expected_output_description_redacted="Returns safe counters and summary only.",
        )

    def make_proposal(self, **definition_overrides):
        build_request = self.make_request()
        proposal = generate_tool_build_proposal(build_request, actor_user=self.admin)
        data = proposal.proposed_definition
        data["definition"].update(definition_overrides)
        proposal.proposed_definition = data
        proposal.save(update_fields=["proposed_definition", "updated_at"])
        return proposal

    def test_customer_and_non_staff_cannot_access_tool_builder_admin(self):
        self.client.force_login(self.customer)

        response = self.client.get("/admin/tools/toolbuildrequest/")
        portal_response = self.client.get("/portal/tools/builder/")

        self.assertIn(response.status_code, {302, 403})
        self.assertIn(portal_response.status_code, {302, 403, 404})

    def test_staff_superuser_can_access_tool_builder_admin(self):
        self.client.force_login(self.admin)

        response = self.client.get("/admin/tools/toolbuildrequest/")

        self.assertEqual(response.status_code, 200)

    def test_proposal_stores_no_secrets_and_audit_metadata_is_safe(self):
        build_request = self.make_request(description="password=secret token=abc APP_KEY=base64:secret")

        proposal = generate_tool_build_proposal(build_request, actor_user=self.admin)
        build_request.refresh_from_db()

        rendered = str(proposal.proposed_definition)
        self.assertNotIn("password=secret", build_request.description_redacted)
        self.assertNotIn("token=abc", rendered)
        self.assertNotIn("base64:secret", rendered)
        for audit in AuditLog.objects.filter(action__startswith="tool_builder."):
            self.assertNotIn("secret", str(audit.metadata).lower())
            self.assertNotIn("token", str(audit.metadata).lower())

    def test_non_read_only_proposal_rejected(self):
        proposal = self.make_proposal(risk_level=ToolDefinition.RiskLevel.WRITE_ACTION)

        passed = validate_tool_build_proposal(proposal, actor_user=self.admin)

        self.assertFalse(passed)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ToolBuildProposal.Status.VALIDATION_FAILED)

    def test_unknown_handler_rejected(self):
        build_request = self.make_request(handler="unknown_handler")

        proposal = generate_tool_build_proposal(build_request, actor_user=self.admin)

        self.assertEqual(proposal.status, ToolBuildProposal.Status.VALIDATION_FAILED)
        self.assertIn("Unknown runtime handler key.", proposal.validation_errors)

    def test_shell_free_command_fields_rejected(self):
        proposal = self.make_proposal(input_schema={"fields": {"shell_command": {"type": "string"}}})

        passed = validate_tool_build_proposal(proposal, actor_user=self.admin)

        self.assertFalse(passed)
        self.assertTrue(any("not allowed" in error for error in proposal.validation_errors))

    def test_unsafe_params_rejected(self):
        proposal = self.make_proposal(input_schema={"fields": {"restart_service": {"type": "string"}}})

        passed = validate_tool_build_proposal(proposal, actor_user=self.admin)

        self.assertFalse(passed)

    def test_missing_timeout_and_output_caps_rejected(self):
        proposal = self.make_proposal(timeout_seconds=0, max_output_bytes=0)

        passed = validate_tool_build_proposal(proposal, actor_user=self.admin)

        self.assertFalse(passed)
        self.assertIn("Timeout is required.", proposal.validation_errors)
        self.assertIn("Max output cap is required.", proposal.validation_errors)

    def test_blocked_paths_are_enforced_before_allowed_paths_after_conversion(self):
        proposal = self.make_proposal(
            input_schema={"fields": {"target_path": {"type": "path"}}, "required": ["target_path"]},
            requires_path_policy=True,
            allowed_path_prefixes=["/"],
            blocked_path_prefixes=["/etc"],
        )
        validate_tool_build_proposal(proposal, actor_user=self.admin)
        review_tool_build_proposal(proposal, reviewer=self.admin, decision=ToolBuildReview.Decision.APPROVED)
        tool_definition = convert_tool_build_proposal(proposal, actor_user=self.admin)
        params, path_values = validate_params(tool_definition.input_schema, {"target_path": "/etc/../etc/shadow"})

        self.assertEqual(params["target_path"], "/etc/shadow")
        with self.assertRaises(ToolParamValidationError):
            validate_path_policy(tool_definition, path_values)

    def test_approved_proposal_converts_to_draft_tool_definition_only(self):
        proposal = self.make_proposal()
        review_tool_build_proposal(proposal, reviewer=self.admin, decision=ToolBuildReview.Decision.APPROVED)

        tool_definition = convert_tool_build_proposal(proposal, actor_user=self.admin)

        self.assertEqual(tool_definition.status, ToolDefinition.Status.DRAFT)
        self.assertEqual(tool_definition.risk_level, ToolDefinition.RiskLevel.READ_ONLY)
        self.assertFalse(tool_definition.policy.is_active)
        self.assertFalse(tool_definition.policy.allow_customer_run)
        self.assertFalse(tool_definition.policy.allow_admin_run)
        self.assertFalse(tool_definition.policy.allow_agent_run)

    def test_no_automatic_enablement_or_plan_attachment(self):
        proposal = self.make_proposal(key="custom_no_plan")
        review_tool_build_proposal(proposal, reviewer=self.admin, decision=ToolBuildReview.Decision.APPROVED)

        tool_definition = convert_tool_build_proposal(proposal, actor_user=self.admin)

        self.assertNotEqual(tool_definition.status, ToolDefinition.Status.ENABLED)
        self.assertFalse(PlanTool.objects.filter(plan=self.plan, tool_definition=tool_definition).exists())

    def test_no_toolrun_agentjob_or_customer_server_execution(self):
        proposal = self.make_proposal(key="custom_no_execution")
        review_tool_build_proposal(proposal, reviewer=self.admin, decision=ToolBuildReview.Decision.APPROVED)

        convert_tool_build_proposal(proposal, actor_user=self.admin)

        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_existing_tool_policy_remains_source_of_truth(self):
        proposal = self.make_proposal(key="custom_source_of_truth")
        review_tool_build_proposal(proposal, reviewer=self.admin, decision=ToolBuildReview.Decision.APPROVED)

        tool_definition = convert_tool_build_proposal(proposal, actor_user=self.admin)

        self.assertFalse(tool_definition.is_enabled_for_mvp)
        self.assertFalse(tool_definition.policy.is_active)
        self.assertEqual(ToolRun.objects.count(), 0)

    def test_rejected_or_invalid_proposal_cannot_convert(self):
        proposal = self.make_proposal(key="custom_rejected")
        review_tool_build_proposal(proposal, reviewer=self.admin, decision=ToolBuildReview.Decision.REJECTED)

        with self.assertRaises(ToolBuildValidationError):
            convert_tool_build_proposal(proposal, actor_user=self.admin)

    def test_command_template_proposal_is_generated_and_stays_inactive(self):
        build_request = self.make_command_request()

        proposal = generate_tool_build_proposal(build_request, actor_user=self.admin)

        self.assertEqual(proposal.status, ToolBuildProposal.Status.PENDING_REVIEW)
        self.assertEqual(proposal.proposed_definition["definition"]["execution_type"], "command_template")
        self.assertEqual(proposal.proposed_definition["definition"]["command_argv_template"], ["apachectl", "-S"])
        self.assertEqual(proposal.proposed_definition["definition"]["allowed_binaries"], ["apachectl"])
        self.assertFalse(proposal.proposed_policy["is_active"])
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)

    def test_command_template_rejects_dangerous_delete_restart_install_patterns(self):
        build_request = self.make_command_request(argv=["systemctl", "restart", "nginx"], allowed_binaries=["systemctl"])

        proposal = generate_tool_build_proposal(build_request, actor_user=self.admin)

        self.assertEqual(proposal.status, ToolBuildProposal.Status.VALIDATION_FAILED)
        self.assertTrue(any("forbidden" in error.lower() for error in proposal.validation_errors))

    def test_command_template_rejects_shell_free_form_command(self):
        build_request = self.make_command_request(argv=["apachectl && rm -rf /"], allowed_binaries=["apachectl"])

        proposal = generate_tool_build_proposal(build_request, actor_user=self.admin)

        self.assertEqual(proposal.status, ToolBuildProposal.Status.VALIDATION_FAILED)
        self.assertTrue(any("argv-only" in error.lower() or "allowlisted" in error.lower() for error in proposal.validation_errors))

    def test_command_template_can_convert_to_draft_definition_only(self):
        proposal = generate_tool_build_proposal(self.make_command_request(key="apache_status_summary"), actor_user=self.admin)
        review_tool_build_proposal(proposal, reviewer=self.admin, decision=ToolBuildReview.Decision.APPROVED)

        tool_definition = convert_tool_build_proposal(proposal, actor_user=self.admin)

        self.assertEqual(tool_definition.status, ToolDefinition.Status.DRAFT)
        self.assertEqual(tool_definition.execution_type, "command_template")
        self.assertEqual(tool_definition.command_argv_template, ["apachectl", "-S"])
        self.assertFalse(tool_definition.policy.is_active)
        self.assertEqual(ToolRun.objects.count(), 0)
        self.assertEqual(AgentJob.objects.count(), 0)
