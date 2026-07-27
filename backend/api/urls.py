"""Configuración de URLs para la API REST."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import DocumentViewSet, ChatView


router = DefaultRouter()
router.register(r"documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("", include(router.urls)),
    path("chat/", ChatView.as_view(), name="chat"),
]
