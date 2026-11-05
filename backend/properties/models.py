import uuid

from django.conf import settings
from django.db import models

from properties.rooms import DEFAULT_ROOMS


class Property(models.Model):
    class PropertyType(models.TextChoices):
        HOUSE_WITH_SUITE = 'house_with_suite', 'House with a suite'
        DUPLEX = 'duplex', 'Duplex'
        CONDO = 'condo', 'Condo'
        ROOM_IN_HOME = 'room_in_home', 'Room in the home'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='properties', on_delete=models.CASCADE)
    street_address = models.CharField(max_length=200)
    city = models.CharField(max_length=80)
    province = models.CharField(max_length=2, default='AB')
    postal_code = models.CharField(max_length=10, blank=True)
    property_type = models.CharField(max_length=32, choices=PropertyType.choices, default=PropertyType.HOUSE_WITH_SUITE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['street_address']
        verbose_name_plural = 'properties'

    def __str__(self):
        return f'{self.street_address}, {self.city}'


class Unit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, related_name='units', on_delete=models.CASCADE)
    label = models.CharField(max_length=80)
    rooms_template = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['label']

    def save(self, *args, **kwargs):
        if not self.rooms_template:
            self.rooms_template = DEFAULT_ROOMS
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.label} — {self.property}'
