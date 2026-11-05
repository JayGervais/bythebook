from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.views import HealthView, WaitlistView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', HealthView.as_view(), name='health'),
    path('api/waitlist/', WaitlistView.as_view(), name='waitlist'),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('properties.urls')),
    path('api/', include('tenancies.urls')),
    path('api/', include('inspections.urls')),
    path('api/', include('deposits.urls')),
    path('api/', include('records.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'By the Book'
admin.site.site_title = 'By the Book'
