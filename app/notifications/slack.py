"""Notifications Slack via Webhook."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def send_slack_notification(
    task_name: str,
    summary: str,
    duration: float = 0.0,
    status: str = "success",
) -> bool:
    """Envoie une notification Slack via webhook."""
    from app.config import settings

    if not settings.SLACK_WEBHOOK_URL:
        logger.warning("[Slack] SLACK_WEBHOOK_URL non configuré, notification ignorée")
        return False

    icon = ":white_check_mark:" if status == "success" else ":x:"
    color = "#36a64f" if status == "success" else "#ff0000"

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{icon} *FinanceAI — {task_name}*",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Statut:*\n{'Succès' if status == 'success' else 'Erreur'}"},
                            {"type": "mrkdwn", "text": f"*Durée:*\n{duration:.1f}s"},
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Résumé:*\n{summary[:500]}",
                        },
                    },
                ],
            }
        ]
    }

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.SLACK_WEBHOOK_URL,
                json=payload,
                timeout=10.0,
            )

        if response.status_code == 200:
            logger.info(f"[Slack] Notification envoyée : {task_name}")
            return True
        else:
            logger.error(f"[Slack] Erreur {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"[Slack] Exception : {e}")
        return False
