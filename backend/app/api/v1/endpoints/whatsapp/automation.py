"""WhatsApp automation routes: macros and SLA policies."""

import logging
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user_id,
    get_db,
    require_feature,
    require_permission,
    require_wa_admin,
    require_wa_manager,
)
from app.repositories.whatsapp_repository import (
    WAConversationRepository,
    WAMacroRepository,
    WASlaBreachRepository,
    WASlaPolicyRepository,
)
from app.schemas.whatsapp import (
    WAMacroCreateRequest,
    WAMacroResponse,
    WAMacroUpdateRequest,
    WASlaBreachResponse,
    WASlaPolicyCreateRequest,
    WASlaPolicyResponse,
    WASlaPolicyUpdateRequest,
)
from app.services.whatsapp_service import whatsapp_service

from ._helpers import _get_tenant_id, _get_tenant_settings, _get_wa_token

logger = logging.getLogger(__name__)

router = APIRouter()

_wa_auto_deps = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.automation.manage")),
]


# =============================================================================
# Automation: Macros
# =============================================================================


@router.get("/macros", response_model=list[WAMacroResponse], dependencies=_wa_auto_deps)
async def list_macros(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(None),
) -> list[WAMacroResponse]:
    """List quick reply macros."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAMacroRepository(db)
    items, _ = await repo.list_by_tenant(tenant_id, category=category)
    return [WAMacroResponse.model_validate(m) for m in items]


@router.post("/macros", response_model=WAMacroResponse, status_code=201, dependencies=_wa_auto_deps)
async def create_macro(
    body: WAMacroCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAMacroResponse:
    """Create a quick reply macro."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAMacroRepository(db)
    macro = await repo.create(
        {
            "tenant_id": tenant_id,
            "name": body.name,
            "shortcut": body.shortcut,
            "text": body.text,
            "category": body.category,
            "created_by": UUID(current_user_id),
        }
    )
    await db.commit()
    return WAMacroResponse.model_validate(macro)


@router.patch("/macros/{macro_id}", response_model=WAMacroResponse, dependencies=_wa_auto_deps)
async def update_macro(
    macro_id: UUID,
    body: WAMacroUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAMacroResponse:
    """Update a macro."""
    repo = WAMacroRepository(db)
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        macro = await repo.get_by_id(macro_id)
    else:
        macro = await repo.update(macro_id, updates)
    if not macro:
        raise HTTPException(status_code=404, detail="Macro not found")
    await db.commit()
    return WAMacroResponse.model_validate(macro)


@router.delete("/macros/{macro_id}", status_code=204, dependencies=_wa_auto_deps)
async def delete_macro(
    macro_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a macro."""
    repo = WAMacroRepository(db)
    deleted = await repo.delete(macro_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Macro not found")
    await db.commit()


@router.post("/macros/{macro_id}/execute", dependencies=_wa_auto_deps)
async def execute_macro(
    macro_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
    conversation_id: UUID = Query(...),
) -> dict:
    """Execute a macro's actions in a conversation.

    Supports multi-action macros with variable substitution:
    - {{contact.name}}, {{contact.phone}}
    - {{agent.name}}
    - {{conversation.id}}
    """
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    ts = await _get_tenant_settings(db, tenant_id)

    macro_repo = WAMacroRepository(db)
    macro = await macro_repo.get_by_id(macro_id)
    if not macro:
        raise HTTPException(status_code=404, detail="Macro not found")

    conv_repo = WAConversationRepository(db)
    conv = await conv_repo.get_with_contact(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Variable context for substitution
    variables = {
        "contact.name": conv.contact.display_name or conv.contact.phone_e164,
        "contact.phone": conv.contact.phone_e164,
        "agent.name": current_user_id,
        "conversation.id": str(conversation_id),
    }

    def _substitute(text_val: str) -> str:
        result = text_val
        for key, val in variables.items():
            result = result.replace("{{" + key + "}}", str(val))
        return result

    actions = macro.actions or [{"type": "send_message", "params": {"text": macro.text}}]
    results = []

    for action in actions:
        action_type = action.get("type", "send_message")
        params = action.get("params", {})

        if action_type == "send_message":
            text_val = _substitute(params.get("text", macro.text))
            try:
                await whatsapp_service.send_text_message(
                    phone_number_id=ts.phone_number_id,
                    to=conv.contact.phone_e164,
                    text=text_val,
                    token=_get_wa_token(ts),
                )
                results.append({"type": "send_message", "status": "sent"})
            except (httpx.HTTPError, ValueError) as e:
                logger.warning("Macro send_message failed: %s", e)
                results.append({"type": "send_message", "status": "failed"})

        elif action_type == "assign":
            agent_id = params.get("agent_id")
            if agent_id:
                conv.assignee_user_id = UUID(agent_id)
                conv.status = "assigned"
                results.append({"type": "assign", "status": "ok"})

        elif action_type == "add_tag":
            tag = params.get("tag")
            if tag:
                current_tags = list(conv.contact.tags or [])
                if tag not in current_tags:
                    current_tags.append(tag)
                    conv.contact.tags = current_tags
                results.append({"type": "add_tag", "status": "ok"})

        elif action_type == "close":
            conv.status = "closed"
            results.append({"type": "close", "status": "ok"})

    await db.commit()

    return {"macro_id": str(macro_id), "actions_executed": results}


# =============================================================================
# Automation: SLA Policies
# =============================================================================


@router.get("/sla/policies", response_model=list[WASlaPolicyResponse], dependencies=_wa_auto_deps)
async def list_sla_policies(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WASlaPolicyResponse]:
    """List SLA policies."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WASlaPolicyRepository(db)
    items = await repo.list_by_tenant(tenant_id)
    return [WASlaPolicyResponse.model_validate(p) for p in items]


@router.post(
    "/sla/policies", response_model=WASlaPolicyResponse, status_code=201, dependencies=_wa_auto_deps
)
async def create_sla_policy(
    body: WASlaPolicyCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WASlaPolicyResponse:
    """Create an SLA policy."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WASlaPolicyRepository(db)
    policy = await repo.create(
        {
            "tenant_id": tenant_id,
            **body.model_dump(),
        }
    )
    await db.commit()
    return WASlaPolicyResponse.model_validate(policy)


@router.patch(
    "/sla/policies/{policy_id}", response_model=WASlaPolicyResponse, dependencies=_wa_auto_deps
)
async def update_sla_policy(
    policy_id: UUID,
    body: WASlaPolicyUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WASlaPolicyResponse:
    """Update an SLA policy."""
    repo = WASlaPolicyRepository(db)
    updates = body.model_dump(exclude_unset=True)
    policy = await repo.update(policy_id, updates) if updates else await repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")
    await db.commit()
    return WASlaPolicyResponse.model_validate(policy)


@router.delete("/sla/policies/{policy_id}", status_code=204, dependencies=_wa_auto_deps)
async def delete_sla_policy(
    policy_id: UUID,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete an SLA policy."""
    repo = WASlaPolicyRepository(db)
    deleted = await repo.delete(policy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="SLA policy not found")
    await db.commit()


@router.get("/sla/breaches", dependencies=_wa_auto_deps)
async def list_sla_breaches(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    policy_id: UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List SLA breaches."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WASlaBreachRepository(db)
    items, total = await repo.list_by_tenant(tenant_id, policy_id=policy_id, skip=skip, limit=limit)
    return {
        "items": [WASlaBreachResponse.model_validate(b) for b in items],
        "total": total,
    }
