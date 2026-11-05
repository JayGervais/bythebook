from rest_framework import viewsets

from accounts.permissions import IsLandlord
from properties.models import Property, Unit
from properties.serializers import PropertySerializer, UnitSerializer
from records.services import ensure_schedule


class PropertyViewSet(viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = [IsLandlord]

    def get_queryset(self):
        units = Unit.objects.filter(property__landlord=self.request.user)
        for unit in units:
            ensure_schedule(unit)
        return Property.objects.filter(landlord=self.request.user).prefetch_related(
            'units__tasks', 'units__tenancies__tenants',
        )


class UnitViewSet(viewsets.ModelViewSet):
    serializer_class = UnitSerializer
    permission_classes = [IsLandlord]

    def get_queryset(self):
        return Unit.objects.filter(property__landlord=self.request.user).select_related('property')
