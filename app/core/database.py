import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from google.cloud import firestore
from config.firebase_config import get_firestore_db  # Imported dependency
from config.settings import settings
from pathlib import Path
import json
import uuid

logger = logging.getLogger("seo_agent.core.database")

# --- FILE STORAGE HELPERS (FOR TESTING MODE) ---

def ensure_test_directories():
    """Create test output directories if they don't exist."""
    if settings.USE_FILE_STORAGE:
        blogs_dir = Path(settings.TEST_STORAGE_PATH) / "blogs"
        provenance_dir = Path(settings.TEST_STORAGE_PATH) / "provenance"
        blogs_dir.mkdir(parents=True, exist_ok=True)
        provenance_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Test directories created at: {settings.TEST_STORAGE_PATH}")


def create_blog_file(blog_data: Dict[str, Any]) -> str:
    """Write blog post to text file instead of Firebase (testing mode)."""
    try:
        ensure_test_directories()
        
        blog_id = str(uuid.uuid4())[:12]  # Generate unique ID
        filename = f"blog_{blog_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(settings.TEST_STORAGE_PATH) / "blogs" / filename
        
        # Add the ID to the data
        blog_data["id"] = blog_id
        
        # Write formatted JSON to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(blog_data, f, indent=2, default=str)
        
        logger.info(f"✅ TEST MODE: Blog saved to file: {filepath}")
        print(f"\n📄 Blog post saved to: {filepath}\n")
        return blog_id
        
    except Exception as e:
        logger.error(f"Failed to write blog file: {str(e)}")
        raise e


def log_provenance_file(blog_id: str, lineage_data: Dict[str, Any]) -> None:
    """Write provenance log to file instead of Firebase (testing mode)."""
    try:
        ensure_test_directories()
        
        provenance_data = {
            "blog_id": blog_id,
            "model_metadata": lineage_data.get("model_metadata", "gemini-1.5-pro"),
            "prompt_chain_snapshots": lineage_data.get("prompt_chain_snapshots", []),
            "extracted_knowledge_sources": lineage_data.get("source_references", []),
            "seed_keyword_origins": lineage_data.get("seed_keyword", ""),
            "calculated_opportunity_score": lineage_data.get("opportunity_score", 0.0),
            "logged_at": datetime.utcnow().isoformat()
        }
        
        filename = f"provenance_{blog_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(settings.TEST_STORAGE_PATH) / "provenance" / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(provenance_data, f, indent=2, default=str)
        
        logger.info(f"✅ TEST MODE: Provenance logged to file: {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to write provenance file: {str(e)}")


def get_test_blogs() -> List[Dict[str, Any]]:
    """Retrieve all test blogs from file storage (testing mode)."""
    if not settings.USE_FILE_STORAGE:
        logger.warning("Not in testing mode. USE_FILE_STORAGE must be True.")
        return []
    
    try:
        blogs_dir = Path(settings.TEST_STORAGE_PATH) / "blogs"
        if not blogs_dir.exists():
            logger.info("No test blogs directory found.")
            return []
        
        blogs = []
        for blog_file in sorted(blogs_dir.glob("*.json"), reverse=True):  # Latest first
            with open(blog_file, 'r', encoding='utf-8') as f:
                blog_data = json.load(f)
                blog_data["file_path"] = str(blog_file)
                blogs.append(blog_data)
        
        logger.info(f"Retrieved {len(blogs)} test blogs from file storage.")
        return blogs
    except Exception as e:
        logger.error(f"Failed to retrieve test blogs: {str(e)}")
        return []


# --- GLOBAL SYSTEM CONFIGURATION AND PROFILES ---

def get_active_agent_profile(db: firestore.Client) -> Optional[Dict[str, Any]]:
    """
    Fetches the active agent profile dynamically configured by the admin.
    First reads the global config, then resolves the matching profile document.
    """
    try:
        # 1. Fetch global system settings
        settings_ref = db.collection("system_settings").document("global_config")
        settings_doc = settings_ref.get()
        
        if not settings_doc.exists:
            logger.warning("Global system settings document does not exist.")
            return None
            
        settings_data = settings_doc.to_dict()
        if not settings_data.get("is_autonomous_mode_enabled"):
            logger.info("Autonomous agent operations are globally disabled by admin.")
            return None
            
        active_profile_id = settings_data.get("active_profile_id")
        if not active_profile_id:
            logger.warning("No active profile ID designated in system settings.")
            return None
            
        # 2. Resolve target profile details
        profile_ref = db.collection("agent_profiles").document(active_profile_id)
        profile_doc = profile_ref.get()
        
        if not profile_doc.exists:
            logger.error(f"Active profile configuration matching ID '{active_profile_id}' not found.")
            return None
            
        return profile_doc.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to fetch active agent configuration profile: {str(e)}")
        return None

from datetime import datetime, timedelta, timezone
from google.cloud import firestore
import logging

logger = logging.getLogger("seo_agent.agent.pipeline")

def is_weekly_quota_met(db: firestore.Client, profile: dict) -> bool:
    """
    Checks if the agent has reached its max_posts_per_week limit.
    """
    max_posts = profile.get("max_posts_per_week", 2) # Default to 2 if missing
    profile_id = profile.get("id")
    
    # Calculate the timestamp for exactly 7 days ago
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    try:
        # Assuming your blogs are saved in a "blogs" collection. 
        # Update "blogs" if create_blog_document() uses a different collection name.
        blogs_ref = db.collection("blogs")
        
        # Query: Get blogs created in the last 7 days by this specific profile
        query = blogs_ref.where("created_at", ">=", seven_days_ago)
        
        # Stream the results and count them
        recent_blogs = list(query.stream())
        
        # Filter in Python if you don't have a composite index set up in Firestore for profile_id + created_at
        # Assuming your create_blog_document saves the profile_id in the blog document
        current_count = len([b for b in recent_blogs if b.to_dict().get("profile_id") == profile_id])
        
        logger.info(f"📊 Weekly Quota Status: {current_count}/{max_posts} posts generated in the last 7 days.")
        
        return current_count >= max_posts
        
    except Exception as e:
        logger.error(f"Failed to check weekly quota: {e}")
        # Fail safe: if we can't check, assume it's NOT met so the pipeline doesn't break permanently,
        # OR return True to be overly safe and stop generation. Returning False to keep it running.
        return False

async def update_system_last_run(db: firestore.Client) -> None:
    """Updates the global system execution heartbeat timestamp."""
    try:
        settings_ref = db.collection("system_settings").document("global_config")
        await settings_ref.set({"last_run_timestamp": datetime.utcnow()}, merge=True)
    except Exception as e:
        logger.error(f"Failed to update execution heartbeat: {str(e)}")


# --- BLOG OPERATIONS (ALIGNED WITH YOUR FIREBASE MODEL) ---

async def create_blog_document(db: firestore.Client, blog_data: Dict[str, Any]) -> str:
    """
    Inserts a newly generated or reviewed article directly into the blogs collection.
    Initializes standard telemetry properties (views, timestamps).
    
    ⚠️ SWITCHABLE MODE: If USE_FILE_STORAGE is True, writes to file instead of Firebase.
    """
    # TESTING MODE: Write to file
    if settings.USE_FILE_STORAGE:
        return create_blog_file(blog_data)
    
    # PRODUCTION MODE: Write to Firebase
    try:
        current_time = datetime.utcnow()
        
        # Enforce exact compatibility with your existing structural layout
        prepared_data = {
            "title": blog_data.get("title", "Untitled Autonomous Article"),
            "content": blog_data.get("content", ""),
            "excerpt": blog_data.get("excerpt", ""),
            "category": blog_data.get("category", "Tech"),
            "tags": blog_data.get("tags", []),
            "featuredImage": blog_data.get("featuredImage", ""),
            "status": blog_data.get("status", "pending_approval"),  # Controlled by governance thresholds
            "authorName": blog_data.get("authorName", "AI Operations Agent"),
            "authorEmail": blog_data.get("authorEmail", "agent@1techub.ai"),
            "authorAvatar": blog_data.get("authorAvatar", ""),
            "views": 0,
            "createdAt": current_time,
            "updatedAt": current_time
        }
        
        doc_ref = db.collection("blogs").document()
        doc_ref.set(prepared_data)
        logger.info(f"Successfully generated new document entry: ID {doc_ref.id} [Status: {prepared_data['status']}]")
        return doc_ref.id
    except Exception as e:
        logger.error(f"Failed to insert generated blog post document: {str(e)}")
        raise e


def get_blog_by_id(db: firestore.Client, blog_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single blog entity record for verification/auditing checks."""
    try:
        doc_ref = db.collection("blogs").document(blog_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return None
    except Exception as e:
        logger.error(f"Error reading blog {blog_id}: {str(e)}")
        return None


# --- AI PROVENANCE TRACKING LAYER ---

async def log_ai_provenance(db: firestore.Client, blog_id: str, lineage_data: Dict[str, Any]) -> None:
    """
    Maintains clean enterprise accountability logs for auditing agent behavior.
    Saves prompt paths, source contexts, and model variants separate from public blog schemas.
    
    ⚠️ SWITCHABLE MODE: If USE_FILE_STORAGE is True, writes to file instead of Firebase.
    """
    # TESTING MODE: Write to file
    if settings.USE_FILE_STORAGE:
        return log_provenance_file(blog_id, lineage_data)
    
    # PRODUCTION MODE: Write to Firebase
    try:
        provenance_data = {
            "blog_id": blog_id,
            "model_metadata": lineage_data.get("model_metadata", "gemini-1.5-pro"),
            "prompt_chain_snapshots": lineage_data.get("prompt_chain_snapshots", []),
            "extracted_knowledge_sources": lineage_data.get("source_references", []),
            "seed_keyword_origins": lineage_data.get("seed_keyword", ""),
            "calculated_opportunity_score": lineage_data.get("opportunity_score", 0.0),
            "logged_at": datetime.utcnow()
        }
        await db.collection("ai_provenance_logs").document(blog_id).set(provenance_data)
        logger.info(f"Stored generation lineage track metrics for document {blog_id}")
    except Exception as e:
        logger.error(f"Failed writing audit trail record: {str(e)}")


# --- DRIFT AND RE-OPTIMIZATION DISCOVERY MATCHING ---

def get_active_blog_urls(db: firestore.Client) -> List[Dict[str, Any]]:
    """
    Queries URLs and titles of currently live blog documents.
    Used by the background monitoring worker to check performance drift via Search Console APIs.
    """
    try:
        blogs_ref = db.collection("blogs")
        query = blogs_ref.where("status", "==", "active")
        active_list = []
        
        for doc in query.stream():
            data = doc.to_dict()
            active_list.append({
                "id": doc.id,
                "title": data.get("title"),
                "category": data.get("category"),
                "status": data.get("status"),
                "updatedAt": data.get("updatedAt")
            })
        return active_list
    except Exception as e:
        logger.error(f"Could not aggregate published list for monitoring scan: {str(e)}")
        return []