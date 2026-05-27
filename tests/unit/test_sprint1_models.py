from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import Account, User
from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.plans.models import Plan
from apps.servers.models import Server
from apps.subscriptions.models import Subscription


class Sprint1ModelTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Acme", type=Account.AccountType.COMPANY)
        self.plan = Plan.objects.create(name="Starter")
        self.server = Server.objects.create(account=self.account, name="Production")

    def test_customer_user_requires_account_and_role(self):
        user = User(username="operator", email="operator@example.com", role=User.CustomerRole.OPERATOR)
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_staff_user_without_account_has_no_customer_role(self):
        user = User(username="admin", email="admin@example.com", is_staff=True, is_superuser=True)
        user.set_unusable_password()
        user.full_clean()

    def test_approved_status_values_are_available(self):
        self.assertEqual(Account.Status.values, ["active", "suspended", "archived"])
        self.assertEqual(Server.Status.values, ["pending", "active", "offline", "archived"])
        self.assertEqual(Application.ReviewStatus.values, ["pending_review", "approved", "ignored", "archived"])
        self.assertEqual(Subscription.Status.values, ["trial", "active", "past_due", "suspended", "cancelled", "expired"])

    def test_audit_log_rejects_secret_like_metadata_keys(self):
        audit_log = AuditLog(
            actor_type=AuditLog.ActorType.SYSTEM,
            account=self.account,
            action="test.event",
            result=AuditLog.Result.INFO,
            metadata={"api_key": "not-allowed"},
        )
        with self.assertRaises(ValidationError):
            audit_log.full_clean()
