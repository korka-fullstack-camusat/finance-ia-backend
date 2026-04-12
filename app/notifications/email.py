"""Notifications email via SendGrid ou SMTP."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


async def send_email_notification(subject: str, body: str, to_email: Optional[str] = None) -> bool:
    """Envoie un email de notification."""
    from app.config import settings

    recipient = to_email or settings.NOTIFICATION_EMAIL
    if not recipient:
        logger.warning("[Email] NOTIFICATION_EMAIL non configuré, email ignoré")
        return False

    # Tentative via SendGrid
    if settings.SENDGRID_API_KEY:
        return await _send_via_sendgrid(subject, body, recipient)

    logger.warning("[Email] Aucun service email configuré (SendGrid requis)")
    return False


async def _send_via_sendgrid(subject: str, body: str, to_email: str) -> bool:
    """Envoie via l'API SendGrid."""
    try:
        import httpx
        from app.config import settings

        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": settings.SENDGRID_FROM_EMAIL, "name": "FinanceAI"},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )

        if response.status_code in (200, 202):
            logger.info(f"[Email] Envoyé à {to_email} : {subject}")
            return True
        else:
            logger.error(f"[Email] Erreur SendGrid {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"[Email] Exception : {e}")
        return False
