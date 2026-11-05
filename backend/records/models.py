import uuid

from django.db import models
from django.utils import timezone

from properties.models import Unit
from tenancies.models import Tenancy


class RentPayment(models.Model):
    class Method(models.TextChoices):
        ETRANSFER = 'etransfer', 'e-Transfer'
        CASH = 'cash', 'Cash'
        CHEQUE = 'cheque', 'Cheque'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenancy = models.ForeignKey(Tenancy, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    paid_on = models.DateField()
    method = models.CharField(max_length=16, choices=Method.choices, default=Method.ETRANSFER)
    receipt_number = models.CharField(max_length=16)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_on', '-created_at']
        unique_together = [('tenancy', 'receipt_number')]

    def __str__(self):
        return f'Receipt {self.receipt_number}'


class Notice(models.Model):
    class Kind(models.TextChoices):
        TERMINATE = 'terminate_periodic', 'End a periodic tenancy'
        BREACH = 'substantial_breach', 'Substantial breach'
        DAMAGE = 'damage_or_assault', 'Damage or assault'
        RENT = 'rent_increase', 'Rent increase'
        ENTRY = 'entry', 'Notice of entry'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenancy = models.ForeignKey(Tenancy, related_name='notices', on_delete=models.CASCADE)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    served_on = models.DateField()
    served_time = models.TimeField(null=True, blank=True)
    effective_on = models.DateField()
    effective_time = models.TimeField(null=True, blank=True)
    service_method = models.CharField(max_length=32)
    reason_code = models.CharField(max_length=32, blank=True)
    reason = models.TextField(blank=True)
    new_rent = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-served_on', '-created_at']

    def __str__(self):
        return f'{self.kind} served {self.served_on}'


class TenancyMessage(models.Model):
    class Role(models.TextChoices):
        LANDLORD = 'landlord', 'Landlord'
        TENANT = 'tenant', 'Tenant'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenancy = models.ForeignKey(Tenancy, related_name='messages', on_delete=models.CASCADE)
    author_role = models.CharField(max_length=16, choices=Role.choices)
    author_name = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class MaintenanceRequest(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In progress'
        RESOLVED = 'resolved', 'Resolved'

    class Requester(models.TextChoices):
        LANDLORD = 'landlord', 'Landlord'
        TENANT = 'tenant', 'Tenant'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(Unit, related_name='maintenance_requests', on_delete=models.CASCADE)
    tenancy = models.ForeignKey(Tenancy, null=True, blank=True, related_name='maintenance_requests', on_delete=models.SET_NULL)
    description = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    requested_by = models.CharField(max_length=16, choices=Requester.choices)
    requester_name = models.CharField(max_length=200, blank=True)
    resolved_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class MaintenancePhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(MaintenanceRequest, related_name='photos', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='maintenance/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    taken_at = models.DateTimeField(default=timezone.now)


class MaintenanceTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(Unit, related_name='tasks', on_delete=models.CASCADE)
    kind = models.CharField(max_length=32)
    label = models.CharField(max_length=80)
    interval_days = models.PositiveIntegerField()
    last_done_on = models.DateField(null=True, blank=True)
    next_due_on = models.DateField()
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['next_due_on', 'label']
        unique_together = [('unit', 'kind')]
