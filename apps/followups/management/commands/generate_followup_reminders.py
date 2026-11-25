from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.followups.models import FollowUp, FollowUpStatus
from apps.notifications.models import Notification, NotificationType


class Command(BaseCommand):
    help = (
        "Scheduled maintenance: sends a reminder notification for follow-ups "
        "due within the next hour, and an overdue notification for pending "
        "follow-ups whose time has passed. Intended to be run periodically "
        "via OS scheduler / cron (no Celery/Redis required)."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        soon = now + timedelta(hours=1)

        due_soon = FollowUp.objects.filter(
            status=FollowUpStatus.PENDING, reminder_sent=False, scheduled_at__gte=now, scheduled_at__lte=soon
        )
        reminder_count = 0
        for f in due_soon:
            Notification.objects.create(
                recipient=f.assigned_to,
                notification_type=NotificationType.FOLLOW_UP_REMINDER,
                title="Follow-up reminder",
                message=f"Callback for {f.lead.student_name} is due at {f.scheduled_at.strftime('%H:%M')}.",
                link=f"/leads/{f.lead_id}/",
            )
            f.reminder_sent = True
            f.save(update_fields=["reminder_sent"])
            reminder_count += 1

        overdue = FollowUp.objects.filter(status=FollowUpStatus.PENDING, scheduled_at__lt=now)
        overdue_count = 0
        for f in overdue:
            already_notified = Notification.objects.filter(
                recipient=f.assigned_to,
                notification_type=NotificationType.FOLLOW_UP_OVERDUE,
                link=f"/leads/{f.lead_id}/",
                created_at__gte=now - timedelta(hours=12),
            ).exists()
            if already_notified:
                continue
            Notification.objects.create(
                recipient=f.assigned_to,
                notification_type=NotificationType.FOLLOW_UP_OVERDUE,
                title="Overdue follow-up",
                message=f"Callback for {f.lead.student_name} was due at {f.scheduled_at.strftime('%d %b, %H:%M')}.",
                link=f"/leads/{f.lead_id}/",
            )
            overdue_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Sent {reminder_count} upcoming reminder(s) and {overdue_count} overdue alert(s).")
        )
