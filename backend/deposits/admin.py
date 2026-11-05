from django.contrib import admin

from deposits.models import Deposit, DepositDeduction, DepositInterest, Reminder


class InterestInline(admin.TabularInline):
    model = DepositInterest
    extra = 0


class DeductionInline(admin.TabularInline):
    model = DepositDeduction
    extra = 0


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('tenancy', 'amount', 'received_on', 'trust_deposited_on')
    inlines = [InterestInline, DeductionInline]


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('headline', 'tenancy', 'due_on', 'sent_at', 'completed_at')
    list_filter = ('kind',)
