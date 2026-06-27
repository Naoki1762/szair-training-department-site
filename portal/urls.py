from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("api/qa/ask", views.ask_question, name="ask_question"),
    path("api/students", views.students, name="students"),
    path("api/auth/dingtalk/start", views.dingtalk_start, name="dingtalk_start"),
    path("api/auth/dingtalk/callback", views.dingtalk_callback, name="dingtalk_callback"),
]
