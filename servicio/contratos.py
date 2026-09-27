"""Contratos de datos con Pydantic v2 para la entrada y salida de la API."""

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class PerfilRiesgo(str, Enum):
    CONSERVADOR = "conservador"
    MODERADO = "moderado"
    AGRESIVO = "agresivo"


class NivelRiesgoActivo(str, Enum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
    MUY_ALTO = "muy_alto"


class EvaluacionRiesgoGeneral(str, Enum):
    FAVORABLE = "FAVORABLE"
    ADECUADO_CON_PRECAUCION = "ADECUADO_CON_PRECAUCION"
    DESFAVORABLE_PARA_PERFIL = "DESFAVORABLE_PARA_PERFIL"


class SolicitudAnalisis(BaseModel):
    activos: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Lista de 1 a 5 IDs de criptoactivos en CoinGecko (ej. ['bitcoin', 'ethereum'])",
    )
    moneda_base: str = Field(
        default="usd",
        pattern="^(usd|eur|pen)$",
        description="Moneda base de cotización: 'usd', 'eur' o 'pen'",
    )
    perfil_riesgo: PerfilRiesgo = Field(
        ...,
        description="Perfil de tolerancia al riesgo del inversor: conservador, moderado o agresivo",
    )
    horizonte_dias: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Horizonte temporal de inversión en días (1 a 365)",
    )

    @field_validator("activos")
    @classmethod
    def normalizar_activos(cls, valores: list[str]) -> list[str]:
        limpios = [v.strip().lower() for v in valores if v and v.strip()]
        if not limpios:
            raise ValueError("La lista de activos no puede estar vacía o contener solo espacios.")
        # Evitar duplicados conservando orden
        return list(dict.fromkeys(limpios))

    def datos_faltantes(self) -> list[str]:
        faltan = []
        if not self.activos:
            faltan.append("activos")
        if not self.perfil_riesgo:
            faltan.append("perfil_riesgo")
        return faltan


class MetricaActivo(BaseModel):
    activo: str = Field(description="ID del criptoactivo")
    precio: float = Field(description="Precio actual en la moneda base")
    cambio_24h_pct: float = Field(description="Variación porcentual en las últimas 24 horas")
    volumen_24h: float = Field(description="Volumen negociado en 24h en la moneda base")
    nivel_riesgo_activo: NivelRiesgoActivo = Field(description="Nivel de riesgo individual calculado")


class RespuestaAnalisis(BaseModel):
    fecha_consulta: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha y hora UTC de la consulta",
    )
    moneda_base: str = Field(description="Moneda en la que se expresan las cotizaciones")
    perfil_riesgo: PerfilRiesgo = Field(description="Perfil evaluado")
    metricas: list[MetricaActivo] = Field(
        default_factory=list,
        description="Métricas cuantitativas obtenidas de CoinGecko y calculadas por reglas",
    )
    evaluacion_riesgo_general: EvaluacionRiesgoGeneral = Field(
        description="Calificación determinista del riesgo de la canasta para el perfil"
    )
    analisis_llm: str = Field(
        description="Explicación ejecutiva generada por el LLM estrictamente fundamentada en las métricas"
    )
    aclaracion: bool = Field(
        default=False,
        description="Indica si se requiere aclaración de datos por parte del usuario",
    )
    trace_id: str | None = Field(
        default=None,
        description="Identificador único de trazabilidad en Langfuse",
    )
