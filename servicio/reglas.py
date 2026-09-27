"""Reglas de negocio deterministas para evaluar volatilidad y riesgo."""

from .contratos import (
    EvaluacionRiesgoGeneral,
    MetricaActivo,
    NivelRiesgoActivo,
    PerfilRiesgo,
    SolicitudAnalisis,
)
from .errores import ErrorEntrada


def calcular_nivel_riesgo_individual(cambio_24h_pct: float) -> NivelRiesgoActivo:
    """Calcula el riesgo individual según la oscilación en 24 horas."""
    variacion_abs = abs(cambio_24h_pct)
    if variacion_abs < 2.0:
        return NivelRiesgoActivo.BAJO
    elif variacion_abs < 5.0:
        return NivelRiesgoActivo.MEDIO
    elif variacion_abs < 10.0:
        return NivelRiesgoActivo.ALTO
    else:
        return NivelRiesgoActivo.MUY_ALTO


def procesar_metricas(
    solicitud: SolicitudAnalisis,
    datos_coingecko: dict,
) -> tuple[list[MetricaActivo], EvaluacionRiesgoGeneral]:
    """Transforma los datos crudos de CoinGecko en métricas tipadas y calcula el semáforo."""
    moneda = solicitud.moneda_base.lower()
    metricas: list[MetricaActivo] = []

    for activo in solicitud.activos:
        if activo not in datos_coingecko:
            continue
        info = datos_coingecko[activo]
        precio = float(info.get(moneda, 0.0))
        volumen = float(info.get(f"{moneda}_24h_vol", 0.0))
        cambio_24h = float(info.get(f"{moneda}_24h_change", 0.0))

        nivel_activo = calcular_nivel_riesgo_individual(cambio_24h)

        metricas.append(
            MetricaActivo(
                activo=activo,
                precio=round(precio, 4),
                cambio_24h_pct=round(cambio_24h, 2),
                volumen_24h=round(volumen, 2),
                nivel_riesgo_activo=nivel_activo,
            )
        )

    if not metricas:
        raise ErrorEntrada(
            f"No se pudieron extraer métricas válidas para los activos {solicitud.activos}."
        )

    # Evaluación determinista del perfil vs la canasta de activos
    riesgo_general = evaluar_canasta_para_perfil(metricas, solicitud.perfil_riesgo)
    return metricas, riesgo_general


def evaluar_canasta_para_perfil(
    metricas: list[MetricaActivo],
    perfil: PerfilRiesgo,
) -> EvaluacionRiesgoGeneral:
    """Reglas fijas para determinar si la canasta es favorable, adecuada o desfavorable."""
    tiene_muy_alto = any(m.nivel_riesgo_activo == NivelRiesgoActivo.MUY_ALTO for m in metricas)
    tiene_alto = any(m.nivel_riesgo_activo == NivelRiesgoActivo.ALTO for m in metricas)
    todos_bajos = all(m.nivel_riesgo_activo == NivelRiesgoActivo.BAJO for m in metricas)

    if perfil == PerfilRiesgo.CONSERVADOR:
        if tiene_muy_alto or tiene_alto:
            return EvaluacionRiesgoGeneral.DESFAVORABLE_PARA_PERFIL
        if todos_bajos:
            return EvaluacionRiesgoGeneral.FAVORABLE
        return EvaluacionRiesgoGeneral.ADECUADO_CON_PRECAUCION

    elif perfil == PerfilRiesgo.MODERADO:
        if tiene_muy_alto:
            return EvaluacionRiesgoGeneral.DESFAVORABLE_PARA_PERFIL
        if tiene_alto:
            return EvaluacionRiesgoGeneral.ADECUADO_CON_PRECAUCION
        return EvaluacionRiesgoGeneral.FAVORABLE

    else:  # PerfilRiesgo.AGRESIVO
        if tiene_muy_alto:
            return EvaluacionRiesgoGeneral.ADECUADO_CON_PRECAUCION
        return EvaluacionRiesgoGeneral.FAVORABLE
