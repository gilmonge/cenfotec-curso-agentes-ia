"""Errores Pinecone públicos y sanitizados."""


class PineconeKnowledgeError(RuntimeError):
    code = "PINECONE_ERROR"
    message = "No fue posible completar la operación de conocimiento."

    def __init__(self) -> None:
        super().__init__(self.message)


class PineconeConfigurationError(PineconeKnowledgeError):
    code = "PINECONE_CONFIGURATION_INVALID"
    message = "La configuración Pinecone no es válida."


class PineconeCredentialsMissingError(PineconeKnowledgeError):
    code = "PINECONE_CREDENTIALS_MISSING"
    message = "Pinecone no está configurado en el entorno del backend."


class PineconeIndexNotFoundError(PineconeKnowledgeError):
    code = "PINECONE_INDEX_NOT_FOUND"
    message = "El índice Pinecone configurado no existe."


class PineconeIndexIncompatibleError(PineconeKnowledgeError):
    code = "PINECONE_INDEX_INCOMPATIBLE"
    message = "El índice Pinecone existente no coincide con el contrato requerido."


class PineconeAuthenticationError(PineconeKnowledgeError):
    code = "PINECONE_AUTHENTICATION_FAILED"
    message = "Pinecone rechazó la autenticación del backend."


class PineconeTimeoutError(PineconeKnowledgeError):
    code = "PINECONE_TIMEOUT"
    message = "La operación Pinecone agotó el tiempo de espera."


class PineconeRateLimitError(PineconeKnowledgeError):
    code = "PINECONE_RATE_LIMITED"
    message = "Pinecone limitó temporalmente las solicitudes del backend."


class PineconeServiceError(PineconeKnowledgeError):
    code = "PINECONE_SERVICE_UNAVAILABLE"
    message = "El servicio Pinecone no está disponible."
