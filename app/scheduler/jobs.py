"""APScheduler — exécution automatique des tâches financières."""
import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal
from app.models.task import Task, TaskType, TaskStatus, TaskFrequency
from app.models.notification import Notification
from app.agent.orchestrator import execute_task
from app.notifications.email import send_email_notification
from app.notifications.slack import send_slack_notification

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _run_auto_tasks(frequency: TaskFrequency):
    """Lance toutes les tâches AUTO d'une fréquence donnée."""
    from sqlalchemy import select

    db = SessionLocal()
    try:
        tasks = db.execute(
            select(Task).where(
                Task.is_auto == True,
                Task.frequency == frequency,
                Task.status != TaskStatus.RUNNING,
            )
        ).scalars().all()

        logger.info(f"[Scheduler] {len(tasks)} tâche(s) AUTO {frequency}")

        for task in tasks:
            try:
                logger.info(f"[Scheduler] Lancement : {task.name}")
                task.status = TaskStatus.RUNNING
                db.commit()

                result_obj = await execute_task(task, db, triggered_by="auto")

                notif = Notification(
                    task_id=task.id,
                    task_name=task.name,
                    message=f"✅ '{task.name}' exécutée en {result_obj.duration}s. {result_obj.summary}",
                    channel="system",
                )
                db.add(notif)
                db.commit()

                subject = f"[FinanceAI] {task.name} — Exécution automatique"
                body = (
                    f"Tâche : {task.name}\nFréquence : {frequency}\n"
                    f"Durée : {result_obj.duration}s\n"
                    f"Date : {datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')}\n\n"
                    f"Résumé :\n{result_obj.summary}"
                )
                await asyncio.gather(
                    send_email_notification(subject=subject, body=body),
                    send_slack_notification(task_name=task.name, summary=result_obj.summary, duration=result_obj.duration),
                    return_exceptions=True,
                )

            except Exception as e:
                logger.error(f"[Scheduler] Erreur {task.name} : {e}")
                db.add(Notification(
                    task_id=task.id,
                    task_name=task.name,
                    message=f"❌ Erreur '{task.name}' : {str(e)[:200]}",
                    channel="system",
                ))
                db.commit()
    finally:
        db.close()


async def run_daily_tasks():
    await _run_auto_tasks(TaskFrequency.DAILY)


async def run_weekly_tasks():
    await _run_auto_tasks(TaskFrequency.WEEKLY)


async def run_monthly_tasks():
    await _run_auto_tasks(TaskFrequency.MONTHLY)


def _seed_default_tasks():
    """Crée les 6 tâches par défaut si absentes."""
    from sqlalchemy import select

    defaults = [
        ("Rapport Financier", "Bilan et P&L automatiques", TaskType.REPORTING, TaskFrequency.MONTHLY),
        ("Rapprochement Bancaire", "Rapprochement écritures comptables/bancaires", TaskType.RECONCILIATION, TaskFrequency.DAILY),
        ("Calcul des KPIs", "DSO, DPO, liquidité, marges", TaskType.KPI, TaskFrequency.WEEKLY),
        ("Prévisions Trésorerie", "Prévisions 6 mois avec scénarios", TaskType.FORECAST, TaskFrequency.MONTHLY),
        ("Détection d'Anomalies", "Fraudes, doublons, transactions suspectes", TaskType.ANOMALY, TaskFrequency.DAILY),
        ("Rapport d'Audit", "Conformité comptable et réglementaire", TaskType.AUDIT, TaskFrequency.MONTHLY),
    ]

    db = SessionLocal()
    try:
        for name, desc, task_type, freq in defaults:
            if not db.execute(select(Task).where(Task.task_type == task_type)).scalar_one_or_none():
                db.add(Task(name=name, description=desc, task_type=task_type, frequency=freq))
        db.commit()
        logger.info("[Scheduler] Tâches par défaut initialisées")
    finally:
        db.close()


def start_scheduler():
    _seed_default_tasks()
    scheduler.add_job(run_daily_tasks, CronTrigger(hour=6, minute=0), id="daily", replace_existing=True)
    scheduler.add_job(run_weekly_tasks, CronTrigger(day_of_week="mon", hour=7, minute=0), id="weekly", replace_existing=True)
    scheduler.add_job(run_monthly_tasks, CronTrigger(day=1, hour=6, minute=0), id="monthly", replace_existing=True)
    scheduler.start()
    logger.info("[Scheduler] Démarré (daily 06h / weekly lun 07h / monthly 1er 06h)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[Scheduler] Arrêté")
