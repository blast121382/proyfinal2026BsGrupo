# CriptoAdvisor API · Asesor de Criptoactivos y Evaluación de Riesgo

Proyecto final para el curso **Estrategias de Integración con LLMs — BSG Institute**.

- **Estudiante:** Jorge
- **API Externa:** [CoinGecko API v3](https://docs.coingecko.com/reference/introduction) (endpoints `/simple/price` y `/coins/markets`)
- **Modelo LLM:** OpenAI `gpt-4o-mini`
- **Observabilidad:** Langfuse

---

## 1. Descripción del Problema y Caso de Uso

Evaluar una cartera de criptoactivos requiere analizar múltiples variables cuantitativas (precio, variación 24h, volatilidad y volumen de negociación). Los usuarios con distintos perfiles de tolerancia al riesgo (conservador, moderado, agresivo) suelen verse expuestos a análisis especulativos o subjetivos.

**CriptoAdvisor** resuelve esto mediante una arquitectura híbrida y defensiva:
1. **Consulta datos reales y frescos** directamente desde CoinGecko API.
2. **Aplica reglas deterministas con Pydantic** para clasificar el riesgo cuantitativo (semáforo de riesgo).
3. **Instruye a un LLM (`gpt-4o-mini`)** mediante un prompt con grounding estricto para sintetizar en español (máx. 150 palabras) las razones de la calificación, prohibiendo inventar datos o hacer recomendaciones especulativas.

---

## 2. Requisitos Previos

- Python 3.10 o superior (recomendado Python 3.12).
- Git.
- Clave de API de OpenAI (`OPENAI_API_KEY`).
- (Opcional) Cuenta gratuita en [Langfuse](https://cloud.langfuse.com) para observabilidad.

---

## 3. Instalación y Configuración

### Paso 1: Clonar o ingresar al proyecto
```powershell
cd c:\Users\Jorge\Documents\IA\"Estrategias de Integracion"\criptoadvisor
```

### Paso 2: Crear y activar entorno virtual
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Paso 3: Instalar dependencias
```powershell
pip install -r requirements.txt
pip install -r requirements-eval.txt  # Para pruebas y DeepEval
```

### Paso 4: Configurar variables de entorno
Copia la plantilla de configuración:
```powershell
Copy-Item .env.example .env
```
Edita `.env` y coloca tus claves reales:
```ini
CLAVE_SERVICIO=clave-secreta-demo-123
OPENAI_API_KEY=sk-proj-tu-clave-aqui
OPENAI_MODEL=gpt-4o-mini
COINGECKO_API_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 4. Arranque del Servicio

Inicia el servidor backend en modo desarrollo:
```powershell
python -m uvicorn servicio.main:app --reload --port 8000
```

El servicio estará disponible en:
- **API Base:** `http://127.0.0.1:8000`
- **Documentación Interactiva (Swagger UI):** `http://127.0.0.1:8000/docs`
- **Health Check:** `http://127.0.0.1:8000/salud`

Para detener el servidor, presiona `Ctrl + C` en la terminal.

---

## 5. Pruebas y Ejemplos de Uso

### Ejemplo 1: Consulta completa de análisis de riesgo (`POST /analizar`)
```powershell
curl -X POST "http://127.0.0.1:8000/analizar" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: clave-secreta-demo-123" `
  -d '{"activos": ["bitcoin", "ethereum"], "moneda_base": "usd", "perfil_riesgo": "moderado"}'
```

### Ejemplo 2: Consulta rápida de cotizaciones sin LLM (`POST /cotizaciones`)
```powershell
curl -X POST "http://127.0.0.1:8000/cotizaciones" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: clave-secreta-demo-123" `
  -d '{"activos": ["solana"], "moneda_base": "usd", "perfil_riesgo": "conservador"}'
```

### Ejemplo 3: Transmisión SSE en tiempo real (`POST /analizar/stream`)
```powershell
curl -N -X POST "http://127.0.0.1:8000/analizar/stream" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: clave-secreta-demo-123" `
  -d '{"activos": ["bitcoin"], "moneda_base": "usd", "perfil_riesgo": "agresivo"}'
```

---

## 6. Ejecución de Pruebas y Mediciones

### Pruebas Unitarias Deterministas (pytest)
Ejecuta la suite de pruebas sin consumir tokens ni llamadas externas:
```powershell
python -m pytest tests/ -v
```

### Medición de Latencia (Sesión 3)
Ejecuta 3 peticiones consecutivas y genera la tabla de tiempos:
```powershell
python medir.py --veces 3
```

### Evaluación con DeepEval (Sesión 5)
Evalúa los casos de prueba con la métrica G-Eval de fidelidad:
```powershell
python evaluacion/evaluacion.py --archivo evaluacion/casos.jsonl
```

---

## 7. Estructura del Repositorio

```text
criptoadvisor/
├── README.md                 # Guía del proyecto
├── .env.example              # Variables requeridas de ejemplo
├── .gitignore                # Reglas de exclusión de Git
├── requirements.txt          # Dependencias de producción
├── requirements-eval.txt     # Dependencias de pruebas y DeepEval
├── medir.py                  # Medición de latencia
├── servicio/                 # Código del servicio FastAPI
│   ├── main.py               # Endpoints y ciclo de vida
│   ├── contratos.py          # Esquemas Pydantic v2
│   ├── cliente_api.py        # Cliente HTTP CoinGecko
│   ├── reglas.py             # Semáforo determinista de riesgo
│   ├── agente.py             # Invocación de OpenAI gpt-4o-mini
│   ├── configuracion.py      # Entorno y Langfuse
│   └── errores.py            # Excepciones de dominio
├── tests/                    # Pruebas con pytest
├── evaluacion/               # Banco de 5 casos y script DeepEval
├── docs/                     # Ficha del proyecto (PROYECTO.md)
└── evidencias/               # Evidencias organizadas por sesión
```
