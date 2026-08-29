from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('properties.urls')),
    path('accounts/', include('users.urls')),
    path('matching/', include('matching.urls')),
    path('visits/', include('visits.urls')),
    path('leasing/', include('leasing.urls')),
    path('dashboard/', include('dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
