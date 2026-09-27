# Evidencia de Trazabilidad en Langfuse · Sesión 4

**Trace ID:** `lf-tr-btc-eth-20260927-01`  
**Servicio:** CriptoAdvisor API  
**Entorno:** Local / Desarrollo  
**Fecha de captura:** 2026-09-27T20:21:02Z  

---

## 1. Árbol de Spans y Generaciones en Langfuse

```mermaid
graph TD
    T["Trace: Analizar riesgo de cartera [lf-tr-btc-eth-20260927-01] (1.63s)"]
    T --> S1["Span: Validación de Contrato Pydantic (1.2ms)"]
    T --> S2["Span: HTTP GET CoinGecko /simple/price (520ms)"]
    T --> S3["Span: Reglas Deterministas de Riesgo (0.8ms)"]
    T --> G1["Generation: OpenAI gpt-4o-mini (1,080ms)"]

    style T fill:#2563eb,stroke:#1d4ed8,color:#fff
    style S1 fill:#10b981,stroke:#059669,color:#fff
    style S2 fill:#f59e0b,stroke:#d97706,color:#fff
    style S3 fill:#10b981,stroke:#059669,color:#fff
    style G1 fill:#8b5cf6,stroke:#7c3aed,color:#fff
```

---

## 2. Detalle de Observaciones

### Observación 1: Raíz (Trace)
- **Nombre:** `Analizar riesgo de cartera`
- **Input:**
  ```json
  {
    "activos": ["bitcoin", "ethereum"],
    "moneda_base": "usd",
    "perfil_riesgo": "moderado",
    "horizonte_dias": 30
  }
  ```
- **Latencia:** 1,630 ms
- **Estado:** SUCCESS (200 OK)

### Observación 2: Llamada Externa (CoinGecko)
- **Tipo:** SPAN
- **URL:** `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true`
- **Status:** 200 OK (520 ms)

### Observación 3: Generación del LLM (OpenAI)
- **Tipo:** GENERATION
- **Modelo:** `gpt-4o-mini`
- **Temperature:** 0.0
- **Tokens de entrada (Prompt tokens):** 348 tokens
- **Tokens de salida (Completion tokens):** 112 tokens
- **Tokens totales:** 460 tokens
- **Costo estimado:** $0.000119 USD
- **Output:**
  > "Para un perfil moderado, la canasta evaluada presenta un comportamiento favorable. Tanto Bitcoin (+0.87%) como Ethereum (+0.47%) exhiben variaciones intradiarias menores al 1% con volúmenes de negociación robustos. Ambos activos se clasifican en nivel de riesgo bajo según las reglas cuantitativas, haciendo que la exposición actual sea compatible con la tolerancia al riesgo declarada."

---

## 3. Conclusión de Trazabilidad

La traza permite auditar todo el ciclo de vida de la solicitud: demuestra fehacientemente que la respuesta final estuvo precedida por la obtención de cotizaciones frescas en CoinGecko y la aplicación de las reglas cuantitativas de riesgo antes de invocar a OpenAI.
