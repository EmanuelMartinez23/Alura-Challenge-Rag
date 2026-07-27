"""
Configuración ASGI para el proyecto RAGMantenimientos.

Expone el callable ASGI como una variable a nivel de módulo llamada ``application``.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
