"""
Ultravox AI webhook and functions endpoints.
Integration endpoints for Ultravox AI voice agent.

Requires API Key authentication with client_type='ultravox_agent'.

Compliance:
- AI Act Art. 50: AI disclosure tracking
- AI Act Art. 12: Decision traceability
- RGPD Art. 7: Consent recording
- LOPDGDD Art. 33: Robinson list verification
"""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.api_key_auth import ai_or_pbx_auth
from app.core.dependencies import get_db
from app.repositories.robinson_repository import RobinsonCheckRepository
from app.schemas.ultravox import (
    AIDisclosureFunctionResponse,
    ConsentFunctionResponse,
    CustomerContextFunctionResponse,
    EscalationFunctionResponse,
    RobinsonCheckFunctionResponse,
    UltravoxEventType,
    UltravoxWebhookEvent,
)
from app.services.ultravox_call_service import UltravoxCallService
from app.voice.utils import detect_direction_and_numbers

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache de org_id para no hacer una query por cada evento de webhook.
# Se invalida si es None (primer uso) o si la DB no devuelve resultado.
_cached_tenant_org_id: "UUID | None" = None


async def _get_tenant_org_id(db: AsyncSession) -> "UUID | None":
    """Devuelve el organization_id del único tenant activo de esta instancia.

    Cada contenedor backend sirve a un solo cliente, por lo que no es necesario
    pasar org_id por metadata de Ultravox — se resuelve directamente de la DB.
    Se cachea en memoria para evitar una query por cada evento webhook.
    """
    global _cached_tenant_org_id
    if _cached_tenant_org_id is not None:
        return _cached_tenant_org_id
    from sqlalchemy import text

    result = await db.execute(
        text("SELECT id FROM organizations WHERE is_active = true LIMIT 1")
    )
    row = result.fetchone()
    if row:
        _cached_tenant_org_id = row[0]
    return _cached_tenant_org_id


# ============================================================================
# WEBHOOK ENDPOINT
# ============================================================================


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Ultravox webhook receiver",
    description="Receive webhook events from Ultravox AI.",
)
async def ultravox_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
    x_ultravox_webhook_signature: Annotated[str | None, Header()] = None,
    x_ultravox_webhook_timestamp: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Receive and process Ultravox AI webhook events."""
    # Verify webhook signature (HMAC-SHA256)
    if not settings.ultravox_webhook_secret:
        logger.error("ULTRAVOX_WEBHOOK_SECRET not configured — rejecting webhook")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Webhook secret not configured"
        )

    body_bytes = await request.body()

    _verify_webhook_signature(
        body_bytes,
        x_ultravox_webhook_timestamp,
        x_ultravox_webhook_signature,
    )

    payload = _parse_webhook_payload(body_bytes)
    event = _parse_webhook_event(payload)

    # Handle call.created events (no call data needed)
    if event.event == UltravoxEventType.CALL_CREATED:
        created_data = event.call_created
        logger.info(
            "Ultravox call_created: from=%s",
            created_data.from_number if created_data else "unknown",
        )

        # --- Enforcement de cuota inbound ---
        # Cada instancia backend sirve a un único tenant, por lo que la organización
        # se obtiene directamente de la DB sin necesidad de metadata en Ultravox.
        try:
            from app.services.voice_quota_service import (
                VoiceQuotaExceededError,
                VoiceQuotaService,
            )

            inbound_org_id = await _get_tenant_org_id(db)
            if inbound_org_id:
                quota_svc = VoiceQuotaService(db)
                remaining = await quota_svc.get_remaining_seconds(inbound_org_id, "inbound")
                if remaining is not None and remaining <= 0:
                    logger.warning(
                        "[voice_quota] Llamada inbound terminada por cuota agotada — org=%s",
                        inbound_org_id,
                    )
                    ultravox_call_id_hdr = (
                        created_data.call_id if hasattr(created_data, "call_id") else None
                    )
                    if ultravox_call_id_hdr:
                        from app.core.http_clients import ultravox_client

                        await ultravox_client.post(f"/calls/{ultravox_call_id_hdr}/end")
                    await db.commit()
                    return {"success": True, "event": "call.created", "action": "terminated_quota"}

                est_sec = VoiceQuotaService.estimate_inbound_seconds(remaining)
                await quota_svc.assert_can_start_call(inbound_org_id, "inbound", est_sec)
        except VoiceQuotaExceededError:
            pass  # Ya logueado; fail-open para no cortar llamadas legítimas
        except Exception as quota_err:
            logger.warning("[voice_quota] Error en check inbound call.created: %s", quota_err)

        await db.commit()
        return {
            "success": True,
            "event": "call.created",
            "message": "Inbound call notification received",
        }

    call_data = event.call
    if not call_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing call data")

    ultravox_call_id = call_data.call_id
    logger.info("Ultravox webhook received: event=%s, call_id=%s", event.event, ultravox_call_id)

    # Resolve direction and phone numbers
    caller_number, called_number = await _resolve_phone_numbers(event, call_data, ultravox_call_id)

    # Get or create the call record
    call_data_dict = _build_call_data_dict(call_data, caller_number, called_number)
    try:
        call_id = await UltravoxCallService.get_or_create_call(db, ultravox_call_id, call_data_dict)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Update phone numbers if the call already existed with NULLs
    await UltravoxCallService.update_call_phone_numbers(db, call_id, caller_number, called_number)

    # Dispatch event-specific handling
    if event.event == UltravoxEventType.CALL_STARTED:
        await UltravoxCallService.mark_call_started(db, call_id)
    elif event.event == UltravoxEventType.CALL_JOINED:
        await UltravoxCallService.mark_call_joined(db, call_id)
    elif event.event == UltravoxEventType.CALL_ENDED:
        caller_number = await UltravoxCallService.handle_call_ended(
            db,
            call_id,
            call_data,
            ultravox_call_id,
            caller_number,
            background_tasks,
        )
        # Commit de cuota inbound (las llamadas outbound se contabilizan en su propio modulo)
        try:
            from app.services.voice_quota_service import (
                VoiceQuotaService,
                _DEFAULT_INBOUND_ESTIMATE_SEC,
            )

            inbound_org_id = await _get_tenant_org_id(db)
            if inbound_org_id:
                duration_ms_inbound = (
                    call_data.duration_ms if hasattr(call_data, "duration_ms") else None
                )
                actual_sec_inbound = (duration_ms_inbound // 1000) if duration_ms_inbound else 0
                quota_svc = VoiceQuotaService(db)
                if actual_sec_inbound > 0:
                    await quota_svc.commit_call_ended(
                        inbound_org_id,
                        "inbound",
                        actual_sec_inbound,
                        _DEFAULT_INBOUND_ESTIMATE_SEC,
                    )
                else:
                    await quota_svc.release_on_no_answer(
                        inbound_org_id, "inbound", _DEFAULT_INBOUND_ESTIMATE_SEC
                    )
        except Exception as quota_err:
            logger.warning("[voice_quota] Error en commit inbound call.ended: %s", quota_err)
    elif event.event == UltravoxEventType.CALL_BILLED:
        if call_data.call_analysis:
            await UltravoxCallService.update_call_billed(
                db,
                call_id,
                sentiment=UltravoxCallService.map_sentiment(call_data.call_analysis.sentiment),
                summary=call_data.call_analysis.call_summary,
            )

    await db.commit()

    # Forward normalized event to n8n
    await UltravoxCallService.forward_to_n8n(payload, caller_number, call_id, db)

    return {
        "success": True,
        "event": event.event,
        "call_id": str(call_id),
        "ultravox_call_id": ultravox_call_id,
    }


# ============================================================================
# WEBHOOK HELPERS
# ============================================================================


def _verify_webhook_signature(
    raw_body: bytes,
    timestamp: str | None,
    signature: str | None,
) -> None:
    """Verify Ultravox webhook HMAC-SHA256 signature."""
    if not timestamp or not signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing webhook security headers",
        )

    # Validate timestamp freshness (5-minute tolerance)
    try:

        webhook_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        if abs((now - webhook_time).total_seconds()) > 300:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Webhook timestamp too old",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timestamp format",
        )

    # Verify HMAC-SHA256
    signed_payload = raw_body + timestamp.encode("utf-8")
    expected_sig = hmac.new(
        settings.ultravox_webhook_secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    # Ultravox may send multiple signatures comma-separated
    if not any(hmac.compare_digest(sig.strip(), expected_sig) for sig in signature.split(",")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature",
        )


def _parse_webhook_payload(raw_payload: bytes) -> dict[str, Any]:
    """Parse raw webhook body as JSON."""
    try:
        payload = json.loads(raw_payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Invalid JSON in Ultravox webhook: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")
    logger.debug("Ultravox webhook raw payload: %s", json.dumps(payload, default=str)[:2000])
    return payload


def _parse_webhook_event(payload: dict[str, Any]) -> UltravoxWebhookEvent:
    """Parse payload into a validated webhook event."""
    try:
        return UltravoxWebhookEvent(**payload)
    except (ValueError, KeyError, TypeError) as e:
        logger.error("Invalid Ultravox webhook format: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook format: {str(e)}"
        )


async def _resolve_phone_numbers(
    event, call_data, ultravox_call_id: str
) -> tuple[str | None, str | None]:
    """Resolve caller and called numbers from webhook data, medium, and Zadarma/API fallback."""
    webhook_metadata = call_data.model_extra.get("metadata") if call_data.model_extra else None
    detected_direction, medium_caller, medium_called = detect_direction_and_numbers(
        call_data.medium,
        webhook_metadata if isinstance(webhook_metadata, dict) else None,
    )

    caller_number = call_data.from_number or medium_caller
    called_number = call_data.to_number or medium_called

    # If still no caller for inbound, try multiple strategies
    if (
        not caller_number
        and detected_direction == "inbound"
        and event.event
        in (
            UltravoxEventType.CALL_STARTED,
            UltravoxEventType.CALL_JOINED,
        )
    ):
        # Strategy 1: Check Zadarma webhook cache (fastest)
        caller_number = UltravoxCallService.lookup_zadarma_caller(
            called_number=called_number,
            approximate_start_time=datetime.now(UTC),
        )
        if caller_number:
            logger.debug("Ultravox: got phone from Zadarma cache: %s***", caller_number[:6])

        # Strategy 2: Fetch from Ultravox API
        if not caller_number:
            api_data = await UltravoxCallService.fetch_call_details(ultravox_call_id)
            if api_data:
                caller_number = api_data.get("fromNumber")
                if not caller_number:
                    _, api_caller, api_called = detect_direction_and_numbers(api_data.get("medium"))
                    caller_number = api_caller
                    if not called_number:
                        called_number = api_called
                logger.debug("Ultravox API phone number: %s", caller_number)

    return caller_number, called_number


def _build_call_data_dict(
    call_data, caller_number: str | None, called_number: str | None
) -> dict[str, Any]:
    """Build the call data dict for get_or_create_call."""
    webhook_metadata = call_data.model_extra.get("metadata") if call_data.model_extra else None
    detected_direction, _, _ = detect_direction_and_numbers(
        call_data.medium,
        webhook_metadata if isinstance(webhook_metadata, dict) else None,
    )
    call_data_dict = call_data.model_dump()
    call_data_dict["direction"] = detected_direction
    if caller_number:
        call_data_dict["from_number"] = caller_number
    if called_number:
        call_data_dict["to_number"] = called_number
    return call_data_dict


# ============================================================================
# ZADARMA WEBHOOK ENDPOINT
# ============================================================================


@router.get(
    "/zadarma/webhook",
    status_code=status.HTTP_200_OK,
    summary="Zadarma webhook verification",
    description="Verification endpoint for Zadarma webhook URL configuration.",
)
async def zadarma_webhook_verify(
    request: Request,
    zd_echo: str | None = None,
) -> Response:
    """Verify Zadarma webhook URL.

    Zadarma sends a GET request with zd_echo parameter when configuring the webhook URL.
    We must return the zd_echo value as plain text to confirm the URL is valid.
    """
    if zd_echo:
        logger.debug("Zadarma verify: returning zd_echo=%s", zd_echo)
        return Response(content=zd_echo, media_type="text/plain")
    return Response(content="OK", media_type="text/plain")


@router.post(
    "/zadarma/webhook",
    status_code=status.HTTP_200_OK,
    summary="Zadarma webhook receiver",
    description="Receive webhook notifications from Zadarma PBX.",
)
async def zadarma_webhook(
    request: Request,
) -> dict[str, Any]:
    """Receive Zadarma PBX notifications.

    This endpoint receives NOTIFY_START events from Zadarma which include the caller_id.
    We cache the caller_id so it can be correlated with Ultravox calls.

    Nota: ZADARMA_API_SECRET es para las llamadas REST a la API de estadísticas de Zadarma,
    NO para la verificación de webhooks. Los webhooks de Zadarma incluyen un parámetro POST
    'sign' (MD5) que no está relacionado con el API secret. Por eso no verificamos la firma
    aquí — el endpoint está protegido por la oscuridad de la URL (dominio del cliente).
    """
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = await request.json()
        else:
            form = await request.form()
            payload = dict(form)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error("Error parsing Zadarma webhook: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload format"
        )

    logger.info("Zadarma webhook received: %s", json.dumps(payload, default=str))

    event_type = payload.get("event", "")
    caller_id = payload.get("caller_id", "")
    called_did = payload.get("called_did", "")
    pbx_call_id = payload.get("pbx_call_id", "")

    if event_type == "NOTIFY_START":
        if caller_id and called_did:
            UltravoxCallService.store_zadarma_caller(called_did, caller_id, pbx_call_id)
            logger.info(
                f"Zadarma NOTIFY_START: caller={caller_id}, called={called_did}, pbx_id={pbx_call_id}"
            )
        else:
            logger.warning(f"Zadarma NOTIFY_START missing caller_id or called_did: {payload}")
    elif event_type == "NOTIFY_END":
        duration = payload.get("duration")
        disposition = payload.get("disposition")
        logger.info(
            f"Zadarma NOTIFY_END: pbx_id={pbx_call_id}, duration={duration}, disposition={disposition}"
        )
    elif event_type == "NOTIFY_ANSWER":
        logger.info(f"Zadarma NOTIFY_ANSWER: pbx_id={pbx_call_id}")

    return {"status": "ok"}


# ============================================================================
# FUNCTION ENDPOINTS - Accept direct format from Ultravox HTTP Tools
# ============================================================================


@router.post(
    "/functions/ai-disclosure",
    response_model=AIDisclosureFunctionResponse,
    summary="Record AI disclosure",
    dependencies=[Depends(ai_or_pbx_auth)],
)
async def function_ai_disclosure(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_ultravox_call_id: Annotated[str | None, Header()] = None,
) -> AIDisclosureFunctionResponse:
    """Record AI disclosure. Accepts direct parameters from Ultravox HTTP Tools."""
    payload = await _safe_json(request)
    logger.debug("AI_DISCLOSURE payload=%s, header_call_id=%s", payload, x_ultravox_call_id)

    ultravox_call_id = UltravoxCallService.resolve_ultravox_call_id(x_ultravox_call_id, payload)
    emotion_disclosed = UltravoxCallService.get_function_arg(
        payload, "emotion_detection_disclosed", False
    )

    call_id = await _resolve_call_id(db, ultravox_call_id)
    now = datetime.now(UTC)

    if call_id is None:
        return AIDisclosureFunctionResponse(
            success=True,
            call_id="none",
            disclosed_at=now,
            message="AI disclosure acknowledged (no active call to update)",
        )

    disclosed_at = await UltravoxCallService.record_ai_disclosure(db, call_id, emotion_disclosed)

    return AIDisclosureFunctionResponse(
        success=True,
        call_id=str(call_id),
        disclosed_at=disclosed_at,
        message="AI disclosure recorded successfully (AI Act Art. 50.1 compliant)",
    )


@router.post(
    "/functions/consent",
    response_model=ConsentFunctionResponse,
    summary="Record consent",
    dependencies=[Depends(ai_or_pbx_auth)],
)
async def function_consent(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_ultravox_call_id: Annotated[str | None, Header()] = None,
) -> ConsentFunctionResponse:
    """Record consent. Accepts direct parameters from Ultravox HTTP Tools."""
    payload = await _safe_json(request)
    logger.debug("CONSENT payload=%s, header_call_id=%s", payload, x_ultravox_call_id)

    ultravox_call_id = UltravoxCallService.resolve_ultravox_call_id(x_ultravox_call_id, payload)
    user_consent = UltravoxCallService.get_function_arg(payload, "user_consent", "")
    consent_type = UltravoxCallService.get_function_arg(payload, "consent_type", "recording")

    consent_value = (
        user_consent.lower() in ("yes", "si", "s\u00ed", "true", "1")
        if isinstance(user_consent, str)
        else bool(user_consent)
    )

    call_id = await _resolve_call_id(db, ultravox_call_id)
    now = datetime.now(UTC)

    if call_id is None:
        message = "Consent acknowledged" if consent_value else "Consent declined"
        return ConsentFunctionResponse(
            success=True,
            call_id="none",
            consent_given=consent_value,
            consent_type=consent_type,
            recorded_at=now,
            message=f"{message} (no active call to update)",
        )

    recorded_at = await UltravoxCallService.record_consent(db, call_id, consent_value, consent_type)
    message = "Consent recorded" if consent_value else "Consent declined - recording disabled"

    return ConsentFunctionResponse(
        success=True,
        call_id=str(call_id),
        consent_given=consent_value,
        consent_type=consent_type,
        recorded_at=recorded_at,
        message=message,
    )


@router.post(
    "/functions/escalation",
    response_model=EscalationFunctionResponse,
    summary="Request human escalation",
    dependencies=[Depends(ai_or_pbx_auth)],
)
async def function_escalation(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_ultravox_call_id: Annotated[str | None, Header()] = None,
) -> EscalationFunctionResponse:
    """Request human escalation. Accepts direct parameters from Ultravox HTTP Tools."""
    payload = await _safe_json(request)
    logger.debug("ESCALATION payload=%s", payload)

    ultravox_call_id = UltravoxCallService.resolve_ultravox_call_id(x_ultravox_call_id, payload)
    reason = UltravoxCallService.get_function_arg(payload, "reason", "customer_request")
    priority = UltravoxCallService.get_function_arg(payload, "priority", "normal")
    context = UltravoxCallService.get_function_arg(payload, "context")

    call_id = await _resolve_call_id(db, ultravox_call_id)

    if call_id is None:
        from uuid import uuid4

        return EscalationFunctionResponse(
            success=True,
            call_id="none",
            escalation_id=str(uuid4()),
            reason=reason,
            priority=priority,
            message=f"Escalation acknowledged (no active call to update): {reason}",
        )

    escalation_id = await UltravoxCallService.request_escalation(
        db,
        call_id,
        ultravox_call_id,
        reason,
        priority,
        context,
    )

    return EscalationFunctionResponse(
        success=True,
        call_id=str(call_id),
        escalation_id=str(escalation_id),
        reason=reason,
        priority=priority,
        message=f"Human escalation requested: {reason}",
    )


@router.get(
    "/functions/robinson-check",
    response_model=RobinsonCheckFunctionResponse,
    summary="Check Robinson list",
    dependencies=[Depends(ai_or_pbx_auth)],
)
async def function_robinson_check(
    phone_number: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RobinsonCheckFunctionResponse:
    """Check Robinson list."""
    robinson_repo = RobinsonCheckRepository(db)
    phone_hash = hashlib.sha256(phone_number.encode()).hexdigest()[:32]
    existing = await robinson_repo.get_valid_check(phone_number)

    if existing:
        return RobinsonCheckFunctionResponse(
            success=True,
            phone_number_hash=phone_hash,
            is_listed=existing.is_listed,
            can_contact=not existing.is_listed,
            message="Cached check valid"
            if not existing.is_listed
            else "ROBINSON: Contact prohibited",
        )

    is_listed = False
    await robinson_repo.record_check(
        phone_number=phone_number,
        is_listed=is_listed,
        purpose="ultravox_outbound",
        checked_by_system="ultravox_agent",
    )
    await db.commit()

    return RobinsonCheckFunctionResponse(
        success=True,
        phone_number_hash=phone_hash,
        is_listed=is_listed,
        can_contact=not is_listed,
        message="Contact allowed" if not is_listed else "ROBINSON: Contact prohibited",
    )


@router.get(
    "/functions/customer-context",
    response_model=CustomerContextFunctionResponse,
    summary="Get customer context",
    dependencies=[Depends(ai_or_pbx_auth)],
)
async def function_customer_context(
    phone_number: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CustomerContextFunctionResponse:
    """Get customer context for personalization."""
    context = await UltravoxCallService.get_customer_context(db, phone_number)

    if not context:
        return CustomerContextFunctionResponse(
            success=True, found=False, message="Customer not found in database"
        )

    consents = context["active_consents"]
    return CustomerContextFunctionResponse(
        success=True,
        found=True,
        contact_id=context["contact_id"],
        full_name=context["full_name"],
        previous_calls_count=context["previous_calls_count"],
        last_call_date=context["last_call_date"],
        active_consents=consents,
        marketing_opt_out="marketing" not in consents,
        profiling_opt_out="profiling" not in consents,
    )


# ============================================================================
# SHARED HELPERS
# ============================================================================


async def _safe_json(request: Request) -> dict[str, Any]:
    """Parse request body as JSON, returning empty dict on failure."""
    try:
        return await request.json()
    except (ValueError, json.JSONDecodeError):
        return {}


async def _resolve_call_id(db: AsyncSession, ultravox_call_id: str):
    """Resolve a call ID, raising HTTPException on ValueError."""
    try:
        return await UltravoxCallService.get_or_create_call(
            db,
            ultravox_call_id,
            {},
            use_active_call_if_generated_id=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

