# Workflows de n8n para CapsuleCorp

Este directorio contiene los workflows exportados de n8n en formato JSON para la integracion con Ultravox AI.

---

## Como Importar un Workflow

1. En n8n, click en **Add workflow** (boton `+`)
2. Click en los **3 puntos** (menu arriba derecha) -> **Import from file**
3. Seleccionar el archivo JSON de este directorio
4. Click en **Save**
5. **Activar** el workflow (toggle arriba derecha)

## Como Exportar un Workflow

1. En n8n, abrir el workflow
2. Click en los 3 puntos (menu) -> **Download**
3. Guardar el archivo JSON en este directorio
4. Nombrar con formato: `XX-nombre-descriptivo.json`

---

## Workflows Disponibles

### 01-ultravox-webhook-handler.json

**Proposito**: Receptor principal de webhooks de Ultravox AI. Este es el workflow mas importante.

**Webhook URL**: `http://localhost:5678/webhook/ultravox-webhook` (local) o `https://n8n.tudominio.com/webhook/ultravox-webhook` (produccion)

**Estructura**:
```
[Webhook Ultravox] -> [Switch por Evento]
                           |
            +--------------+---------------+---------------+
            |              |               |               |
            v              v               v               v
      call.started    call.ended    call.joined     call.billed
                           |
                           v
                  [Fue Transferida?]
                       |      |
                       v      v
                     SI      NO
                (alerta)  (resumen)
```

**Eventos que maneja**:
| Evento | Descripcion | Nodo de salida |
|--------|-------------|----------------|
| `call.started` | Llamada iniciada | Call Started |
| `call.ended` | Llamada finalizada | Call Ended -> verifica si fue transferida |
| `call.joined` | Cliente se conecto | Call Joined |
| `call.billed` | Informacion de facturacion | Call Billed |

**Datos extraidos en `call.ended`**:
- `call_id` - ID de la llamada en Ultravox
- `from_number` - Telefono del cliente
- `duration_seconds` - Duracion en segundos (calculado desde duration_ms o timestamps)
- `disconnection_reason` - Razon de fin (user_hangup, call_transfer, etc.)
- `sentiment` - Sentimiento detectado (positive, neutral, negative)
- `call_summary` - Resumen generado por IA
- `was_transferred` - Boolean indicando si fue transferida a humano

**Nodos TODO** (para conectar cuando configures integraciones):
- `TODO: Alerta Transferencia` - Conectar Email/Slack/Teams
- `TODO: Resumen Normal` - Conectar WhatsApp/Email

---

## Testing

### Test con curl (local)

```bash
# Test evento call.ended (el mas comun)
curl -X POST http://localhost:5678/webhook/ultravox-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "call.ended",
    "call": {
      "call_id": "test_call_123",
      "from_number": "+34612345678",
      "to_number": "+34911234567",
      "direction": "inbound",
      "start_timestamp": 1705156800000,
      "end_timestamp": 1705156860000,
      "duration_ms": 60000,
      "disconnection_reason": "user_hangup",
      "call_analysis": {
        "sentiment": "positive",
        "call_successful": true,
        "call_summary": "Cliente consulto sobre servicios. Conversacion positiva.",
        "custom_variables": {
          "consent_given": true
        }
      }
    }
  }'

# Test evento call_transfer (para probar alerta de transferencia)
curl -X POST http://localhost:5678/webhook/ultravox-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "call.ended",
    "call": {
      "call_id": "test_transfer_456",
      "from_number": "+34612345678",
      "to_number": "+34911234567",
      "direction": "inbound",
      "start_timestamp": 1705156800000,
      "end_timestamp": 1705156830000,
      "duration_ms": 30000,
      "disconnection_reason": "call_transfer",
      "call_analysis": {
        "sentiment": "neutral",
        "call_summary": "Cliente solicito hablar con un humano."
      }
    }
  }'
```

### Verificar ejecucion

1. En n8n, ir a **Executions** (menu lateral)
2. Ver que aparece la ejecucion del test
3. Click en la ejecucion para ver el flujo y datos de cada nodo

---

## Datos de Referencia de Ultravox

### Estructura del webhook `call.ended`

```json
{
  "event": "call.ended",
  "call": {
    "call_id": "call_abc123",
    "agent_id": "agent_xyz",
    "from_number": "+34612345678",
    "to_number": "+34911234567",
    "direction": "inbound",
    "start_timestamp": 1705156800000,
    "end_timestamp": 1705156860000,
    "duration_ms": 60000,
    "disconnection_reason": "user_hangup",
    "medium": "twilio",
    "model": "fixie-ai/ultravox",
    "voice": "terrence",
    "language": "es-ES",
    "transcript": "Texto completo de la conversacion...",
    "transcript_object": [...],
    "recording_url": "https://storage.ultravox.ai/...",
    "call_analysis": {
      "sentiment": "positive",
      "call_successful": true,
      "call_summary": "Resumen generado por IA...",
      "custom_variables": {
        "consent_given": true,
        "appointment_date": "2026-02-01T10:00:00"
      }
    }
  }
}
```

### Valores de `disconnection_reason`

| Valor | Significado | `was_transferred` |
|-------|-------------|-------------------|
| `user_hangup` | Cliente colgo | false |
| `agent_hangup` | Agente finalizo | false |
| `call_transfer` | Transferida a humano | **true** |
| `voicemail_reached` | Buzon de voz | false |
| `inactivity` | Sin actividad | false |
| `max_duration_reached` | Limite de tiempo | false |
| `timeout` | Timeout | false |
| `client_disconnected` | Cliente desconectado | false |
| `error` | Error tecnico | false |

### Expresiones n8n utiles

```javascript
// Acceso a datos basicos
{{ $json.event }}                           // "call.ended"
{{ $json.call.call_id }}                    // ID de llamada
{{ $json.call.from_number }}                // Telefono cliente

// Datos de analisis (con fallback)
{{ $json.call.call_analysis?.sentiment || 'neutral' }}
{{ $json.call.call_analysis?.call_summary || 'Sin resumen' }}

// Variables custom del agente Ultravox
{{ $json.call.call_analysis?.custom_variables?.appointment_date }}
{{ $json.call.call_analysis?.custom_variables?.consent_given }}

// Calculo de duracion (preferir duration_ms si esta disponible)
{{ $json.call.duration_ms ? Math.round($json.call.duration_ms / 1000) : Math.round(($json.call.end_timestamp - $json.call.start_timestamp) / 1000) }}

// Verificar si fue transferida
{{ $json.call.disconnection_reason === 'call_transfer' }}

// Datos especificos de Ultravox
{{ $json.call.medium }}                     // "twilio", "telnyx", "plivo", "webRtc"
{{ $json.call.model }}                      // Modelo de IA usado
{{ $json.call.voice }}                      // Voz del agente
{{ $json.call.language }}                   // Idioma (es-ES)
```

---

## Notas Importantes

- Los workflows **NO incluyen credenciales** (se configuran en n8n -> Credentials)
- Despues de importar, **activar** el workflow para que el webhook funcione
- Los IDs de nodos pueden cambiar al importar (no afecta funcionalidad)
- El webhook URL cambia segun el entorno:
  - Local: `http://localhost:5678/webhook/...`
  - Produccion: `https://n8n.tudominio.com/webhook/...`
