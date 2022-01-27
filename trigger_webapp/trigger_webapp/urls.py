"""trigger_webapp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from trigger_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', views.home_page),
    path('user_alert_status/', views.user_alert_status),
    path('user_alert_delete/<int:id>/', views.user_alert_delete),
    path('user_alert_create/', views.user_alert_create),
    path('trigger_log/', views.TriggerEventList.as_view()),
    path('voevent_log/', views.VOEventList.as_view()),
    path('comet_log/', views.CometLogList.as_view()),
    #path('<str:filepath>/', views.download_file),
    path('voevent_view/<int:id>/', views.voevent_view),
    path('voevent_create/', views.voevent_create),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)