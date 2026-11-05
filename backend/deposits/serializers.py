from django.conf import settings
from rest_framework import serializers

from deposits.models import DepositDeduction, DepositInterest
from deposits.services import DAMAGE_BLOCK, damage_deduction_allowed


class InterestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositInterest
        fields = ('covers_year', 'amount', 'paid_on', 'note')

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Interest cannot be negative.')
        return value

    def validate_covers_year(self, value):
        if value < 1 or value > 40:
            raise serializers.ValidationError('Use the tenancy year, starting at 1.')
        return value


class DeductionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositDeduction
        fields = ('kind', 'amount', 'reason', 'inspection_item')

    def validate(self, attrs):
        if attrs['amount'] <= 0:
            raise serializers.ValidationError({'amount': 'Enter an amount greater than zero.'})
        if not attrs['reason'].strip():
            raise serializers.ValidationError({'reason': 'Say what this deduction is for.'})
        tenancy = self.context['tenancy']
        if attrs['kind'] == DepositDeduction.Kind.DAMAGE and not damage_deduction_allowed(tenancy):
            raise serializers.ValidationError({'kind': DAMAGE_BLOCK})
        item = attrs.get('inspection_item')
        if item is not None and item.inspection.tenancy_id != tenancy.id:
            raise serializers.ValidationError({'inspection_item': 'That checklist row is from a different tenancy.'})
        return attrs


class DepositUpdateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    received_on = serializers.DateField(required=False)
    trust_deposited_on = serializers.DateField(required=False, allow_null=True)
    statement_sent_on = serializers.DateField(required=False, allow_null=True)

    def validate_amount(self, value):
        tenancy = self.context['tenancy']
        if value > tenancy.rent_amount:
            raise serializers.ValidationError('A security deposit cannot be more than one month of rent.')
        if value < 0:
            raise serializers.ValidationError('The deposit cannot be negative.')
        return value

    def update_deposit(self, deposit):
        for field, value in self.validated_data.items():
            setattr(deposit, field, value)
        deposit.save()
        return deposit


def calculator_url():
    return settings.DEPOSIT_INTEREST_CALCULATOR_URL
