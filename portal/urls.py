from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("api/auth/me", views.current_user, name="current_user"),
    path("api/auth/login", views.local_login, name="local_login"),
    path("api/auth/logout", views.local_logout, name="local_logout"),
    path("api/qa/ask", views.ask_question, name="ask_question"),
    path("api/students", views.students, name="students"),
    path("api/conduct/records", views.create_conduct_record, name="create_conduct_record"),
    path("api/resources", views.resources, name="resources"),
    path("api/resources/upload", views.upload_resource, name="upload_resource"),
    path("api/auth/dingtalk/start", views.dingtalk_start, name="dingtalk_start"),
    path("api/auth/dingtalk/callback", views.dingtalk_callback, name="dingtalk_callback"),
]
