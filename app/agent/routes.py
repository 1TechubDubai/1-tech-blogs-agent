from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from google.cloud import firestore
from app.agent.pipeline import run_autonomous_seo_loop
from config.firebase_config import get_firestore_db
from app.core.database import get_active_agent_profile
import logging

logger = logging.getLogger("seo_agent.agent.routes")
router = APIRouter(prefix="/agent", tags=["Autonomous Agent Webhooks"])

@router.post("/trigger-loop")
async def trigger_autonomous_loop(background_tasks: BackgroundTasks, db: firestore.Client = Depends(get_firestore_db)):
    """
    Secure endpoint triggered by GCP Cloud Scheduler.
    Executes the heavy agent pipeline as a background task so the webhook responds instantly.
    """
    # 1. Validate that the system is currently armed and has a valid profile
    profile = get_active_agent_profile(db)
    if not profile:
        raise HTTPException(status_code=400, detail="Autonomous mode is disabled or no active profile exists.")
    
    # 2. Push the heavy execution to the background thread
    logger.info(f"Triggering autonomous loop for profile: {profile.get('profile_name')}")
    background_tasks.add_task(run_autonomous_seo_loop, db, profile)
    
    return {"status": "success", "message": "Autonomous SEO loop initiated in the background."}