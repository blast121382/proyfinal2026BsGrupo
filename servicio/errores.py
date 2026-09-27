"""Excepciones de dominio y errores estructurados del servicio."""

class ErrorCriptoAdvisor(Exception):
    """Clase base para errores de CriptoAdvisor."""
    pass

class ErrorConfiguracion(ErrorCriptoAdvisor):
    """Falta alguna variable de entorno o clave obligatoria."""
    pass

class ErrorEntrada(ErrorCriptoAdvisor):
    """Datos de entrada inválidos o faltantes."""
    pass

class ErrorUpstreamAPI(ErrorCriptoAdvisor):
    """Error al comunicarse con la API de CoinGecko o OpenAI."""
    pass
