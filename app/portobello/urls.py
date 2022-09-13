from django.contrib import admin
from django.urls import include, path
from portobello import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include('bot.urls')),
    path('admin/', admin.site.urls),
]

if bool(settings.DEBUG):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
