from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/',include('base.urls')),
    path('api/v1/community/',include('communities.urls')),
    path('api/v1/surveys/', include('surveys.urls')),
    path('api/v1/quiz/', include('quiz.urls'))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)