import logging
import firebase_admin
from firebase_admin import credentials, firestore
from pydantic import json
from config.settings import settings

logger = logging.getLogger("seo_agent.config.firebase")

# We store the app instance globally so we don't try to initialize Firebase twice
_firebase_app = None
_db_client = None

def initialize_firebase():
    """Initializes Firebase using Local File or Production JSON String."""
    if not firebase_admin._apps:
        try:
            # 1. PRODUCTION (RENDER) - Load from JSON String
            if settings.GOOGLE_APPLICATION_CREDENTIALS_JSON:
                logger.info("Initializing Firebase via Production JSON String...")
                cred_dict = json.loads(settings.GOOGLE_APPLICATION_CREDENTIALS_JSON)
                cred = credentials.Certificate(cred_dict)
                
            # 2. LOCAL DEV - Load from JSON File
            elif settings.GOOGLE_APPLICATION_CREDENTIALS:
                logger.info(f"Initializing Firebase via Local File: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
                cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
                
            # 3. FALLBACK
            else:
                logger.info("Initializing Firebase via Application Default Credentials...")
                cred = credentials.ApplicationDefault()

            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase successfully initialized.")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firebase: {str(e)}")
            raise e

def get_firestore_db():
    """
    FastAPI Dependency that yields the Firestore client.
    Usage in routes: async def my_route(db: firestore.Client = Depends(get_firestore_db)):
    """
    global _db_client
    
    # Failsafe initialization check
    if _db_client is None:
        initialize_firebase()
        
    try:
        yield _db_client
    finally:
        # We don't close the client here because Firestore handles its own 
        # background gRPC connection pooling optimally.
        pass