"""Cliente HTTP asíncrono para consultar datos reales de CoinGecko API."""

import os
import httpx
from .errores import ErrorUpstreamAPI

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


async def consultar_cotizaciones_reales(
    activos: list[str],
    moneda_base: str = "usd",
) -> dict:
    """Consulta precios, volumen 24h y variación 24h directamente a CoinGecko.

    Devuelve un diccionario estructurado indexado por ID de activo.
    Lanza ErrorUpstreamAPI en caso de fallo o activo no encontrado.
    """
    if not activos:
        return {}

    ids_param = ",".join(activos)
    url = f"{COINGECKO_BASE_URL}/simple/price"
    params = {
        "ids": ids_param,
        "vs_currencies": moneda_base.lower(),
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "CriptoAdvisor/1.0 (Estrategias-Integracion-LLM)",
    }

    # Si se configuró clave opcional de CoinGecko (Demo key)
    api_key = os.getenv("COINGECKO_API_KEY")
    if api_key:
        headers["x-cg-demo-api-key"] = api_key

    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            respuesta = await client.get(url, params=params, headers=headers)
            
            if respuesta.status_code == 429:
                raise ErrorUpstreamAPI(
                    "Límite de cuota excedido en CoinGecko (429 Too Many Requests). Intenta en 1 minuto."
                )
            if respuesta.status_code != 200:
                raise ErrorUpstreamAPI(
                    f"CoinGecko respondió con error HTTP {respuesta.status_code}."
                )

            datos = respuesta.json()
            if not isinstance(datos, dict):
                raise ErrorUpstreamAPI("Respuesta inesperada de CoinGecko (no es un objeto JSON).")

            # Verificar si ninguno de los activos solicitados fue devuelto
            encontrados = [a for a in activos if a in datos]
            if not encontrados:
                raise ErrorUpstreamAPI(
                    f"Ninguno de los activos solicitados ({activos}) fue encontrado en CoinGecko."
                )

            return datos

    except httpx.RequestError as exc:
        raise ErrorUpstreamAPI(f"Falla de conexión al consultar CoinGecko: {str(exc)}") from exc
