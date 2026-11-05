import uuid

from django.db import models

from tenancies.models import Tenancy


class Deposit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenancy = models.OneToOneField(Tenancy, related_name='deposit', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    received_on = models.DateField()
    trust_deposited_on = models.DateField(null=True, blank=True)
    statement_sent_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'${self.amount} for {self.tenancy}'


class DepositInterest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deposit = models.ForeignKey(Deposit, related_name='interest_entries', on_delete=models.CASCADE)
    covers_year = models.PositiveSmallIntegerField(help_text='The tenancy year this payment covers, counting from the deposit date.')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    paid_on = models.DateField()
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['covers_year']
        unique_together = [('deposit', 'covers_year')]


class DepositDeduction(models.Model):
    class Kind(models.TextChoices):
        DAMAGE = 'damage', 'Damage or cleaning'
        RENT = 'rent', 'Unpaid rent'
        OTHER = 'other', 'Other agreed amount'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deposit = models.ForeignKey(Deposit, related_name='deductions', on_delete=models.CASCADE)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    reason = models.TextField()
    inspection_item = models.ForeignKey(
        'inspections.InspectionItem',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deductions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class Reminder(models.Model):
    class Kind(models.TextChoices):
        TRUST_DEPOSIT = 'trust_deposit', 'Trust account'
        INSPECTION_MOVE_IN = 'inspection_move_in', 'Move-in inspection'
        INSPECTION_MOVE_OUT = 'inspection_move_out', 'Move-out inspection'
        INTEREST = 'deposit_interest', 'Deposit interest'
        NOTICE_OF_LANDLORD = 'notice_of_landlord', 'Notice of landlord'
        LEASE_COPY = 'lease_copy', 'Copy of the lease'
        DEPOSIT_STATEMENT = 'deposit_statement', 'Deposit statement'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenancy = models.ForeignKey(Tenancy, related_name='reminders', on_delete=models.CASCADE)
    kind = models.CharField(max_length=40, choices=Kind.choices)
    due_on = models.DateField()
    headline = models.CharField(max_length=200)
    detail = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['due_on', 'kind']
        unique_together = [('tenancy', 'kind', 'due_on')]

    def __str__(self):
        return self.headline
