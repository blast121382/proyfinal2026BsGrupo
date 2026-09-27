"""Pruebas HTTP deterministas con FastAPI TestClient simulando autenticación y mocks."""

import os
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

# Establecer clave de prueba para el entorno de test
os.environ["CLAVE_SERVICIO"] = "clave-test-123"

from servicio.main import app
from servicio.errores import ErrorUpstreamAPI

cliente = TestClient(app)


def test_endpoint_salud():
    resp = cliente.get("/salud")
    assert resp.status_code == 200
    assert resp.json()["estado"] == "ok"


def test_rechazo_sin_autorizacion():
    # Petición sin cabecera X-API-Key
    resp = cliente.post("/analizar", json={"activos": ["bitcoin"], "perfil_riesgo": "moderado"})
    assert resp.status_code == 401
    assert "No autorizado" in resp.json()["detail"]


def test_rechazo_clave_invalida():
    headers = {"X-API-Key": "clave-falsa"}
    resp = cliente.post(
        "/analizar",
        json={"activos": ["bitcoin"], "perfil_riesgo": "moderado"},
        headers=headers,
    )
    assert resp.status_code == 401


def test_rechazo_datos_invalidos():
    headers = {"X-API-Key": "clave-test-123"}
    # activos vacío y moneda base no permitida
    resp = cliente.post(
        "/analizar",
        json={"activos": [], "moneda_base": "invalida", "perfil_riesgo": "moderado"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_flujo_cotizaciones_con_mock():
    mock_datos_coingecko = {
        "bitcoin": {"usd": 65000.0, "usd_24h_vol": 20000000.0, "usd_24h_change": 1.5},
        "ethereum": {"usd": 3200.0, "usd_24h_vol": 10000000.0, "usd_24h_change": -0.8},
    }

    with patch(
        "servicio.cliente_api.consultar_cotizaciones_reales",
        new=AsyncMock(return_value=mock_datos_coingecko),
    ):
        headers = {"X-API-Key": "clave-test-123"}
        resp = cliente.post(
            "/cotizaciones",
            json={"activos": ["bitcoin", "ethereum"], "moneda_base": "usd", "perfil_riesgo": "moderado"},
            headers=headers,
        )
        assert resp.status_code == 200
        cuerpo = resp.json()
        assert len(cuerpo["metricas"]) == 2
        assert cuerpo["metricas"][0]["activo"] == "bitcoin"
        assert cuerpo["evaluacion_riesgo_general"] == "FAVORABLE"


@pytest.mark.asyncio
async def test_manejo_error_upstream_502():
    with patch(
        "servicio.cliente_api.consultar_cotizaciones_reales",
        side_effect=ErrorUpstreamAPI("CoinGecko no responde"),
    ):
        headers = {"X-API-Key": "clave-test-123"}
        resp = cliente.post(
            "/cotizaciones",
            json={"activos": ["bitcoin"], "moneda_base": "usd", "perfil_riesgo": "conservador"},
            headers=headers,
        )
        assert resp.status_code == 502
        assert "CoinGecko no responde" in resp.json()["detail"]
