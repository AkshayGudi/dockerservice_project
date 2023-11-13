from django.urls import path
from . import views
from rest_framework.authtoken import views as auth_view

urlpatterns = [
    path('build-push', views.build_and_push_docker ,name="build-push-endpoint"),
    path('build-push-status', views.get_build_push_status ,name="build-push-status-endpoint"),
    path('retry-build', views.retry_build, name="retry-build-endpoint")
    ]