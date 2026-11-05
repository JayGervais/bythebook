from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from deposits.alberta_calendar import add_banking_days, add_years
from deposits.models import Deposit, Reminder
from inspections.models import Inspection


DAMAGE_BLOCK = (
    'Alberta does not let a landlord deduct for damage or cleaning from the security deposit '
    'unless both the move-in and move-out reports are finished, with the required statements '
    'and signatures, and a copy was given to the tenant. Unpaid rent can still be recorded.'
)


def _latest_finalized(tenancy, inspection_type):
    return (
        tenancy.inspections.filter(inspection_type=inspection_type, finalized_at__isnull=False)
        .order_by('-version')
        .first()
    )


def damage_deduction_allowed(tenancy) -> bool:
    move_in = _latest_finalized(tenancy, Inspection.Type.MOVE_IN)
    move_out = _latest_finalized(tenancy, Inspection.Type.MOVE_OUT)
    return bool(move_in and move_out and move_in.copy_sent_at and move_out.copy_sent_at)


def _statement_sent(tenancy) -> bool:
    try:
        return bool(tenancy.deposit.statement_sent_on)
    except Deposit.DoesNotExist:
        return False


def _desired(tenancy) -> list[dict]:
    rows = []
    start = tenancy.start_date
    rows.append({
        'kind': Reminder.Kind.NOTICE_OF_LANDLORD,
        'due_on': start + timedelta(days=7),
        'headline': 'Give written notice of who the landlord is',
        'detail': (
            'Do this within 7 days of move-in. Mark the date once you have handed it over. '
            'Confirm the current wording in the Residential Tenancies Act before you rely on it.'
        ),
        'done': bool(tenancy.notice_of_landlord_on),
    })
    rows.append({
        'kind': Reminder.Kind.LEASE_COPY,
        'due_on': start + timedelta(days=21),
        'headline': 'Give the tenant a copy of the lease',
        'detail': 'Do this within 21 days of signing. Mark the date once they have it.',
        'done': bool(tenancy.lease_copy_on),
    })
    move_in_done = tenancy.inspections.filter(
        inspection_type=Inspection.Type.MOVE_IN, finalized_at__isnull=False,
    ).exists()
    rows.append({
        'kind': Reminder.Kind.INSPECTION_MOVE_IN,
        'due_on': start + timedelta(days=7),
        'headline': 'Finish the move-in inspection',
        'detail': (
            'Complete it within one week before or after move-in. Without this report, '
            'and the move-out report later, you generally cannot deduct for damage.'
        ),
        'done': move_in_done,
    })
    if tenancy.end_date:
        move_out_done = tenancy.inspections.filter(
            inspection_type=Inspection.Type.MOVE_OUT, finalized_at__isnull=False,
        ).exists()
        rows.append({
            'kind': Reminder.Kind.INSPECTION_MOVE_OUT,
            'due_on': tenancy.end_date + timedelta(days=7),
            'headline': 'Finish the move-out inspection',
            'detail': 'Complete it within one week before or after the tenant gives up possession.',
            'done': move_out_done,
        })
        rows.append({
            'kind': Reminder.Kind.DEPOSIT_STATEMENT,
            'due_on': tenancy.end_date + timedelta(days=10),
            'headline': 'Send the deposit statement or return the deposit',
            'detail': (
                'Within 10 days of the tenant giving up possession, return the deposit with interest '
                'or give a statement of account that shows the deposit, interest, deductions, and the balance.'
            ),
            'done': _statement_sent(tenancy),
        })

    try:
        deposit = tenancy.deposit
    except Deposit.DoesNotExist:
        deposit = None
    if deposit is not None:
        rows.append({
            'kind': Reminder.Kind.TRUST_DEPOSIT,
            'due_on': add_banking_days(deposit.received_on, 2),
            'headline': 'Put the security deposit in a trust account',
            'detail': (
                'Deposit it within two banking days in an interest-bearing trust account at a bank, '
                'treasury branch, credit union, or trust company in Alberta. The account name should include “in trust”, '
                'and it should hold only security-deposit money.'
            ),
            'done': bool(deposit.trust_deposited_on),
        })
        paid_years = set(deposit.interest_entries.values_list('covers_year', flat=True))
        year_index = 1
        anniversary = add_years(deposit.received_on, year_index)
        today = timezone.localdate()
        while anniversary <= today + timedelta(days=45):
            rows.append({
                'kind': Reminder.Kind.INTEREST,
                'due_on': anniversary,
                'headline': f'Pay security-deposit interest for year {year_index}',
                'detail': (
                    'Interest is owed each tenancy year at the rate the province sets. '
                    'Use the Service Alberta calculator, then record what you paid. '
                    'You can instead agree in writing to pay it when the tenancy ends.'
                ),
                'done': year_index in paid_years,
            })
            year_index += 1
            anniversary = add_years(deposit.received_on, year_index)
            if year_index > 30:
                break
    return rows


def sync_reminders(tenancy):
    desired = _desired(tenancy)
    seen = set()
    now = timezone.now()
    for row in desired:
        key = (row['kind'], row['due_on'])
        seen.add(key)
        reminder, _created = Reminder.objects.get_or_create(
            tenancy=tenancy,
            kind=row['kind'],
            due_on=row['due_on'],
            defaults={'headline': row['headline'], 'detail': row['detail']},
        )
        reminder.headline = row['headline']
        reminder.detail = row['detail']
        if row['done'] and reminder.completed_at is None:
            reminder.completed_at = now
        if not row['done']:
            reminder.completed_at = None
        reminder.save()
    stale = Reminder.objects.filter(tenancy=tenancy, sent_at__isnull=True, completed_at__isnull=True)
    for reminder in stale:
        if (reminder.kind, reminder.due_on) not in seen:
            reminder.delete()


def deposit_balance(deposit) -> Decimal:
    interest = sum((entry.amount for entry in deposit.interest_entries.all()), Decimal('0'))
    deductions = sum((entry.amount for entry in deposit.deductions.all()), Decimal('0'))
    return deposit.amount + interest - deductions
