from django.contrib import admin

from tenancies.models import Tenancy, Tenant


class TenantInline(admin.TabularInline):
    model = Tenant
    extra = 0
    exclude = ('invite_token_hash',)


@admin.register(Tenancy)
class TenancyAdmin(admin.ModelAdmin):
    list_display = ('unit', 'start_date', 'end_date', 'rent_amount', 'status')
    list_filter = ('status',)
    inlines = [TenantInline]
