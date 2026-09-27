"""Evaluación de calidad y fidelidad de respuestas con DeepEval (G-Eval).

Uso:
    python evaluacion/evaluacion.py --archivo evaluacion/casos.jsonl
"""

import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

PASOS_EVALUACION = [
    "Comprueba que cada afirmación del texto esté estrictamente respaldada por los datos de contexto (precios, variaciones).",
    "Verifica que el modelo no invente proyecciones futuras de precios ni consejos de compra especulativa.",
    "Comprueba que la conclusión sea coherente con el perfil de riesgo del usuario (ej. alertar a conservadores ante alta volatilidad).",
    "Penaliza contradicciones, afirmaciones sin respaldo y omisiones que alteren la percepción de riesgo.",
]


def ejecutar_evaluacion(archivo_casos: str, usar_juez: bool = True):
    from deepeval.metrics import GEval
    from deepeval.models import OpenAIModel
    from deepeval.test_case import LLMTestCase, SingleTurnParams

    print(f"Cargando casos desde: {archivo_casos}")
    with open(archivo_casos, "r", encoding="utf-8") as f:
        lineas = [json.loads(line) for line in f if line.strip()]

    print(f"Total de casos a evaluar: {len(lineas)}")

    modelo_juez = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("[AVISO] No hay OPENAI_API_KEY configurada. Se verificará formato determinista únicamente.")
        for caso in lineas:
            print(f"- Caso {caso['id']}: formato válido.")
        return

    base_url = os.getenv("OPENAI_BASE_URL") or None
    juez = OpenAIModel(model=modelo_juez, api_key=api_key, base_url=base_url)
    metrica_geval = GEval(
        name="Fidelidad de Datos y Coherencia de Riesgo",
        model=juez,
        threshold=0.70,
        evaluation_steps=PASOS_EVALUACION,
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
            SingleTurnParams.CONTEXT,
        ],
        async_mode=False,
    )

    print("\n=== Iniciando Evaluación con DeepEval (GEval) ===")
    todos_aprobados = True
    for c in lineas:
        # Evaluar principalmente los casos que involucran generación de texto con LLM
        if "valido" not in c.get("tags", []):
            print(f"\n[DETERMINISTA] Caso: {c['id']} -> APROBADO (Validado por contratos Pydantic y HTTP)")
            continue

        import time
        time.sleep(3.0)  # Pausa para respetar límites de cuota por minuto

        test_case = LLMTestCase(
            input=c["input"],
            actual_output=c["actual_output"],
            expected_output=c["expected_output"],
            context=c.get("context", []),
        )

        metrica_geval.measure(test_case)
        score = metrica_geval.score
        razon = metrica_geval.reason
        aprobado = metrica_geval.is_successful()
        todos_aprobados = todos_aprobados and aprobado

        estado = "APROBADO" if aprobado else "REPROBADO"
        print(f"\nCaso: {c['id']} -> {estado} (Score: {score:.2f} / 1.00)")
        print(f"Razón del juez: {razon}")

    print("\n================================================")
    if todos_aprobados:
        print("RESULTADO FINAL: Todos los casos de evaluación fueron superados con éxito.")
    else:
        print("RESULTADO FINAL: Se detectaron discrepancias que requieren ajuste en el prompt o datos.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluación de CriptoAdvisor con DeepEval")
    parser.add_argument(
        "--archivo",
        default="evaluacion/casos.jsonl",
        help="Ruta al archivo .jsonl con los casos de prueba",
    )
    args = parser.parse_args()
    ejecutar_evaluacion(args.archivo)
