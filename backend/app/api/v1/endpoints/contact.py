"""
Contact form endpoints.
Allows authenticated users to send contact emails to the company.
"""

import html
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Annotated
from uuid import UUID

import aiosmtplib
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.dependencies import get_current_user_id, get_db
from app.repositories.gdpr_repository import AuditLogRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.contact import ContactRequest, ContactResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Rate limiting: max 5 contact emails per user per hour
CONTACT_RATE_LIMIT = 5
CONTACT_RATE_WINDOW_HOURS = 1


async def send_email_task(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: str,
    reply_to: str | None = None,
) -> None:
    """Background task to send email via SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to_email
        if reply_to:
            msg["Reply-To"] = reply_to

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user if settings.smtp_user else None,
            password=settings.smtp_password if settings.smtp_password else None,
            start_tls=settings.smtp_tls,
        )
        logger.info(f"Contact email sent successfully to {to_email}")
    except (aiosmtplib.SMTPException, OSError) as e:
        logger.error("Error sending contact email: %s", e)


async def check_rate_limit(db: AsyncSession, user_id: UUID) -> bool:
    """Check if user has exceeded contact email rate limit."""
    repo = TenantRepository(db)
    return await repo.check_rate_limit(
        user_id, "INSERT", "contact_emails", CONTACT_RATE_LIMIT, CONTACT_RATE_WINDOW_HOURS
    )


@router.post(
    "/send",
    response_model=ContactResponse,
    summary="Send contact email",
    description="Send a contact message to the company. Limited to 5 messages per hour.",
)
async def send_contact_email(
    request: Request,
    contact_data: ContactRequest,
    background_tasks: BackgroundTasks,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactResponse:
    """
    Send a contact email to the company.

    The email will include the user's information and the message content.
    Email is sent asynchronously in the background for faster response.
    Rate limited to 5 messages per hour per user.
    """
    user_id = UUID(current_user_id)
    user_repo = UserRepository(db)
    audit_repo = AuditLogRepository(db)

    # Check rate limit
    if not await check_rate_limit(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Has excedido el límite de {CONTACT_RATE_LIMIT} mensajes por hora. Inténtalo más tarde.",
        )

    # Get user info for the email
    user_data = await user_repo.get_decrypted_user_data(user_id)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user_email = user_data.get("email", "No disponible")
    user_name = user_data.get("name", "Usuario")
    user_company = user_data.get("company", "No especificada")

    # Build email content
    email_subject = f"[Contacto Dashboard] {contact_data.subject}"

    body_text = f"""
Nuevo mensaje de contacto desde el Dashboard de Sfera AI

De: {user_name}
Email: {user_email}
Empresa: {user_company}
Asunto: {contact_data.subject}

Mensaje:
{contact_data.message}

---
Este mensaje fue enviado desde el formulario de contacto del Dashboard.
    """.strip()

    body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1e3a8a, #0891b2); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0; }}
        .footer {{ background: #1f2937; color: #9ca3af; padding: 15px; text-align: center; font-size: 12px; border-radius: 0 0 8px 8px; }}
        .info-row {{ margin: 10px 0; }}
        .label {{ font-weight: bold; color: #4b5563; }}
        .message-box {{ background: white; padding: 15px; border-left: 4px solid #0891b2; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">Nuevo mensaje de contacto</h2>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">Dashboard Sfera AI</p>
        </div>
        <div class="content">
            <div class="info-row">
                <span class="label">De:</span> {html.escape(user_name)}
            </div>
            <div class="info-row">
                <span class="label">Email:</span> {html.escape(user_email)}
            </div>
            <div class="info-row">
                <span class="label">Empresa:</span> {html.escape(user_company)}
            </div>
            <div class="info-row">
                <span class="label">Asunto:</span> {html.escape(contact_data.subject)}
            </div>
            <h3>Mensaje:</h3>
            <div class="message-box">
                {html.escape(contact_data.message).replace(chr(10), "<br>")}
            </div>
        </div>
        <div class="footer">
            Este mensaje fue enviado desde el formulario de contacto del Dashboard de Sfera AI
        </div>
    </div>
</body>
</html>
    """.strip()

    # Log the action first (before sending)
    client_ip = request.client.host if request.client else None
    try:
        await audit_repo.log_action(
            action="INSERT",
            entity_type="contact_emails",
            user_id=user_id,
            details={
                "subject": contact_data.subject,
                "to_email": settings.contact_email,
            },
            ip_address=client_ip,
        )
        await db.commit()
    except (SQLAlchemyError, ValueError) as e:
        logger.warning("Failed to log contact action: %s", e)

    # Queue email to be sent in background
    background_tasks.add_task(
        send_email_task,
        to_email=settings.contact_email,
        subject=email_subject,
        body_html=body_html,
        body_text=body_text,
        reply_to=user_email,
    )

    return ContactResponse(
        success=True,
        message="Tu mensaje ha sido enviado correctamente. Nos pondremos en contacto contigo pronto.",
    )
