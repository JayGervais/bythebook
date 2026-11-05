from rest_framework import serializers

from inspections.models import Inspection, InspectionItem, Photo, Signature
from inspections.services import drop_stale_signatures, finalize_blockers, statement_bundle


class PhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Photo
        fields = ('id', 'url', 'caption', 'taken_at')

    def get_url(self, obj):
        return obj.image.url if obj.image else ''


class ItemSerializer(serializers.ModelSerializer):
    photos = PhotoSerializer(many=True, read_only=True)

    class Meta:
        model = InspectionItem
        fields = (
            'id', 'room', 'item', 'condition', 'notes', 'sort_order',
            'prior_condition', 'prior_notes', 'photos',
        )


class SignatureSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Signature
        fields = ('id', 'role', 'name', 'url', 'signed_at', 'ip_address', 'user_agent')

    def get_url(self, obj):
        return obj.image.url if obj.image else ''


class PublicSignatureSerializer(SignatureSerializer):
    class Meta(SignatureSerializer.Meta):
        fields = ('id', 'role', 'name', 'url', 'signed_at')


class InspectionSerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True, read_only=True)
    signatures = SignatureSerializer(many=True, read_only=True)
    statements = serializers.SerializerMethodField()
    blockers = serializers.SerializerMethodField()
    is_locked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inspection
        fields = (
            'id', 'tenancy', 'inspection_type', 'version', 'supersedes',
            'scheduled_on', 'conducted_on', 'presence', 'landlord_name',
            'tenant_signer_name', 'disagreement_reasons', 'occupied_agreement_note',
            'offered_times', 'general_notes', 'finalized_at', 'copy_sent_at',
            'copy_warning', 'is_locked', 'items', 'signatures', 'statements', 'blockers',
        )
        read_only_fields = (
            'id', 'tenancy', 'inspection_type', 'version', 'supersedes',
            'finalized_at', 'copy_sent_at', 'copy_warning', 'is_locked',
        )

    def get_statements(self, obj):
        return statement_bundle(obj)

    def get_blockers(self, obj):
        if obj.is_locked:
            return []
        return finalize_blockers(obj)

    def validate_offered_times(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Offered times need to be a list.')
        cleaned = []
        for entry in value:
            if not isinstance(entry, dict):
                raise serializers.ValidationError('Each offered time needs a date and a time.')
            cleaned.append({
                'date': str(entry.get('date', '')).strip(),
                'time': str(entry.get('time', '')).strip(),
            })
        return cleaned

    def update(self, instance, validated_data):
        if instance.is_locked:
            raise serializers.ValidationError('This report is finished. Start a revision to change it.')
        items = self.initial_data.get('items')
        presence_before = instance.presence
        inspection = super().update(instance, validated_data)
        if inspection.presence != presence_before:
            drop_stale_signatures(inspection)
        if items is not None:
            self._apply_items(inspection, items)
        return inspection

    def _apply_items(self, inspection, items):
        if not isinstance(items, list):
            raise serializers.ValidationError({'items': 'Send a list of checklist rows.'})
        by_id = {str(item.id): item for item in inspection.items.all()}
        for row in items:
            if not isinstance(row, dict) or 'id' not in row:
                continue
            item = by_id.get(str(row['id']))
            if item is None:
                continue
            if 'condition' in row:
                condition = row['condition'] or ''
                allowed = {choice for choice, _label in InspectionItem.Condition.choices} | {''}
                if condition not in allowed:
                    raise serializers.ValidationError({'items': f'Unknown condition “{condition}”.'})
                item.condition = condition
            if 'notes' in row:
                item.notes = str(row['notes'] or '')
            item.save()


class PublicInspectionSerializer(InspectionSerializer):
    signatures = PublicSignatureSerializer(many=True, read_only=True)

    class Meta(InspectionSerializer.Meta):
        fields = tuple(
            field for field in InspectionSerializer.Meta.fields
            if field not in ('copy_warning',)
        )
