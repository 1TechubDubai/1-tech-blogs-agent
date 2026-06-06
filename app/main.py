from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# --- NEW IMPORTS FOR SCHEDULING ---
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from firebase_admin import db

from app.admin.routes import router as admin_router
from config.firebase_config import initialize_firebase, get_firestore_db

# Imports for the scheduled task
from app.core.database import get_active_agent_profile
from app.agent.pipeline import run_autonomous_seo_loop

# Configure basic console logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seo_agent.main")

# --- 1. Define the Background Wrapper Task ---
async def scheduled_seo_task():
    """This function is called by the scheduler. It acts as the internal trigger."""
    logger.info("⏰ APScheduler triggered the SEO task.")
    
    try:
        # Initialize DB directly (Cannot use Depends() outside of HTTP routes)
        db = next(get_firestore_db())
        profile = get_active_agent_profile(db)
        
        if not profile:
            logger.info("Autonomous mode disabled or no active profile. Skipping run.")
            return
            
        logger.info(f"Initiating background loop for profile: {profile.get('profile_name')}")
        
        # Execute the heavy pipeline
        await run_autonomous_seo_loop(db, profile)
        
    except Exception as e:
        logger.error(f"Scheduled task failed: {str(e)}")

# --- 2. Setup the FastAPI Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up the SEO Agent backend...")
    initialize_firebase()
    
    # Initialize and start the scheduler
    logger.info("Starting up APScheduler...")
    scheduler = AsyncIOScheduler()
    
    # Configure your cron schedule here (Currently set to run every day at 2:00 AM)
    scheduler.add_job(
        scheduled_seo_task,
        trigger=CronTrigger(hour=18, minute=52), 
        id="daily_seo_loop",
        name="Daily Autonomous SEO Agent",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler running. Next run scheduled for 2:00 AM.")
    
    yield # The FastAPI app is now running and serving requests
    
    # Shutdown logic (cleanup)
    logger.info("Shutting down APScheduler...")
    scheduler.shutdown()
    logger.info("Shutting down the SEO Agent backend safely.")

# --- 3. Initialize FastAPI ---
app = FastAPI(
    title="Autonomous SEO & Content Operations Engine API",
    description="Backend microservice managing dynamic automated loops and admin configurations.",
    version="1.0.0",
    lifespan=lifespan # Attaching the lifespan manager
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route inclusions
app.include_router(admin_router)
# (Optional) If you kept your webhook route around for manual testing, include it here:
# from app.agent.routes import router as agent_router
# app.include_router(agent_router)

@app.get("/", tags=["Health Check"])
async def root_health_check():
    return {
        "status": "healthy",
        # Note: Be careful with scale-to-zero environments when using internal schedulers
        "environment": "production_scale_to_zero", 
        "service": "SEO Agent Backend Engine"
    }