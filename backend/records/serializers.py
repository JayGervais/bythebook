from rest_framework import serializers

from records.models import MaintenancePhoto, MaintenanceRequest, MaintenanceTask, Notice, RentPayment, TenancyMessage
from records.notices import SERVICE_LABELS
from records.services import prepare_notice


class RentPaymentSerializer(serializers.ModelSerializer):
    method_label = serializers.CharField(source='get_method_display', read_only=True)

    class Meta:
        model = RentPayment
        fields = ('id', 'amount', 'paid_on', 'method', 'method_label', 'receipt_number', 'note', 'created_at')
        read_only_fields = ('id', 'receipt_number', 'created_at', 'method_label')


class NoticeSerializer(serializers.ModelSerializer):
    service_label = serializers.SerializerMethodField()

    class Meta:
        model = Notice
        fields = (
            'id', 'kind', 'served_on', 'served_time', 'effective_on', 'effective_time',
            'service_method', 'service_label', 'reason_code', 'reason', 'new_rent', 'body', 'created_at',
        )
        read_only_fields = ('id', 'body', 'created_at', 'service_label')

    def get_service_label(self, obj):
        return SERVICE_LABELS.get(obj.service_method, obj.service_method)

    def create(self, validated_data):
        tenancy = self.context['tenancy']
        fields, errors = prepare_notice(tenancy, validated_data)
        if errors:
            raise serializers.ValidationError(errors)
        return Notice.objects.create(tenancy=tenancy, **fields)


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenancyMessage
        fields = ('id', 'author_role', 'author_name', 'body', 'created_at')
        read_only_fields = ('id', 'author_role', 'author_name', 'created_at')

    def validate_body(self, value):
        text = value.strip()
        if not text:
            raise serializers.ValidationError('Write a message.')
        if len(text) > 2000:
            raise serializers.ValidationError('Keep the message under 2,000 characters.')
        return text


class MaintenancePhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MaintenancePhoto
        fields = ('id', 'url', 'caption', 'taken_at')

    def get_url(self, obj):
        return obj.image.url if obj.image else ''


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    photos = MaintenancePhotoSerializer(many=True, read_only=True)

    class Meta:
        model = MaintenanceRequest
        fields = (
            'id', 'unit', 'tenancy', 'description', 'status', 'requested_by',
            'requester_name', 'resolved_on', 'created_at', 'photos',
        )
        read_only_fields = ('id', 'unit', 'tenancy', 'requested_by', 'requester_name', 'created_at', 'photos')

    def validate_description(self, value):
        text = value.strip()
        if not text:
            raise serializers.ValidationError('Describe what needs attention.')
        return text


class MaintenanceTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceTask
        fields = ('id', 'unit', 'kind', 'label', 'interval_days', 'last_done_on', 'next_due_on', 'note')
        read_only_fields = fields
