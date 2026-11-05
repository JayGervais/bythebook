import uuid

from django.db import models
from django.utils import timezone

from tenancies.models import Tenancy


class Inspection(models.Model):
    class Type(models.TextChoices):
        MOVE_IN = 'move_in', 'Move-in'
        MOVE_OUT = 'move_out', 'Move-out'

    class Presence(models.TextChoices):
        TOGETHER = 'together', 'Landlord and tenant together'
        REFUSED = 'refused', 'Tenant was there and refused to sign'
        ABSENT = 'absent', 'Tenant was not there'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenancy = models.ForeignKey(Tenancy, related_name='inspections', on_delete=models.CASCADE)
    inspection_type = models.CharField(max_length=16, choices=Type.choices)
    version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        'self', null=True, blank=True, related_name='revisions', on_delete=models.SET_NULL,
    )
    scheduled_on = models.DateField(null=True, blank=True)
    conducted_on = models.DateField(null=True, blank=True)
    presence = models.CharField(max_length=16, choices=Presence.choices, default=Presence.TOGETHER)
    landlord_name = models.CharField(max_length=200, blank=True)
    tenant_signer_name = models.CharField(max_length=200, blank=True)
    disagreement_reasons = models.TextField(blank=True)
    occupied_agreement_note = models.TextField(blank=True)
    offered_times = models.JSONField(default=list, blank=True)
    general_notes = models.TextField(blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    copy_sent_at = models.DateTimeField(null=True, blank=True)
    copy_warning = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['inspection_type', '-version']
        unique_together = [('tenancy', 'inspection_type', 'version')]

    @property
    def is_locked(self):
        return self.finalized_at is not None

    def __str__(self):
        return f'{self.get_inspection_type_display()} v{self.version}'


class InspectionItem(models.Model):
    class Condition(models.TextChoices):
        GOOD = 'good', 'Good'
        FAIR = 'fair', 'Fair'
        POOR = 'poor', 'Poor'
        DAMAGED = 'damaged', 'Damaged'
        NOT_APPLICABLE = 'not_applicable', 'Not applicable'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inspection = models.ForeignKey(Inspection, related_name='items', on_delete=models.CASCADE)
    room = models.CharField(max_length=80)
    item = models.CharField(max_length=120)
    condition = models.CharField(max_length=20, choices=Condition.choices, blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    prior_condition = models.CharField(max_length=20, blank=True)
    prior_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['sort_order', 'room']


class Photo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InspectionItem, related_name='photos', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='inspections/photos/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    taken_at = models.DateTimeField(default=timezone.now)


class Signature(models.Model):
    class Role(models.TextChoices):
        LANDLORD_PRESENCE = 'landlord_presence', 'Landlord, who attended'
        TENANT_AGREE = 'tenant_agree', 'Tenant agrees'
        TENANT_DISAGREE = 'tenant_disagree', 'Tenant disagrees'
        LANDLORD_REFUSAL = 'landlord_refusal', 'Landlord, tenant refused to sign'
        LANDLORD_ABSENT = 'landlord_absent', 'Landlord, tenant absent'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inspection = models.ForeignKey(Inspection, related_name='signatures', on_delete=models.CASCADE)
    role = models.CharField(max_length=32, choices=Role.choices)
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='inspections/signatures/%Y/%m/')
    signed_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        unique_together = [('inspection', 'role')]
