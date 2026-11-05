from decimal import Decimal

from rest_framework import serializers

from deposits.models import Deposit, DepositDeduction, DepositInterest, Reminder
from deposits.services import damage_deduction_allowed, deposit_balance, sync_reminders
from inspections.models import Inspection
from inspections.services import ensure_opening_inspections
from properties.models import Unit
from records.serializers import MaintenanceRequestSerializer, MessageSerializer, NoticeSerializer, RentPaymentSerializer
from tenancies.models import Tenancy, Tenant


class TenantSerializer(serializers.ModelSerializer):
    invite_active = serializers.SerializerMethodField()
    has_account = serializers.SerializerMethodField()
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Tenant
        fields = ('id', 'name', 'email', 'phone', 'invite_expires_at', 'invite_active', 'has_account')
        read_only_fields = ('id', 'invite_expires_at', 'invite_active', 'has_account')

    def get_invite_active(self, obj):
        from django.utils import timezone
        return bool(obj.invite_expires_at and obj.invite_expires_at >= timezone.now())

    def get_has_account(self, obj):
        return obj.account_id is not None


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ('id', 'kind', 'due_on', 'headline', 'detail', 'sent_at', 'completed_at')


class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositInterest
        fields = ('id', 'covers_year', 'amount', 'paid_on', 'note')
        read_only_fields = ('id',)


class DeductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositDeduction
        fields = ('id', 'kind', 'amount', 'reason', 'inspection_item', 'created_at')
        read_only_fields = ('id', 'created_at')


class DepositSerializer(serializers.ModelSerializer):
    interest_entries = InterestSerializer(many=True, read_only=True)
    deductions = DeductionSerializer(many=True, read_only=True)
    balance = serializers.SerializerMethodField()
    damage_allowed = serializers.SerializerMethodField()

    class Meta:
        model = Deposit
        fields = (
            'id', 'amount', 'received_on', 'trust_deposited_on', 'statement_sent_on',
            'interest_entries', 'deductions', 'balance', 'damage_allowed',
        )
        read_only_fields = ('id',)

    def get_balance(self, obj):
        return str(deposit_balance(obj))

    def get_damage_allowed(self, obj):
        return damage_deduction_allowed(obj.tenancy)

    def validate_amount(self, value):
        tenancy = self.context['tenancy']
        if value > tenancy.rent_amount:
            raise serializers.ValidationError('A security deposit cannot be more than one month of rent.')
        if value < 0:
            raise serializers.ValidationError('The deposit cannot be negative.')
        return value


class InspectionSummarySerializer(serializers.ModelSerializer):
    is_locked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inspection
        fields = (
            'id', 'inspection_type', 'version', 'conducted_on', 'finalized_at',
            'is_locked', 'copy_sent_at', 'presence',
        )


class TenancySerializer(serializers.ModelSerializer):
    unit_id = serializers.UUIDField(write_only=True, required=False)
    tenants = TenantSerializer(many=True)
    deposit_amount = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True, write_only=True)
    deposit_received_on = serializers.DateField(required=False, allow_null=True, write_only=True)
    deposit = DepositSerializer(read_only=True, allow_null=True)
    inspections = InspectionSummarySerializer(many=True, read_only=True)
    reminders = ReminderSerializer(many=True, read_only=True)
    payments = RentPaymentSerializer(many=True, read_only=True)
    notices = NoticeSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    maintenance_requests = MaintenanceRequestSerializer(many=True, read_only=True)
    address = serializers.SerializerMethodField()
    unit_label = serializers.CharField(source='unit.label', read_only=True)

    class Meta:
        model = Tenancy
        fields = (
            'id', 'unit_id', 'unit', 'unit_label', 'address', 'start_date', 'end_date',
            'rent_amount', 'rent_due_day', 'period', 'status', 'notice_of_landlord_on', 'lease_copy_on',
            'tenants', 'deposit', 'deposit_amount', 'deposit_received_on',
            'inspections', 'reminders', 'payments', 'notices', 'messages', 'maintenance_requests',
            'created_at',
        )
        read_only_fields = ('id', 'unit', 'status', 'created_at')

    def get_address(self, obj):
        prop = obj.unit.property
        return f'{prop.street_address}, {prop.city}'

    def validate_rent_due_day(self, value):
        if value < 1 or value > 28:
            raise serializers.ValidationError('Use a day from 1 to 28 so February still works.')
        return value

    def validate(self, attrs):
        start = attrs.get('start_date') or getattr(self.instance, 'start_date', None)
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'Move-out cannot be before move-in.'})
        period = attrs.get('period') or getattr(self.instance, 'period', Tenancy.Period.MONTHLY)
        if period == Tenancy.Period.FIXED and not end:
            raise serializers.ValidationError({'end_date': 'A fixed term needs the date it ends.'})
        rent = attrs.get('rent_amount', getattr(self.instance, 'rent_amount', None))
        amount = attrs.get('deposit_amount', None)
        if amount is not None and rent is not None and amount > rent:
            raise serializers.ValidationError({
                'deposit_amount': 'A security deposit cannot be more than one month of rent.',
            })
        if amount is not None and amount > 0 and not (attrs.get('deposit_received_on') or self._existing_received()):
            raise serializers.ValidationError({
                'deposit_received_on': 'Add the date you received the deposit.',
            })
        request = self.context['request']
        if 'unit_id' in attrs:
            unit = Unit.objects.filter(id=attrs['unit_id'], property__landlord=request.user).first()
            if unit is None:
                raise serializers.ValidationError({'unit_id': 'Choose one of your units.'})
            attrs['unit'] = unit
        elif self.instance is None:
            raise serializers.ValidationError({'unit_id': 'Choose a unit.'})
        return attrs

    def _existing_received(self):
        if self.instance is None:
            return None
        try:
            return self.instance.deposit.received_on
        except Deposit.DoesNotExist:
            return None

    def create(self, validated_data):
        tenants = validated_data.pop('tenants', [])
        amount = validated_data.pop('deposit_amount', None)
        received = validated_data.pop('deposit_received_on', None)
        validated_data.pop('unit_id', None)
        unit = validated_data.pop('unit')
        if not tenants:
            raise serializers.ValidationError({'tenants': 'Add at least one person.'})
        tenancy = Tenancy.objects.create(unit=unit, **validated_data)
        for row in tenants:
            Tenant.objects.create(tenancy=tenancy, **self._tenant_fields(row))
        if amount:
            Deposit.objects.create(tenancy=tenancy, amount=amount, received_on=received)
        ensure_opening_inspections(tenancy)
        sync_reminders(tenancy)
        return tenancy

    def update(self, instance, validated_data):
        raw_tenants = self.initial_data.get('tenants') if 'tenants' in self.initial_data else None
        amount = validated_data.pop('deposit_amount', None)
        received = validated_data.pop('deposit_received_on', None)
        validated_data.pop('tenants', None)
        validated_data.pop('unit_id', None)
        validated_data.pop('unit', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if raw_tenants is not None:
            self._sync_tenants(instance, raw_tenants)
        try:
            existing = instance.deposit
        except Deposit.DoesNotExist:
            existing = None
        if existing is not None and existing.amount > instance.rent_amount and not amount:
            raise serializers.ValidationError({
                'rent_amount': 'Rent cannot drop below the security deposit already recorded.',
            })
        if amount:
            received_on = received or self._existing_received()
            try:
                deposit = instance.deposit
            except Deposit.DoesNotExist:
                deposit = None
            if deposit is None:
                Deposit.objects.create(tenancy=instance, amount=amount, received_on=received_on)
            else:
                deposit.amount = amount
                if received:
                    deposit.received_on = received
                if deposit.amount > instance.rent_amount:
                    raise serializers.ValidationError({
                        'deposit_amount': 'A security deposit cannot be more than one month of rent.',
                    })
                deposit.save()
        ensure_opening_inspections(instance)
        sync_reminders(instance)
        return instance

    def _tenant_fields(self, row):
        return {
            'name': row['name'].strip(),
            'email': (row.get('email') or '').strip().lower(),
            'phone': (row.get('phone') or '').strip(),
        }

    def _sync_tenants(self, tenancy, rows):
        if not rows:
            raise serializers.ValidationError({'tenants': 'Keep at least one person on the tenancy.'})
        seen = []
        for row in rows:
            fields = self._tenant_fields(row)
            tenant_id = row.get('id')
            if tenant_id:
                tenant = tenancy.tenants.filter(pk=tenant_id).first()
                if tenant is None:
                    continue
                for key, value in fields.items():
                    setattr(tenant, key, value)
                tenant.save()
                seen.append(tenant.id)
            else:
                created = Tenant.objects.create(tenancy=tenancy, **fields)
                seen.append(created.id)
        tenancy.tenants.exclude(pk__in=seen).delete()


class TenancyExportSerializer(TenancySerializer):
    """Same record the landlord can download, including signature audit fields."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        from inspections.serializers import InspectionSerializer
        data['inspections_full'] = InspectionSerializer(
            instance.inspections.prefetch_related('items__photos', 'signatures'),
            many=True,
        ).data
        return data
