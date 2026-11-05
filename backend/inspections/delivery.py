from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from deposits.services import sync_reminders
from inspections.pdf import render_inspection_pdf
from inspections.services import finalize_blockers


def email_inspection_copy(inspection) -> str:
    """Email the PDF to the landlord and any tenant with an address.

    Returns a warning string when nothing could be sent. An empty string means
    at least the landlord received a copy.
    """
    tenancy = inspection.tenancy
    landlord = tenancy.unit.property.landlord
    recipients = [landlord.email]
    recipients.extend(email for email in tenancy.tenants.values_list('email', flat=True) if email)
    prop = tenancy.unit.property
    kind = inspection.get_inspection_type_display()
    message = EmailMessage(
        subject=f'{kind} inspection report — {prop.street_address}',
        body=(
            f'A copy of the {kind.lower()} inspection report is attached.\n\n'
            f'{settings.NOT_LEGAL_ADVICE}'
        ),
        to=recipients,
    )
    filename = f'{inspection.inspection_type}-v{inspection.version}.pdf'
    message.attach(filename, render_inspection_pdf(inspection), 'application/pdf')
    tenant_emails = [email for email in tenancy.tenants.values_list('email', flat=True) if email]
    try:
        message.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001 — surface mail failure without losing the signed report
        inspection.copy_warning = str(exc)
        inspection.save(update_fields=['copy_warning'])
        return 'The report is finished, but the copy could not be emailed. Download it and send it yourself.'
    inspection.copy_warning = ''
    if tenant_emails:
        inspection.copy_sent_at = timezone.now()
        inspection.save(update_fields=['copy_sent_at', 'copy_warning'])
        return ''
    inspection.save(update_fields=['copy_warning'])
    return (
        'The report was emailed to you. There is no tenant email on file, so download the PDF '
        'and give them a copy, then mark it as handed over.'
    )


def finish_inspection(inspection):
    if inspection.is_locked:
        return ['This report is already finished.'], ''
    blockers = finalize_blockers(inspection)
    if blockers:
        return blockers, ''
    inspection.finalized_at = timezone.now()
    inspection.save(update_fields=['finalized_at'])
    warning = email_inspection_copy(inspection)
    sync_reminders(inspection.tenancy)
    return [], warning
