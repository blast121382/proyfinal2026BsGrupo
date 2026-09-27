"""Script de medición de latencias para el Hito de la Sesión 3.

Ejecuta 3 peticiones consecutivas a la misma solicitud para medir tiempos y estabilidad.
Uso:
    python medir.py --url http://127.0.0.1:8000/analizar --clave clave-secreta-demo-123
"""

import argparse
import json
import time
import httpx


def medir(url: str, clave: str, veces: int = 3):
    payload = {
        "activos": ["bitcoin", "ethereum"],
        "moneda_base": "usd",
        "perfil_riesgo": "moderado",
        "horizonte_dias": 30,
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": clave,
    }

    print(f"=== Iniciando {veces} mediciones sobre {url} ===")
    print(f"Payload: {json.dumps(payload)}\n")

    resultados = []
    with httpx.Client(timeout=60.0) as client:
        for i in range(1, veces + 1):
            t0 = time.perf_counter()
            try:
                resp = client.post(url, json=payload, headers=headers)
                latencia = time.perf_counter() - t0
                status = resp.status_code
                exito = "200 OK" if status == 200 else f"Error {status}"
            except Exception as exc:
                latencia = time.perf_counter() - t0
                exito = f"Fallo de red: {type(exc).__name__}"

            resultados.append((i, round(latencia, 2), exito))
            print(f"Corrida {i}: {latencia:.2f} s -> {exito}")
            time.sleep(1.0)  # Pausa breve entre corridas

    print("\n--- Tabla para copiar en docs/PROYECTO.md ---")
    print("| Ejecución | Tiempo total | Resultado o error |")
    print("|---|---|---|")
    for r in resultados:
        print(f"| {r[0]} | {r[1]} s | {r[2]} |")
    print("---------------------------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Medidor de tiempos de CriptoAdvisor")
    parser.add_argument("--url", default="http://127.0.0.1:8000/analizar", help="URL del endpoint a medir")
    parser.add_argument("--clave", default="clave-secreta-demo-123", help="Valor de X-API-Key")
    parser.add_argument("--veces", type=int, default=3, help="Número de ejecuciones")
    args = parser.parse_args()

    medir(args.url, args.clave, args.veces)
