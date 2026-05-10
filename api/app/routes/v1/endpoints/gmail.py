import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user, get_db_session
from app.services import mail_token_service
from app.models.gmail_sync_job import GmailSyncJob
from app.tasks.gmail_sync import sync_gmail_boarding_passes
from app.schemas.gmail_schema import GmailSyncEnqueueResponse, GmailSyncStatusResponse
from sqlalchemy import select
import logging

router = APIRouter(prefix="/gmail", tags=["Gmail"])
logger = logging.getLogger(__name__)


@router.post("/sync", response_model=GmailSyncEnqueueResponse, summary="Trigger Gmail sync")
async def start_gmail_sync(
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> GmailSyncEnqueueResponse:
    # Verify a Gmail connection exists before creating a job
    connections = await mail_token_service.list_connections(session, user_id)
    if not any(c.provider == "gmail" for c in connections):
        raise HTTPException(
            status_code=400,
            detail="Google account not connected. Please re-authenticate to grant Gmail access.",
        )

    # Create job record
    job = GmailSyncJob(user_id=uuid.UUID(user_id), status="pending")
    session.add(job)
    await session.flush()

    # Enqueue Celery task
    task = sync_gmail_boarding_passes.delay(user_id, str(job.id))
    job.celery_task_id = task.id
    await session.commit()

    logger.info(f"Gmail sync enqueued: job={job.id}, task={task.id}, user={user_id}")
    return GmailSyncEnqueueResponse(job_id=str(job.id), task_id=task.id, status="pending")


@router.get("/sync/status", response_model=GmailSyncStatusResponse, summary="Get latest sync status")
async def get_sync_status(
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> GmailSyncStatusResponse:
    result = await session.execute(
        select(GmailSyncJob)
        .where(GmailSyncJob.user_id == uuid.UUID(user_id))
        .order_by(GmailSyncJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if not job:
        return GmailSyncStatusResponse(status="idle")

    return GmailSyncStatusResponse(
        status=job.status,
        emails_scanned=job.emails_scanned,
        passes_found=job.passes_found,
        passes_saved=job.passes_saved,
        last_synced_at=job.completed_at.isoformat() if job.completed_at else None,
        error=job.error_message,
    )
