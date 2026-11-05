import uuid

from django.db import models
from django.utils import timezone

from properties.models import Unit


class Tenancy(models.Model):
    class Status(models.TextChoices):
        UPCOMING = 'upcoming', 'Upcoming'
        ACTIVE = 'active', 'Active'
        ENDED = 'ended', 'Ended'

    class Period(models.TextChoices):
        WEEKLY = 'weekly', 'Week to week'
        MONTHLY = 'monthly', 'Month to month'
        YEARLY = 'yearly', 'Year to year'
        FIXED = 'fixed', 'Fixed term'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(Unit, related_name='tenancies', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    rent_amount = models.DecimalField(max_digits=8, decimal_places=2)
    rent_due_day = models.PositiveSmallIntegerField(default=1)
    period = models.CharField(max_length=16, choices=Period.choices, default=Period.MONTHLY)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPCOMING)
    notice_of_landlord_on = models.DateField(null=True, blank=True)
    lease_copy_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name_plural = 'tenancies'

    def refresh_status(self):
        today = timezone.localdate()
        if self.end_date and self.end_date < today:
            self.status = self.Status.ENDED
        elif self.start_date > today:
            self.status = self.Status.UPCOMING
        else:
            self.status = self.Status.ACTIVE

    def save(self, *args, **kwargs):
        self.refresh_status()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.unit} from {self.start_date}'


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenancy = models.ForeignKey(Tenancy, related_name='tenants', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    invite_token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    invite_expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
