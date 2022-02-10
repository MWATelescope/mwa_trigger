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
    path('triggerevent_details/<int:tid>/', views.TriggerEvent_details),
    path('voevent_log/', views.VOEventList.as_view()),
    path('comet_log/', views.CometLogList.as_view()),
    path('project_settings/', views.ProjectSettingsList.as_view()),
    path('project_decision_details/<int:id>/', views.ProjectDecision_details),
    path('project_decision_result/<int:id>/<int:decision>/', views.ProjectDecision_result),
    path('project_decision_log/', views.ProjectDecisionList.as_view()),
    path('voevent_view/<int:id>/', views.voevent_view),
    path('voevent_create/', views.voevent_create),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)