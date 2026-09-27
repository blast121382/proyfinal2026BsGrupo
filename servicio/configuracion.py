"""Configuración del entorno y cliente de observabilidad con Langfuse."""

import os
from contextlib import nullcontext
from pathlib import Path
from dotenv import load_dotenv
from .errores import ErrorConfiguracion

# Cargar variables desde .env en la raíz del proyecto
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def trazas_activas() -> bool:
    """Comprueba si Langfuse está configurado y habilitado."""
    activado = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"
    tiene_claves = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
    return activado and tiene_claves


def observacion(nombre: str, entrada=None):
    """Envoltorio de contexto para registrar un span/observación en Langfuse."""
    if not trazas_activas():
        return nullcontext()
    try:
        from langfuse import get_client
        return get_client().start_as_current_observation(name=nombre, input=entrada)
    except Exception:
        return nullcontext()


def trace_id() -> str | None:
    """Devuelve el ID de la traza activa en Langfuse si está disponible."""
    if not trazas_activas():
        return None
    try:
        from langfuse import get_client
        return get_client().get_current_trace_id()
    except Exception:
        return None
