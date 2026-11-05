from django.contrib import admin

from inspections.models import Inspection, InspectionItem, Photo, Signature


class ItemInline(admin.TabularInline):
    model = InspectionItem
    extra = 0


class SignatureInline(admin.TabularInline):
    model = Signature
    extra = 0


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ('tenancy', 'inspection_type', 'version', 'conducted_on', 'finalized_at')
    list_filter = ('inspection_type',)
    inlines = [ItemInline, SignatureInline]


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('item', 'caption', 'taken_at')
