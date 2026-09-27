"""Pruebas deterministas sobre los contratos Pydantic y reglas de riesgo."""

import pytest
from pydantic import ValidationError

from servicio.contratos import (
    EvaluacionRiesgoGeneral,
    MetricaActivo,
    NivelRiesgoActivo,
    PerfilRiesgo,
    SolicitudAnalisis,
)
from servicio.reglas import calcular_nivel_riesgo_individual, evaluar_canasta_para_perfil


def test_solicitud_valida():
    solicitud = SolicitudAnalisis(
        activos=["BITCOIN", "  ethereum  "],
        moneda_base="usd",
        perfil_riesgo=PerfilRiesgo.MODERADO,
    )
    assert solicitud.activos == ["bitcoin", "ethereum"]
    assert solicitud.moneda_base == "usd"
    assert solicitud.horizonte_dias == 30


def test_solicitud_rechaza_lista_vacia():
    with pytest.raises(ValidationError):
        SolicitudAnalisis(
            activos=[],
            perfil_riesgo=PerfilRiesgo.CONSERVADOR,
        )


def test_solicitud_rechaza_moneda_invalida():
    with pytest.raises(ValidationError):
        SolicitudAnalisis(
            activos=["bitcoin"],
            moneda_base="libras",
            perfil_riesgo=PerfilRiesgo.AGRESIVO,
        )


def test_reglas_nivel_riesgo_individual():
    assert calcular_nivel_riesgo_individual(1.2) == NivelRiesgoActivo.BAJO
    assert calcular_nivel_riesgo_individual(-3.5) == NivelRiesgoActivo.MEDIO
    assert calcular_nivel_riesgo_individual(7.8) == NivelRiesgoActivo.ALTO
    assert calcular_nivel_riesgo_individual(-15.0) == NivelRiesgoActivo.MUY_ALTO


def test_reglas_perfil_conservador_con_activo_alto():
    metricas = [
        MetricaActivo(
            activo="bitcoin",
            precio=60000.0,
            cambio_24h_pct=-0.5,
            volumen_24h=1000000.0,
            nivel_riesgo_activo=NivelRiesgoActivo.BAJO,
        ),
        MetricaActivo(
            activo="solana",
            precio=140.0,
            cambio_24h_pct=8.5,
            volumen_24h=500000.0,
            nivel_riesgo_activo=NivelRiesgoActivo.ALTO,
        ),
    ]
    riesgo = evaluar_canasta_para_perfil(metricas, PerfilRiesgo.CONSERVADOR)
    assert riesgo == EvaluacionRiesgoGeneral.DESFAVORABLE_PARA_PERFIL
