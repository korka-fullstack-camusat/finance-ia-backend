"""Orchestrateur principal — agent IA FinanceAI (100% async)."""
import asyncio
import json
import time
from datetime import datetime
from typing import AsyncGenerator

import anthropic
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task import Task, TaskResult, TaskStatus, TaskType
from app.models.file import UploadedFile
from app.agent.tasks.reporting import run_reporting
from app.agent.tasks.reconciliation import run_reconciliation
from app.agent.tasks.kpi import run_kpi
from app.agent.tasks.forecast import run_forecast
from app.agent.tasks.anomaly import run_anomaly
from app.agent.tasks.audit import run_audit

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

Réponds en français, de manière précise et professionnelle.
Utilise des tableaux markdown quand c'est pertinent.

Contexte des dernières analyses :
{context}
"""


def _get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


async def _load_file_data(db: AsyncSession) -> str:
    """Charge les données du dernier fichier uploadé (async)."""
    import aiofiles
    import pandas as pd

    result = await db.execute(
        select(UploadedFile).order_by(desc(UploadedFile.created_at)).limit(1)
    )
    file_record = result.scalar_one_or_none()

    if not file_record:
        return "Aucun fichier disponible. Uploadez un fichier CSV ou XLSX via le dashboard."

    try:
        if file_record.file_type == "csv":
            df = await asyncio.to_thread(pd.read_csv, file_record.file_path)
            return df.to_string(max_rows=200)
        elif file_record.file_type in ("xlsx", "xls"):
            df = await asyncio.to_thread(pd.read_excel, file_record.file_path)
            return df.to_string(max_rows=200)
        else:
            async with aiofiles.open(file_record.file_path, "r", errors="ignore") as f:
                return (await f.read())[:8000]
    except Exception as e:
        return f"Erreur lecture fichier : {e}"


async def execute_task(
    task: Task, db: AsyncSession, triggered_by: str = "auto"
) -> TaskResult:
    """Exécute une tâche financière via Claude (async)."""
    client = _get_client()
    data = await _load_file_data(db)
    date = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

    runner = TASK_RUNNERS.get(task.task_type)
    if not runner:
        raise ValueError(f"Type de tâche inconnu : {task.task_type}")

    start = time.perf_counter()
    try:
        content = await runner(data=data, date=date, anthropic_client=client)
        duration = round(time.perf_counter() - start, 2)

        summary_lines = [l.strip() for l in content.split("\n") if l.strip()]
        summary = summary_lines[0][:200] if summary_lines else "Analyse complétée"

        result = TaskResult(
            task_id=task.id,
            content=content,
            summary=summary,
            duration=duration,
            triggered_by=triggered_by,
        )
        db.add(result)
        task.status = TaskStatus.SUCCESS
        task.last_run = datetime.utcnow()
        await db.commit()
        await db.refresh(result)
        return result

    except Exception:
        task.status = TaskStatus.ERROR
        task.last_run = datetime.utcnow()
        await db.commit()
        raise


async def stream_chat(
    message: str, db: AsyncSession
) -> AsyncGenerator[str, None]:
    """Stream la réponse du chat token par token (async SSE)."""
    client = _get_client()

    result = await db.execute(
        select(TaskResult).order_by(desc(TaskResult.created_at)).limit(3)
    )
    recent = result.scalars().all()
    context_parts = [
        f"### Analyse du {r.created_at.strftime('%d/%m/%Y')}\n{r.summary}"
        for r in recent
    ]
    context = "\n\n".join(context_parts) if context_parts else "Aucune analyse récente."

    system = CHAT_SYSTEM_PROMPT.format(context=context)

    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": message}],
    ) as stream:
        async for token in stream.text_stream:
            yield token


async def stream_task_execution(
    task: Task, db: AsyncSession
) -> AsyncGenerator[str, None]:
    """Stream les logs d'exécution d'une tâche en temps réel (SSE)."""

    def _evt(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    yield _evt({"type": "log", "message": f"Démarrage : {task.name}"})
    yield _evt({"type": "log", "message": "Chargement des données financières..."})

    client = _get_client()
    data = await _load_file_data(db)
    date = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

    yield _evt({"type": "log", "message": "Données chargées. Analyse Claude en cours..."})
    yield _evt({"type": "progress", "value": 30})

    runner = TASK_RUNNERS.get(task.task_type)
    if not runner:
        yield _evt({"type": "error", "message": "Type de tâche inconnu"})
        return

    task.status = TaskStatus.RUNNING
    await db.commit()

    start = time.perf_counter()
    try:
        yield _evt({"type": "progress", "value": 60})
        content = await runner(data=data, date=date, anthropic_client=client)
        duration = round(time.perf_counter() - start, 2)

        summary_lines = [l.strip() for l in content.split("\n") if l.strip()]
        summary = summary_lines[0][:200] if summary_lines else "Analyse complétée"

        result = TaskResult(
            task_id=task.id,
            content=content,
            summary=summary,
            duration=duration,
            triggered_by="manual",
        )
        db.add(result)
        task.status = TaskStatus.SUCCESS
        task.last_run = datetime.utcnow()
        await db.commit()
        await db.refresh(result)

        yield _evt({"type": "progress", "value": 100})
        yield _evt({"type": "log", "message": f"Terminé en {duration}s"})
        yield _evt({"type": "result", "result_id": result.id, "summary": summary})
        yield _evt({"type": "done"})

    except Exception as e:
        task.status = TaskStatus.ERROR
        task.last_run = datetime.utcnow()
        await db.commit()
        yield _evt({"type": "error", "message": str(e)[:300]})
