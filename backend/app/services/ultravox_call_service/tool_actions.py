"""Tool call action processing helpers.

Extracted from webhook.py save_tool_call_actions to reduce file size.
Maps Ultravox tool calls to ai_decision_log entries.
"""

import json
import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Tool name to (decision_type, base_description) mapping.
# Tools not in this map are skipped (e.g. getCurrentTimeN8N).
TOOL_MAP: dict[str, tuple[str, str]] = {
    "identificar_cliente": ("other", "Identificación de cliente"),
    "consultar_servicios": ("other", "Consulta de catálogo de servicios"),
    "buscar_servicio": ("other", "Búsqueda de servicio"),
    "consultar_disponibilidad": ("other", "Consulta de disponibilidad"),
    "agendar_cita": ("other", "Reserva de cita"),
    "cancelar_cita": ("other", "Cancelación de cita"),
    "crear_recado": ("other", "Recado telefónico"),
}


def _parse_json_safe(text_val: str) -> dict:
    """Parse JSON safely, returning raw wrapper on failure."""
    if not text_val:
        return {}
    try:
        return json.loads(text_val)
    except (json.JSONDecodeError, ValueError):
        return {"raw": text_val}


def _build_description(
    tool_name: str, base_desc: str, params: dict, result: dict, success: bool | None
) -> str:
    """Build human-readable description for a tool call action."""
    if tool_name == "buscar_servicio":
        search_term = params.get("nombre_servicio", "")
        if result.get("mensaje"):
            return result["mensaje"]
        if search_term:
            return f"Búsqueda de servicio: {search_term}"

    elif tool_name == "agendar_cita":
        if success and result.get("mensaje"):
            return result["mensaje"]
        if success:
            svc = result.get("servicio_nombre", "")
            fecha = result.get("fecha", "")
            hora = result.get("hora", "")
            return f"Cita agendada: {svc} - {fecha} {hora}"
        if not success and result.get("mensaje"):
            return result["mensaje"]

    elif tool_name == "consultar_disponibilidad":
        fecha = params.get("fecha", "")
        if fecha:
            return f"Consulta de disponibilidad: {fecha}"

    elif tool_name == "consultar_servicios":
        total = result.get("total")
        if total:
            return f"Consulta de catálogo: {total} servicios"

    elif tool_name == "cancelar_cita":
        if success:
            cliente = result.get("cliente_nombre", "")
            parts = [
                p
                for p in [result.get("titulo", ""), result.get("fecha", ""), result.get("hora", "")]
                if p
            ]
            desc = f"Cita cancelada: {' - '.join(parts)}" if parts else "Cita cancelada"
            if cliente:
                desc += f" ({cliente})"
            return desc
        if result.get("error") == "multiples_citas":
            return result.get("mensaje", "Múltiples citas encontradas")
        if result.get("error") == "sin_citas":
            return result.get("mensaje", "Sin citas próximas")
        if result.get("mensaje"):
            return result["mensaje"]
        return "Cancelación fallida"

    elif tool_name == "identificar_cliente":
        if success:
            nombre = result.get("nombre", "")
            apellido = result.get("apellido1", "")
            telefono = result.get("telefono", result.get("movil", ""))
            cliente_str = f"{nombre} {apellido}".strip()
            if cliente_str and telefono:
                return f"Cliente identificado: {cliente_str} ({telefono})"
            if cliente_str:
                return f"Cliente identificado: {cliente_str}"
            return "Cliente identificado"
        return "Cliente no encontrado"

    elif tool_name == "crear_recado":
        nombre = params.get("nombre_cliente", "")
        if success and result.get("mensaje_confirmacion"):
            return result["mensaje_confirmacion"]
        if nombre:
            return f"Recado de {nombre}"

    return base_desc


async def save_tool_call_actions(
    db: AsyncSession,
    call_id: UUID,
    messages: list[dict[str, Any]],
) -> int:
    """Extract tool calls from Ultravox messages and save as ai_decision_logs.

    Pairs TOOL_CALL messages with their TOOL_RESULT by invocationId.
    Returns the number of actions saved.
    """
    tool_calls: dict[str, dict] = {}
    tool_results: dict[str, dict] = {}

    for msg in messages:
        role = msg.get("role", "")
        inv_id = msg.get("invocationId")
        if not inv_id:
            continue
        if role == "MESSAGE_ROLE_TOOL_CALL":
            tool_calls[inv_id] = msg
        elif role == "MESSAGE_ROLE_TOOL_RESULT":
            tool_results[inv_id] = msg

    if not tool_calls:
        return 0

    saved = 0
    for inv_id, tc_msg in tool_calls.items():
        tr_msg = tool_results.get(inv_id)
        tool_name = tc_msg.get("toolName") or "unknown_tool"

        if tool_name not in TOOL_MAP:
            continue

        params = _parse_json_safe(tc_msg.get("text", ""))
        result = _parse_json_safe(tr_msg.get("text", "") if tr_msg else "")

        decision_type, base_desc = TOOL_MAP[tool_name]

        result_success = result.get("success")
        if result_success is True:
            action_status = "success"
        elif result_success is False:
            action_status = "failed"
        else:
            action_status = "success" if tr_msg else "pending"

        description = _build_description(tool_name, base_desc, params, result, result_success)

        decision_details: dict[str, Any] = {
            "tool_name": tool_name,
            "tool_args": params,
            "tool_result": result,
            "action_type": decision_type,
            "status": action_status,
        }

        if tool_name == "agendar_cita" and result_success:
            decision_details["booking"] = {
                k: result[k]
                for k in (
                    "cita_id",
                    "fecha",
                    "hora",
                    "servicio_nombre",
                    "cliente_nombre",
                    "empleado_nombre",
                    "cliente_nuevo",
                )
                if k in result
            }

        action_id = uuid4()
        try:
            async with db.begin_nested():
                await db.execute(
                    text("""
                        INSERT INTO ai_decision_logs (
                            id, call_id, decision_category,
                            model_id, model_version, model_provider,
                            input_reference,
                            decision_type, decision_value, confidence_score,
                            risk_level,
                            human_oversight_required, human_review_completed,
                            human_override,
                            action_executed, involves_employee,
                            is_emotion_analysis,
                            created_at, decision_details
                        ) VALUES (
                            :id, :call_id, 'service',
                            'ultravox-agent', '1.0', 'ultravox',
                            :input_reference,
                            :decision_type, :decision_value, 1.0,
                            'minimal',
                            false, false,
                            NULL,
                            true, false,
                            false,
                            NOW(), CAST(:decision_details AS JSONB)
                        )
                    """),
                    {
                        "id": action_id,
                        "call_id": call_id,
                        "input_reference": tool_name,
                        "decision_type": decision_type,
                        "decision_value": description,
                        "decision_details": json.dumps(decision_details, ensure_ascii=False),
                    },
                )
            saved += 1
        except (SQLAlchemyError, KeyError, TypeError) as e:
            logger.error("Error saving tool call action %s: %s", tool_name, e)

    return saved
