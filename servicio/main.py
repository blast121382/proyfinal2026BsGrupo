"""FastAPI: Definición de endpoints, seguridad y ciclo de vida de CriptoAdvisor."""

import json
import os
import secrets
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader

from . import agente, cliente_api, reglas
from .configuracion import trazas_activas
from .contratos import RespuestaAnalisis, SolicitudAnalisis
from .errores import (
    ErrorConfiguracion,
    ErrorCriptoAdvisor,
    ErrorEntrada,
    ErrorUpstreamAPI,
)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Manejo del ciclo de vida del servidor: inicialización y vaciado de Langfuse."""
    yield
    if trazas_activas():
        try:
            from langfuse import get_client
            get_client().flush()
        except Exception:
            pass


app = FastAPI(
    title="CriptoAdvisor API · Estrategias de Integración",
    description="Servicio backend que integra CoinGecko API y OpenAI (gpt-4o-mini) para análisis de riesgo.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

cabecera_api_key = APIKeyHeader(name="X-API-Key", auto_error=False)


def verificar_acceso(clave: str | None = Security(cabecera_api_key)):
    """Valida la cabecera de autenticación X-API-Key de forma segura."""
    esperada = os.getenv("CLAVE_SERVICIO", "")
    if not esperada:
        raise HTTPException(
            status_code=503,
            detail="Servicio no configurado: falta definir CLAVE_SERVICIO en las variables de entorno.",
        )
    if not clave or not secrets.compare_digest(clave.encode("utf-8"), esperada.encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail="No autorizado: Clave de acceso inválida o ausente en la cabecera X-API-Key.",
        )


def traducir_error_http(error: Exception) -> HTTPException:
    """Mapea excepciones internas a códigos HTTP estándar sin filtrar secretos ni trazas internas."""
    if isinstance(error, ErrorConfiguracion):
        return HTTPException(status_code=503, detail=str(error))
    if isinstance(error, ErrorEntrada):
        return HTTPException(status_code=422, detail=str(error))
    if isinstance(error, ErrorUpstreamAPI):
        return HTTPException(status_code=502, detail=str(error))
    return HTTPException(
        status_code=500,
        detail="Error interno del servidor. Por favor, intente más tarde.",
    )


@app.get("/salud", tags=["Monitoreo"])
def salud():
    """Comprobación de vida del servicio (Health Check)."""
    return {"estado": "ok", "servicio": "criptoadvisor", "version": "1.0.0"}


@app.post(
    "/cotizaciones",
    tags=["Consultas"],
    dependencies=[Depends(verificar_acceso)],
)
async def consultar_cotizaciones(solicitud: SolicitudAnalisis):
    """Consulta directa a CoinGecko y cálculo de métricas sin invocar al LLM (Hito Sesión 2)."""
    try:
        datos = await cliente_api.consultar_cotizaciones_reales(
            activos=solicitud.activos,
            moneda_base=solicitud.moneda_base,
        )
        metricas, riesgo_general = reglas.procesar_metricas(solicitud, datos)
        return {
            "moneda_base": solicitud.moneda_base,
            "perfil_riesgo": solicitud.perfil_riesgo,
            "metricas": [m.model_dump() for m in metricas],
            "evaluacion_riesgo_general": riesgo_general,
        }
    except ErrorCriptoAdvisor as exc:
        raise traducir_error_http(exc) from exc
    except Exception as exc:
        raise traducir_error_http(exc) from exc


@app.post(
    "/analizar",
    response_model=RespuestaAnalisis,
    tags=["Análisis de Inversión"],
    dependencies=[Depends(verificar_acceso)],
)
async def analizar_cartera(solicitud: SolicitudAnalisis):
    """Flujo completo: CoinGecko -> Reglas Deterministas -> OpenAI (gpt-4o-mini)."""
    try:
        # 1. Consulta a la API externa
        datos = await cliente_api.consultar_cotizaciones_reales(
            activos=solicitud.activos,
            moneda_base=solicitud.moneda_base,
        )
        # 2. Reglas deterministas
        metricas, riesgo_general = reglas.procesar_metricas(solicitud, datos)
        # 3. Síntesis y justificación con el LLM
        return await agente.generar_analisis(solicitud, metricas, riesgo_general)
    except ErrorCriptoAdvisor as exc:
        raise traducir_error_http(exc) from exc
    except Exception as exc:
        raise traducir_error_http(exc) from exc


@app.post(
    "/analizar/stream",
    tags=["Análisis de Inversión"],
    dependencies=[Depends(verificar_acceso)],
)
async def analizar_cartera_stream(solicitud: SolicitudAnalisis):
    """Transmisión Server-Sent Events (SSE) del análisis en tiempo real."""
    async def generador_eventos():
        try:
            datos = await cliente_api.consultar_cotizaciones_reales(
                activos=solicitud.activos,
                moneda_base=solicitud.moneda_base,
            )
            metricas, riesgo_general = reglas.procesar_metricas(solicitud, datos)
            async for evento in agente.generar_analisis_stream(solicitud, metricas, riesgo_general):
                yield "data: " + json.dumps(evento, ensure_ascii=False) + "\n\n"
        except ErrorCriptoAdvisor as exc:
            err = traducir_error_http(exc)
            yield "data: " + json.dumps({"evento": "error", "mensaje": err.detail}) + "\n\n"
        except Exception:
            yield "data: " + json.dumps({"evento": "error", "mensaje": "Fallo durante la transmisión."}) + "\n\n"

    return StreamingResponse(
        generador_eventos(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
