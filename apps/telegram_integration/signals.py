from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.bootstrap.models import BootstrapSession
from apps.servers.models import BaselineScan, Finding, Server

from .models import TelegramNotification
from .services import notifications_for_account


@receiver(post_save, sender=Finding)
def notify_high_finding_created(sender, instance, created, **kwargs):
    if not created:
        return
    if str(instance.severity).lower() not in {"critical", "high"}:
        return
    notifications_for_account(
        instance.account,
        TelegramNotification.NotificationType.FINDING_CREATED,
        server=instance.server,
        finding=instance,
        payload={
            "message": "High-severity finding created",
            "title": instance.title,
            "severity": instance.severity,
            "status": instance.status,
            "evidence_summary": instance.evidence_summary,
        },
        dedupe_key=f"finding:{instance.id}",
    )


@receiver(post_save, sender=BaselineScan)
def notify_baseline_completed(sender, instance, created, **kwargs):
    if instance.status != BaselineScan.Status.SUCCEEDED:
        return
    notifications_for_account(
        instance.account,
        TelegramNotification.NotificationType.BASELINE_COMPLETED,
        server=instance.server,
        payload={
            "message": "Baseline scan completed",
            "status": instance.status,
            "summary": instance.summary,
        },
        dedupe_key=f"baseline:{instance.id}:{instance.status}",
    )


@receiver(post_save, sender=BootstrapSession)
def notify_bootstrap_terminal(sender, instance, created, **kwargs):
    if instance.status == BootstrapSession.Status.COMPLETED:
        notification_type = TelegramNotification.NotificationType.BOOTSTRAP_COMPLETED
        message = "Remote bootstrap completed"
    elif instance.status == BootstrapSession.Status.FAILED:
        notification_type = TelegramNotification.NotificationType.BOOTSTRAP_FAILED
        message = "Remote bootstrap failed"
    else:
        return
    notifications_for_account(
        instance.account,
        notification_type,
        server=instance.server,
        payload={"message": message, "status": instance.status},
        dedupe_key=f"bootstrap:{instance.id}:{instance.status}",
    )


@receiver(pre_save, sender=Server)
def remember_previous_agent_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_agent_status = ""
        return
    previous = Server.objects.filter(pk=instance.pk).values_list("agent_status", flat=True).first()
    instance._previous_agent_status = previous or ""


@receiver(post_save, sender=Server)
def notify_agent_status_change(sender, instance, created, **kwargs):
    if created:
        return
    previous = getattr(instance, "_previous_agent_status", "") or ""
    current = instance.agent_status or ""
    if previous == current:
        return
    if current == "offline":
        notification_type = TelegramNotification.NotificationType.AGENT_OFFLINE
        message = "Scanner agent is offline"
    elif previous == "offline" and current and current != "offline":
        notification_type = TelegramNotification.NotificationType.AGENT_RECOVERED
        message = "Scanner agent recovered"
    else:
        return
    notifications_for_account(
        instance.account,
        notification_type,
        server=instance,
        payload={"message": message, "agent_status": current},
        dedupe_key=f"server:{instance.id}:agent:{current}",
    )
