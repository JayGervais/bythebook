from django.contrib import admin

from records.models import MaintenanceRequest, MaintenanceTask, Notice, RentPayment, TenancyMessage

admin.site.register(RentPayment)
admin.site.register(Notice)
admin.site.register(TenancyMessage)
admin.site.register(MaintenanceRequest)
admin.site.register(MaintenanceTask)
