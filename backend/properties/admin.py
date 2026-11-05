from django.contrib import admin

from properties.models import Property, Unit


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('street_address', 'city', 'property_type', 'landlord')
    search_fields = ('street_address', 'city', 'landlord__email')
    inlines = [UnitInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('label', 'property')
    search_fields = ('label', 'property__street_address')
