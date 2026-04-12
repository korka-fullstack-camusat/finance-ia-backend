"""Orchestrateur principal de l'agent IA FinanceAI."""
import asyncio
import time
from datetime import datetime
from typing import AsyncGenerator, Optional

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.task import Task, TaskResult, TaskStatus, TaskType
from app.models.file import UploadedFile
from app.agent.tasks.reporting import run_reporting
from app.agent.tasks.reconciliation import run_reconciliation
from app.agent.tasks.kpi import run_kpi
from app.agent.tasks.forecast import run_forecast
from app.agent.tasks.anomaly import run_anomaly
from app.agent.tasks.audit import run_audit

# Map task types to their runner functions
TASK_RUNNERS = {
    TaskType.REPORTING: run_reporting,
    TaskType.RECONCILIATION: run_reconciliation,
    TaskType.KPI: run_kpi,
    TaskType.FORECAST: run_forecast,
    TaskType.ANOMALY: run_anomaly,
    TaskType.AUDIT: run_audit,
}

CHAT_SYSTEM_PROMPT = """Tu es FinanceAI, un assistant financier expert propulsé par Claude.
Tu aides les équipes financières à analyser leurs données, comprendre les résultats d'analyses,
et prendre de meilleures décisions financières.

Tu as accès au contexte des dernières analyses effectuées sur la plateforme.
Réponds en français, de manière précise et professionnelle.
Utilise des tableaux markdown quand c'est pertinent.

Contexte des dernières analyses :
{context}
"""


def _get_anthropic_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


def _load_file_data(db: Session) -> str:
    """Charge les données du dernier fichier uploadé."""
    import os
    import pandas as pd

    file_record = (
        db.query(UploadedFile).order_by(UploadedFile.created_at.desc()).first()
    )
    if not file_record:
        return "Aucun fichier de données disponible. Veuillez uploader un fichier CSV ou XLSX."

    try:
        path = file_record.file_path
        if file_record.file_type == "csv":
            df = pd.read_csv(path)
        elif file_record.file_type in ("xlsx", "xls"):
            df = pd.read_excel(path)
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()[:8000]

        return df.to_string(max_rows=200)
    except Exception as e:
        return f"Erreur lors de la lecture du fichier : {str(e)}"


async def execute_task(task: Task, db: Session, triggered_by: str = "auto") -> TaskResult:
    """Exécute une tâche financière via l'agent IA."""
    client = _get_anthropic_client()
    data = _load_file_data(db)
    date = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

    runner = TASK_RUNNERS.get(task.task_type)
    if not runner:
        raise ValueError(f"Type de tâche inconnu : {task.task_type}")

    start = time.time()
    try:
        content = await runner(data=data, date=date, anthropic_client=client)
        duration = time.time() - start

        # Résumé court (première ligne non vide)
        summary_lines = [l.strip() for l in content.split("\n") if l.strip()]
        summary = summary_lines[0][:200] if summary_lines else "Analyse complétée"

        result = TaskResult(
            task_id=task.id,
            content=content,
            summary=summary,
            duration=round(duration, 2),
            triggered_by=triggered_by,
        )
        db.add(result)

        task.status = TaskStatus.SUCCESS
        task.last_run = datetime.utcnow()
        db.commit()
        db.refresh(result)
        return result
    except Exception as e:
        task.status = TaskStatus.ERROR
        task.last_run = datetime.utcnow()
        db.commit()
        raise


async def stream_chat(
    message: str,
    db: Session,
) -> AsyncGenerator[str, None]:
    """Stream une réponse de chat via SSE."""
    client = _get_anthropic_client()

    # Récupère le contexte des 3 dernières analyses
    from app.models.task import TaskResult as TR
    recent_results = (
        db.query(TR).order_by(TR.created_at.desc()).limit(3).all()
    )
    context_parts = []
    for r in recent_results:
        context_parts.append(f"### Analyse du {r.created_at.strftime('%d/%m/%Y')}\n{r.summary}")
    context = "\n\n".join(context_parts) if context_parts else "Aucune analyse récente."

    system = CHAT_SYSTEM_PROMPT.format(context=context)

    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": message}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def stream_task_execution(task: Task, db: Session) -> AsyncGenerator[str, None]:
    """Stream les logs d'exécution d'une tâche en temps réel."""
    yield f"data: {{'type': 'log', 'message': 'Démarrage de la tâche : {task.name}'}}\n\n"
    yield f"data: {{'type': 'log', 'message': 'Chargement des données financières...'}}\n\n"

    client = _get_anthropic_client()
    data = _load_file_data(db)
    date = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

    yield f"data: {{'type': 'log', 'message': 'Données chargées. Analyse en cours avec Claude...'}}\n\n"
    yield f"data: {{'type': 'progress', 'value': 30}}\n\n"

    runner = TASK_RUNNERS.get(task.task_type)
    if not runner:
        yield f"data: {{'type': 'error', 'message': 'Type de tâche inconnu'}}\n\n"
        return

    start = time.time()
    try:
        task.status = TaskStatus.RUNNING
        db.commit()

        yield f"data: {{'type': 'progress', 'value': 60}}\n\n"
        content = await runner(data=data, date=date, anthropic_client=client)
        duration = time.time() - start

        summary_lines = [l.strip() for l in content.split("\n") if l.strip()]
        summary = summary_lines[0][:200] if summary_lines else "Analyse complétée"

        result = TaskResult(
            task_id=task.id,
            content=content,
            summary=summary,
            duration=round(duration, 2),
            triggered_by="manual",
        )
        db.add(result)
        task.status = TaskStatus.SUCCESS
        task.last_run = datetime.utcnow()
        db.commit()
        db.refresh(result)

        yield f"data: {{'type': 'progress', 'value': 100}}\n\n"
        yield f"data: {{'type': 'log', 'message': 'Analyse terminée en {duration:.1f}s'}}\n\n"
        import json
        yield f"data: {{'type': 'result', 'result_id': '{result.id}', 'summary': {json.dumps(summary)}}}\n\n"
        yield "data: {'type': 'done'}\n\n"
    except Exception as e:
        task.status = TaskStatus.ERROR
        task.last_run = datetime.utcnow()
        db.commit()
        yield f"data: {{'type': 'error', 'message': '{str(e)[:200]}'}}\n\n"
