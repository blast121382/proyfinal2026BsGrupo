"""Módulo del Agente LLM (OpenAI gpt-4o-mini) para síntesis y fundamentación de riesgo."""

import json
import os
from .configuracion import observacion, trace_id, trazas_activas
from .contratos import (
    EvaluacionRiesgoGeneral,
    MetricaActivo,
    RespuestaAnalisis,
    SolicitudAnalisis,
)
from .errores import ErrorConfiguracion, ErrorUpstreamAPI

SISTEMA = """Eres un analista financiero cuantitativo especializado en criptoactivos y gestión de riesgos. Responde en español.
Tu tarea es explicar de manera ejecutiva y profesional si la canasta de criptoactivos evaluada es adecuada para el perfil de riesgo del usuario.
Reglas estrictas de fundamentación:
1. Limítate estrictamente a las métricas del JSON de contexto (precios, variaciones 24h, volúmenes y la calificación de riesgo determinista).
2. Prohibido inventar datos, proyecciones de precios o especular sobre el futuro.
3. Prohibido dar consejos de compra o venta directa ("compre ahora", "venda"). Enfócate en el nivel de riesgo y la volatilidad actual.
4. Explica el significado del semáforo de riesgo determinista para el perfil indicado.
5. Lenguaje claro, formal y conciso. Máximo 150 palabras."""


def obtener_cliente_llm():
    """Inicializa el cliente de OpenAI asíncrono, integrando Langfuse si está activo."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL") or None

    if not api_key and not base_url:
        raise ErrorConfiguracion("Falta configurar OPENAI_API_KEY en el archivo .env.")

    if not api_key:
        api_key = "ollama"

    if trazas_activas():
        from langfuse.openai import AsyncOpenAI
    else:
        from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=1)


async def generar_analisis(
    solicitud: SolicitudAnalisis,
    metricas: list[MetricaActivo],
    riesgo_general: EvaluacionRiesgoGeneral,
) -> RespuestaAnalisis:
    """Genera la respuesta completa invocando al LLM con las métricas como contexto estricto."""
    with observacion("Analizar riesgo de cartera", solicitud.model_dump(mode="json")) as span:
        modelo = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        cliente = obtener_cliente_llm()

        contexto = {
            "perfil_riesgo": solicitud.perfil_riesgo.value,
            "horizonte_dias": solicitud.horizonte_dias,
            "moneda_base": solicitud.moneda_base,
            "evaluacion_riesgo_general": riesgo_general.value,
            "activos": [m.model_dump(mode="json") for m in metricas],
        }

        mensajes = [
            {"role": "system", "content": SISTEMA},
            {
                "role": "user",
                "content": f"Analiza esta cartera con los siguientes datos reales calculados:\n{json.dumps(contexto, ensure_ascii=False, indent=2)}",
            },
        ]

        try:
            async with cliente:
                respuesta = await cliente.chat.completions.create(
                    model=modelo,
                    messages=mensajes,
                    temperature=0.0,
                    max_completion_tokens=300,
                )

            if not respuesta.choices:
                raise ErrorUpstreamAPI("El modelo LLM no devolvió una respuesta válida.")

            texto = respuesta.choices[0].message.content or ""
            if not texto:
                raise ErrorUpstreamAPI("El modelo LLM devolvió una respuesta vacía.")

            resultado = RespuestaAnalisis(
                moneda_base=solicitud.moneda_base,
                perfil_riesgo=solicitud.perfil_riesgo,
                metricas=metricas,
                evaluacion_riesgo_general=riesgo_general,
                analisis_llm=texto.strip(),
                trace_id=trace_id(),
            )

            if span and hasattr(span, "update"):
                span.update(output=resultado.model_dump(mode="json"))

            return resultado

        except Exception as exc:
            if isinstance(exc, (ErrorConfiguracion, ErrorUpstreamAPI)):
                raise
            raise ErrorUpstreamAPI(f"Fallo en la llamada al modelo LLM: {str(exc)}") from exc


async def generar_analisis_stream(
    solicitud: SolicitudAnalisis,
    metricas: list[MetricaActivo],
    riesgo_general: EvaluacionRiesgoGeneral,
):
    """Genera la respuesta vía SSE (Server-Sent Events) transmitiendo fragmentos en tiempo real."""
    with observacion("Analizar riesgo (Streaming)", solicitud.model_dump(mode="json")) as span:
        modelo = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        cliente = obtener_cliente_llm()

        # Emitir primer evento con datos cuantitativos antes del texto del LLM
        yield {
            "evento": "datos",
            "metricas": [m.model_dump(mode="json") for m in metricas],
            "evaluacion_riesgo_general": riesgo_general.value,
        }

        contexto = {
            "perfil_riesgo": solicitud.perfil_riesgo.value,
            "horizonte_dias": solicitud.horizonte_dias,
            "moneda_base": solicitud.moneda_base,
            "evaluacion_riesgo_general": riesgo_general.value,
            "activos": [m.model_dump(mode="json") for m in metricas],
        }

        mensajes = [
            {"role": "system", "content": SISTEMA},
            {
                "role": "user",
                "content": f"Analiza esta cartera con los siguientes datos reales calculados:\n{json.dumps(contexto, ensure_ascii=False, indent=2)}",
            },
        ]

        texto_acumulado = ""
        async with cliente:
            stream = await cliente.chat.completions.create(
                model=modelo,
                messages=mensajes,
                temperature=0.0,
                max_completion_tokens=300,
                stream=True,
            )
            async with stream:
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        parte = chunk.choices[0].delta.content
                        texto_acumulado += parte
                        yield {"evento": "texto", "texto": parte}

        final = RespuestaAnalisis(
            moneda_base=solicitud.moneda_base,
            perfil_riesgo=solicitud.perfil_riesgo,
            metricas=metricas,
            evaluacion_riesgo_general=riesgo_general,
            analisis_llm=texto_acumulado.strip(),
            trace_id=trace_id(),
        )

        if span and hasattr(span, "update"):
            span.update(output=final.model_dump(mode="json"))

        yield {"evento": "fin", "respuesta": final.model_dump(mode="json")}
