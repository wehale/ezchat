"""AI integration for kirbus — /ai <prompt> command."""
from kirbus.ai.provider import ask, AIConfigError

__all__ = ["ask", "AIConfigError"]
