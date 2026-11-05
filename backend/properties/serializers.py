from rest_framework import serializers

from properties.models import Property, Unit
from properties.rooms import DEFAULT_ROOMS


def _current_tenancy(unit):
    open_rows = [row for row in unit.tenancies.all() if row.status != 'ended']
    if not open_rows:
        return None
    return max(open_rows, key=lambda row: (row.start_date, row.created_at))


class UnitSerializer(serializers.ModelSerializer):
    tasks = serializers.SerializerMethodField()
    current_tenancy_id = serializers.SerializerMethodField()
    tenants = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = ('id', 'property', 'label', 'rooms_template', 'tasks', 'current_tenancy_id', 'tenants')
        read_only_fields = ('id', 'tasks', 'current_tenancy_id', 'tenants')

    def get_tasks(self, obj):
        from records.serializers import MaintenanceTaskSerializer
        return MaintenanceTaskSerializer(obj.tasks.all(), many=True).data

    def get_current_tenancy_id(self, obj):
        tenancy = _current_tenancy(obj)
        return str(tenancy.id) if tenancy else None

    def get_tenants(self, obj):
        tenancy = _current_tenancy(obj)
        if tenancy is None:
            return []
        from tenancies.serializers import TenantSerializer
        return TenantSerializer(tenancy.tenants.all(), many=True).data

    def validate_property(self, prop):
        request = self.context['request']
        if prop.landlord_id != request.user.id:
            raise serializers.ValidationError('Choose one of your properties.')
        return prop

    def validate_rooms_template(self, value):
        if value in (None, ''):
            return DEFAULT_ROOMS
        if not isinstance(value, list):
            raise serializers.ValidationError('Rooms need to be a list.')
        cleaned = []
        for room in value:
            if not isinstance(room, dict):
                raise serializers.ValidationError('Each room needs a name and a list of items.')
            name = str(room.get('room', '')).strip()
            items = room.get('items') or []
            if not name:
                raise serializers.ValidationError('Each room needs a name.')
            if not isinstance(items, list) or not items:
                raise serializers.ValidationError(f'{name} needs at least one item.')
            cleaned.append({'room': name, 'items': [str(item).strip() for item in items if str(item).strip()]})
        return cleaned

    def create(self, validated_data):
        from records.services import ensure_schedule
        unit = super().create(validated_data)
        ensure_schedule(unit)
        return unit


class PropertySerializer(serializers.ModelSerializer):
    units = UnitSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = (
            'id', 'street_address', 'city', 'province', 'postal_code',
            'property_type', 'units', 'created_at',
        )
        read_only_fields = ('id', 'created_at', 'units')

    def validate_province(self, value):
        province = (value or 'AB').strip().upper()
        if province != 'AB':
            raise serializers.ValidationError('This tool only covers Alberta.')
        return province

    def create(self, validated_data):
        validated_data['landlord'] = self.context['request'].user
        return super().create(validated_data)
