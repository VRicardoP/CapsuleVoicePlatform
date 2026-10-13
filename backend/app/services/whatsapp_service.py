"""WhatsApp Business API client via Meta Graph API."""

import hashlib
import hmac
import logging
import re

from app.config.settings import settings
from app.core import http_clients

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com"


class WhatsAppAPIError(Exception):
    """Error returned by the Meta WhatsApp API."""

    def __init__(self, status_code: int, message: str, meta_code: int | None = None):
        self.status_code = status_code
        self.message = message
        self.meta_code = meta_code
        super().__init__(message)


class WhatsAppService:
    """Meta Graph API client for WhatsApp Business."""

    def __init__(self) -> None:
        self._api_version = settings.whatsapp_api_version

    def _url(self, phone_number_id: str, path: str = "messages") -> str:
        return f"{GRAPH_API_BASE}/{self._api_version}/{phone_number_id}/{path}"

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def send_text_message(
        self,
        phone_number_id: str,
        to: str,
        text: str,
        token: str,
    ) -> dict:
        """Send a text message via WhatsApp."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        response = await http_clients.whatsapp_client.post(
            self._url(phone_number_id),
            headers=self._headers(token),
            json=payload,
        )
        if not response.is_success:
            body = (
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            meta_error = body.get("error", {})
            error_msg = meta_error.get("message", response.text[:200])
            logger.error(
                "Meta API error %s: %s (code=%s)",
                response.status_code,
                error_msg,
                meta_error.get("code"),
            )
            raise WhatsAppAPIError(response.status_code, error_msg, meta_error.get("code"))
        return response.json()

    async def send_template_message(
        self,
        phone_number_id: str,
        to: str,
        template_name: str,
        language: str,
        token: str,
        components: list[dict] | None = None,
    ) -> dict:
        """Send a template message via WhatsApp (used to re-open 24h window)."""
        template_obj: dict = {
            "name": template_name,
            "language": {"code": language},
        }
        if components:
            template_obj["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": template_obj,
        }
        response = await http_clients.whatsapp_client.post(
            self._url(phone_number_id),
            headers=self._headers(token),
            json=payload,
        )
        if not response.is_success:
            body = (
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            meta_error = body.get("error", {})
            error_msg = meta_error.get("message", response.text[:200])
            logger.error(
                "Meta API template error %s: %s (code=%s)",
                response.status_code,
                error_msg,
                meta_error.get("code"),
            )
            raise WhatsAppAPIError(response.status_code, error_msg, meta_error.get("code"))
        return response.json()

    async def mark_as_read(
        self,
        phone_number_id: str,
        message_id: str,
        token: str,
    ) -> None:
        """Mark a message as read in WhatsApp."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        response = await http_clients.whatsapp_client.post(
            self._url(phone_number_id),
            headers=self._headers(token),
            json=payload,
        )
        response.raise_for_status()

    async def get_media_url(
        self,
        media_id: str,
        token: str,
    ) -> str:
        """Get a download URL for a media attachment."""
        url = f"{GRAPH_API_BASE}/{self._api_version}/{media_id}"
        response = await http_clients.whatsapp_client.get(url, headers=self._headers(token))
        response.raise_for_status()
        return response.json().get("url", "")

    @staticmethod
    def _validate_media_url(url: str) -> None:
        """Validate that media URL is safe to fetch (SSRF prevention)."""
        import ipaddress
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.scheme not in ("https",):
            raise WhatsAppAPIError(400, "Only HTTPS URLs are allowed")
        if not parsed.hostname:
            raise WhatsAppAPIError(400, "Invalid URL")
        # Block internal/private IPs
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise WhatsAppAPIError(400, "Internal URLs are not allowed")
        except ValueError:
            pass  # hostname is a domain name, not IP — OK

    async def upload_media_for_template(
        self,
        image_url: str,
        token: str,
    ) -> str:
        """Upload an image to Meta via Resumable Upload API for template headers.

        1. Download the image from the URL
        2. Create an upload session with Meta
        3. Upload the binary data
        4. Return the file handle (h:...)
        """
        app_id = settings.whatsapp_app_id
        if not app_id:
            raise WhatsAppAPIError(
                400, "WHATSAPP_APP_ID not configured — required for media uploads"
            )

        # Validate URL to prevent SSRF
        self._validate_media_url(image_url)

        # Step 1: Download the image
        dl_response = await http_clients.whatsapp_client.get(
            image_url, headers={}, follow_redirects=True
        )
        if not dl_response.is_success:
            raise WhatsAppAPIError(
                400, f"Failed to download image from URL: {dl_response.status_code}"
            )
        image_bytes = dl_response.content
        content_type = dl_response.headers.get("content-type", "image/jpeg")
        # Normalize content type
        if "jpeg" in content_type or "jpg" in content_type:
            content_type = "image/jpeg"
        elif "png" in content_type:
            content_type = "image/png"
        else:
            content_type = "image/jpeg"

        file_length = len(image_bytes)
        logger.info("Downloaded template image: %d bytes, type=%s", file_length, content_type)

        # Step 2: Create upload session
        session_url = f"{GRAPH_API_BASE}/{self._api_version}/{app_id}/uploads"
        session_response = await http_clients.whatsapp_client.post(
            session_url,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "file_length": str(file_length),
                "file_type": content_type,
                "file_name": "template_header.jpg",
            },
        )
        if not session_response.is_success:
            body = (
                session_response.json()
                if session_response.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            error_msg = body.get("error", {}).get("message", session_response.text[:200])
            logger.error("Meta upload session error: %s", error_msg)
            raise WhatsAppAPIError(
                session_response.status_code, f"Upload session failed: {error_msg}"
            )

        upload_id = session_response.json().get("id")
        if not upload_id:
            raise WhatsAppAPIError(500, "Meta returned no upload session ID")
        logger.info("Created upload session: %s", upload_id)

        # Step 3: Upload binary data
        upload_url = f"{GRAPH_API_BASE}/{self._api_version}/{upload_id}"
        upload_response = await http_clients.whatsapp_client.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {token}",
                "file_offset": "0",
                "Content-Type": content_type,
            },
            content=image_bytes,
        )
        if not upload_response.is_success:
            body = (
                upload_response.json()
                if upload_response.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            error_msg = body.get("error", {}).get("message", upload_response.text[:200])
            logger.error("Meta upload data error: %s", error_msg)
            raise WhatsAppAPIError(upload_response.status_code, f"Upload failed: {error_msg}")

        handle = upload_response.json().get("h")
        if not handle:
            raise WhatsAppAPIError(500, "Meta returned no file handle after upload")
        logger.info("Upload complete, handle: %s...", handle[:30])
        return handle

    async def submit_template(
        self,
        waba_id: str,
        name: str,
        language: str,
        category: str,
        body_text: str,
        token: str,
        header_type: str | None = None,
        header_content: str | None = None,
        footer: str | None = None,
        buttons: list[dict] | None = None,
        body_examples: list[str] | None = None,
    ) -> dict:
        """Submit a template to Meta for review.

        Calls POST /{waba_id}/message_templates.
        Returns Meta's response including the template ID.
        """
        components = []

        # Header component
        if header_type and header_content:
            header_component: dict = {"type": "HEADER"}
            if header_type.upper() == "TEXT":
                header_component["format"] = "TEXT"
                header_component["text"] = header_content
            else:
                header_component["format"] = header_type.upper()
                header_component["example"] = {"header_handle": [header_content]}
            components.append(header_component)

        # Body component (always present)
        body_component: dict = {"type": "BODY", "text": body_text}
        # Add variable examples if body has {{N}} placeholders
        if body_examples:
            body_component["example"] = {"body_text": [body_examples]}
        components.append(body_component)

        # Footer component
        if footer:
            components.append({"type": "FOOTER", "text": footer})

        # Buttons component
        if buttons:
            components.append({"type": "BUTTONS", "buttons": buttons})

        payload = {
            "name": name,
            "language": language,
            "category": category,
            "components": components,
        }

        url = f"{GRAPH_API_BASE}/{self._api_version}/{waba_id}/message_templates"
        response = await http_clients.whatsapp_client.post(
            url,
            headers=self._headers(token),
            json=payload,
        )
        if not response.is_success:
            body = (
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            meta_error = body.get("error", {})
            error_msg = meta_error.get("message", response.text[:200])
            logger.error(
                "Meta API submit template error %s: %s (code=%s)",
                response.status_code,
                error_msg,
                meta_error.get("code"),
            )
            raise WhatsAppAPIError(response.status_code, error_msg, meta_error.get("code"))
        return response.json()

    async def delete_template(
        self,
        waba_id: str,
        template_name: str,
        token: str,
    ) -> None:
        """Elimina una plantilla en Meta por nombre.

        Meta borra TODAS las variantes de idioma con ese nombre.
        """
        url = f"{GRAPH_API_BASE}/{self._api_version}/{waba_id}/message_templates"
        response = await http_clients.whatsapp_client.delete(
            url,
            headers=self._headers(token),
            params={"name": template_name},
        )
        if not response.is_success:
            body = (
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            meta_error = body.get("error", {})
            error_msg = meta_error.get("message", response.text[:200])
            logger.error(
                "Meta API delete template error %s: %s (code=%s)",
                response.status_code,
                error_msg,
                meta_error.get("code"),
            )
            raise WhatsAppAPIError(response.status_code, error_msg, meta_error.get("code"))

    async def fetch_templates(
        self,
        waba_id: str,
        token: str,
    ) -> list[dict]:
        """Fetch all message templates from Meta.

        Handles cursor-based pagination automatically.
        Returns the full list of template objects from Meta.
        """
        url = f"{GRAPH_API_BASE}/{self._api_version}/{waba_id}/message_templates"
        params: dict = {"limit": "100"}
        all_templates: list[dict] = []

        while url:
            response = await http_clients.whatsapp_client.get(
                url,
                headers=self._headers(token),
                params=params,
            )
            if not response.is_success:
                body = (
                    response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else {}
                )
                meta_error = body.get("error", {})
                error_msg = meta_error.get("message", response.text[:200])
                logger.error(
                    "Meta API fetch templates error %s: %s", response.status_code, error_msg
                )
                raise WhatsAppAPIError(response.status_code, error_msg, meta_error.get("code"))

            data = response.json()
            all_templates.extend(data.get("data", []))

            # Follow pagination cursor
            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}  # next URL already includes params

        logger.info("Fetched %d templates from Meta (WABA %s)", len(all_templates), waba_id)
        return all_templates

    @staticmethod
    def count_body_variables(body_text: str) -> int:
        """Count {{N}} placeholders in body text."""
        if not body_text:
            return 0
        return len(re.findall(r"\{\{\d+\}\}", body_text))

    @staticmethod
    def parse_meta_template(meta_template: dict) -> dict:
        """Convert a Meta template object to our local DB format."""
        status_map = {
            "APPROVED": "approved",
            "PENDING": "pending",
            "REJECTED": "rejected",
            "PAUSED": "paused",
            "DISABLED": "disabled",
            "IN_APPEAL": "rejected",
        }

        header_type = None
        header_content = None
        body_text = ""
        footer = None
        buttons = None

        for comp in meta_template.get("components", []):
            comp_type = comp.get("type", "").upper()
            if comp_type == "HEADER":
                header_type = comp.get("format")
                header_content = comp.get("text")
                # For media headers (IMAGE, VIDEO, DOCUMENT), extract example URL
                if not header_content and header_type in ("IMAGE", "VIDEO", "DOCUMENT"):
                    example = comp.get("example", {})
                    handles = example.get("header_handle", [])
                    if handles:
                        header_content = handles[0]
            elif comp_type == "BODY":
                body_text = comp.get("text", "")
            elif comp_type == "FOOTER":
                footer = comp.get("text")
            elif comp_type == "BUTTONS":
                buttons = {"buttons": comp.get("buttons", [])}

        return {
            "meta_template_id": meta_template["id"],
            "name": meta_template["name"],
            "language": meta_template.get("language", "en_US"),
            "category": meta_template.get("category", "MARKETING").upper(),
            "status": status_map.get(meta_template.get("status", "").upper(), "draft"),
            "header_type": header_type,
            "header_content": header_content,
            "body_text": body_text,
            "footer": footer,
            "buttons": buttons,
            "meta_rejected_reason": meta_template.get("rejected_reason"),
        }

    @staticmethod
    def get_token(tenant_settings) -> str:
        """Extract the WhatsApp API token from tenant settings.

        Currently api_token_enc is stored as plaintext.
        When Fernet encryption is added, decrypt here.
        """
        return tenant_settings.api_token_enc

    @staticmethod
    def verify_webhook_signature(
        payload_bytes: bytes,
        signature_header: str,
        app_secret: str,
    ) -> bool:
        """
        Verify X-Hub-Signature-256 from Meta webhook.

        Returns True if HMAC-SHA256 matches.
        """
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_sig = signature_header[7:]  # Remove "sha256=" prefix
        computed_sig = hmac.new(
            app_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed_sig, expected_sig)


# Singleton
whatsapp_service = WhatsAppService()
