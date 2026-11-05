from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from deposits.models import Reminder
from deposits.services import sync_reminders
from tenancies.models import Tenancy


class Command(BaseCommand):
    help = 'Refresh deadline reminders and email any that are due.'

    def handle(self, *args, **options):
        for tenancy in Tenancy.objects.all():
            sync_reminders(tenancy)
        due = Reminder.objects.filter(
            due_on__lte=timezone.localdate(),
            sent_at__isnull=True,
            completed_at__isnull=True,
        ).select_related('tenancy__unit__property__landlord')
        sent = 0
        for reminder in due:
            landlord = reminder.tenancy.unit.property.landlord
            send_mail(
                subject=reminder.headline,
                message=f'{reminder.detail}\n\nOpen By the Book to deal with it.\n\n{settings.NOT_LEGAL_ADVICE}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[landlord.email],
                fail_silently=False,
            )
            reminder.sent_at = timezone.now()
            reminder.save(update_fields=['sent_at'])
            sent += 1
        self.stdout.write(self.style.SUCCESS(f'Sent {sent} reminder(s).'))
