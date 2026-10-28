import { QUOTA_RECOVERY_UNKNOWN, quotaRecoveryMessage } from './quotaRecovery.js';

const SAFE_MESSAGES = Object.freeze({
  NETWORK_ERROR: 'No hay conexión con el backend local. Revisa el estado del servicio e inténtalo de nuevo.',
  OPENCODE_UNAVAILABLE: 'No hay conexión con OpenCode Server. Revisa su estado e inténtalo de nuevo.',
  OPENCODE_AUTH_FAILED: 'La autenticación local del agente falló. Revisa la configuración del servicio.',
  OPENCODE_RATE_LIMITED: QUOTA_RECOVERY_UNKNOWN,
  OPENCODE_INCOMPATIBLE: 'La configuración o versión del agente no coincide con la esperada.',
  MODEL_UNAVAILABLE: 'El modelo no está disponible o no tiene costo cero verificable en OpenCode. Revisa OPENCODE_MODEL_ID o el modelo predeterminado.',
  PROMPT_INVALID: 'El prompt del agente no está disponible. Revisa la configuración local.',
  PROMPT_RESTART_REQUIRED: 'El prompt cambió. Reinicia el backend para continuar.',
  MCP_UNAVAILABLE: 'No fue posible consultar las fuentes autorizadas. Inténtalo de nuevo.',
  TURN_IN_PROGRESS: 'Esta conversación ya está procesando una solicitud. Espera o cancela ese turno.',
  TURN_CANCELLED: 'El turno se canceló. Puedes enviar otro mensaje.',
  TURN_INVALIDATED: 'La conversación cambió durante el turno. Inicia un nuevo envío.',
  TURN_TIMEOUT: 'El análisis tardó demasiado. Puedes volver a intentarlo.',
  AGENT_OUTPUT_INVALID: 'El agente no devolvió una respuesta válida. Puedes volver a intentarlo.',
  MESSAGE_EMPTY: 'Escribe un mensaje antes de enviarlo.',
  MESSAGE_TOO_LONG: 'El mensaje supera el límite de 4.000 caracteres.',
  INVALID_REQUEST: 'El mensaje no cumple el formato esperado.',
  REQUEST_ID_CONFLICT: 'El identificador de envío ya se usó con otro contenido. Vuelve a enviarlo.',
  CONVERSATION_NOT_FOUND: 'La conversación ya no está disponible. Inicia un chat nuevo.',
  CAPACITY_EXCEEDED: 'El servicio alcanzó su capacidad temporal. Inténtalo de nuevo en unos minutos.',
  INTERNAL_ERROR: 'No fue posible completar el análisis. Puedes volver a intentarlo.',
});

export function analystErrorMessage(error) {
  if (error?.name === 'AbortError') return 'La solicitud se canceló.';
  if (error?.code === 'OPENCODE_RATE_LIMITED') return quotaRecoveryMessage(error.retryAt);
  return SAFE_MESSAGES[error?.code] || 'No fue posible completar la solicitud. Revisa el estado e inténtalo de nuevo.';
}
