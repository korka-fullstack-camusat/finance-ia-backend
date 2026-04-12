"""APScheduler jobs pour l'exécution automatique des tâches financières."""
import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from database import SessionLocal
from app.models.task import Task, TaskType, TaskStatus, TaskFrequency
from app.models.notification import Notification
from app.agent.orchestrator import execute_task
from app.notifications.email import send_email_notification
from app.notifications.slack import send_slack_notification

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def _get_auto_tasks(db: Session, frequency: TaskFrequency):
    return db.query(Task).filter(
        Task.is_auto == True,
        Task.frequency == frequency,
        Task.status != TaskStatus.RUNNING,
    ).all()


async def _run_auto_tasks(frequency: TaskFrequency):
    """Lance toutes les tâches AUTO pour une fréquence donnée."""
    db = SessionLocal()
    try:
        tasks = _get_auto_tasks(db, frequency)
        logger.info(f"[Scheduler] {len(tasks)} tâche(s) AUTO {frequency} à lancer")

        for task in tasks:
            try:
                logger.info(f"[Scheduler] Exécution : {task.name}")
                task.status = TaskStatus.RUNNING
                db.commit()

                result = await execute_task(task, db, triggered_by="auto")

                # Notif en base
                notif = Notification(
                    task_id=task.id,
                    task_name=task.name,
                    message=f"Tâche '{task.name}' exécutée avec succès en {result.duration}s. {result.summary}",
                    channel="system",
                )
                db.add(notif)
                db.commit()

                # Notif email + Slack
                subject = f"[FinanceAI] {task.name} - Exécution automatique"
                body = f"""
Tâche : {task.name}
Type : {task.task_type}
Fréquence : {frequency}
Durée : {result.duration}s
Date : {datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')}

Résumé :
{result.summary}

Consultez le dashboard pour le rapport complet.
"""
                await send_email_notification(subject=subject, body=body)
                await send_slack_notification(task_name=task.name, summary=result.summary, duration=result.duration)

            except Exception as e:
                logger.error(f"[Scheduler] Erreur tâche {task.name}: {e}")
                notif = Notification(
                    task_id=task.id,
                    task_name=task.name,
                    message=f"Erreur lors de l'exécution de '{task.name}' : {str(e)[:200]}",
                    channel="system",
                )
                db.add(notif)
                db.commit()
    finally:
        db.close()


async def run_daily_tasks():
    await _run_auto_tasks(TaskFrequency.DAILY)


async def run_weekly_tasks():
    await _run_auto_tasks(TaskFrequency.WEEKLY)


async def run_monthly_tasks():
    await _run_auto_tasks(TaskFrequency.MONTHLY)


def _seed_default_tasks(db: Session):
    """Crée les 6 tâches par défaut si elles n'existent pas."""
    default_tasks = [
        {
            "name": "Rapport Financier",
            "description": "Génération automatique du bilan et du compte de résultat (P&L)",
            "task_type": TaskType.REPORTING,
            "frequency": TaskFrequency.MONTHLY,
        },
        {
            "name": "Rapprochement Bancaire",
            "description": "Rapprochement automatique des écritures comptables et bancaires",
            "task_type": TaskType.RECONCILIATION,
            "frequency": TaskFrequency.DAILY,
        },
        {
            "name": "Calcul des KPIs",
            "description": "Calcul DSO, DPO, liquidité, marges et indicateurs de performance",
            "task_type": TaskType.KPI,
            "frequency": TaskFrequency.WEEKLY,
        },
        {
            "name": "Prévisions Trésorerie",
            "description": "Prévisions de trésorerie sur 6 mois avec scénarios",
            "task_type": TaskType.FORECAST,
            "frequency": TaskFrequency.MONTHLY,
        },
        {
            "name": "Détection d'Anomalies",
            "description": "Détection de fraudes, doublons et transactions suspectes",
            "task_type": TaskType.ANOMALY,
            "frequency": TaskFrequency.DAILY,
        },
        {
            "name": "Rapport d'Audit",
            "description": "Rapport de conformité comptable, fiscale et réglementaire",
            "task_type": TaskType.AUDIT,
            "frequency": TaskFrequency.MONTHLY,
        },
    ]
    for t in default_tasks:
        existing = db.query(Task).filter(Task.task_type == t["task_type"]).first()
        if not existing:
            task = Task(**t)
            db.add(task)
    db.commit()


def start_scheduler(db: Session):
    """Initialise et démarre le scheduler APScheduler."""
    _seed_default_tasks(db)

    # Quotidien : 06:00 chaque jour
    scheduler.add_job(
        run_daily_tasks,
        CronTrigger(hour=6, minute=0),
        id="daily_tasks",
        replace_existing=True,
    )

    # Hebdomadaire : lundi 07:00
    scheduler.add_job(
        run_weekly_tasks,
        CronTrigger(day_of_week="mon", hour=7, minute=0),
        id="weekly_tasks",
        replace_existing=True,
    )

    # Mensuel : 1er du mois 06:00
    scheduler.add_job(
        run_monthly_tasks,
        CronTrigger(day=1, hour=6, minute=0),
        id="monthly_tasks",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("[Scheduler] APScheduler démarré (daily/weekly/monthly)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[Scheduler] APScheduler arrêté")
