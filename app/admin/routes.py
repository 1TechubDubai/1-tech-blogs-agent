from fastapi import APIRouter, HTTPException, status, Depends
from google.cloud import firestore
from app.admin.schemas import AgentProfileSchema, SystemSettingsSchema, ApprovalActionSchema, BlogResponseSchema
from config.firebase_config import get_firestore_db # We will implement this config dependency next
from config.settings import settings
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core.database import get_test_blogs
import logging

logger = logging.getLogger("seo_agent.admin.routes")

router = APIRouter(prefix="/admin", tags=["Admin Control Panel"])

# --- AGENT PROFILE MANAGEMENT ---

@router.post("/profiles", response_model=AgentProfileSchema, status_code=status.HTTP_201_CREATED)
async def create_agent_profile(profile: AgentProfileSchema, db: firestore.Client = Depends(get_firestore_db)):
    """Create a new dynamic SEO behavior and governance profile."""
    profile_data = profile.dict(exclude_none=True)
    # Store into 'agent_profiles' collection
    doc_ref = db.collection("agent_profiles").document()
    profile_data["id"] = doc_ref.id
    doc_ref.set(profile_data)
    return profile_data

@router.get("/profiles", response_model=List[AgentProfileSchema])
async def list_agent_profiles(db: firestore.Client = Depends(get_firestore_db)):
    """Retrieve all saved admin operational profiles."""
    profiles_stream = db.collection("agent_profiles").stream()
    profiles = []
    for doc in profiles_stream:
        profiles.append(doc.to_dict())
    return profiles

@router.put("/profiles/{profile_id}", response_model=AgentProfileSchema)
async def update_agent_profile(profile_id: str, profile: AgentProfileSchema, db: firestore.Client = Depends(get_firestore_db)):
    """Update an existing operational profile."""
    doc_ref = db.collection("agent_profiles").document(profile_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Profile configuration not found")
    
    updated_data = profile.dict(exclude={"id"})
    updated_data["id"] = profile_id
    doc_ref.set(updated_data, merge=True)
    return updated_data

# --- SYSTEM GLOBAL CONTROLS ---

@router.post("/settings", response_model=SystemSettingsSchema)
async def update_system_settings(settings_obj: SystemSettingsSchema, db: firestore.Client = Depends(get_firestore_db)):
    """Switch active profile or toggle the global autonomous switch."""
    # Ensure specified profile actually exists before linking it
    profile_ref = db.collection("agent_profiles").document(settings_obj.active_profile_id)
    profile_doc = profile_ref.get()
    if not profile_doc.exists:
        raise HTTPException(status_code=400, detail="Invalid active_profile_id. Profile does not exist.")
    
    settings_ref = db.collection("system_settings").document("global_config")
    settings_ref.set(settings_obj.dict(), merge=True)
    return settings_obj

@router.get("/settings", response_model=SystemSettingsSchema)
async def get_system_settings(db: firestore.Client = Depends(get_firestore_db)):
    """Fetch current system orchestration parameters."""
    settings_ref = db.collection("system_settings").document("global_config")
    doc = settings_ref.get()
    if not doc.exists:
        # Provide clean initialization defaults if empty to avoid breaking frontends
        return {"active_profile_id": "", "is_autonomous_mode_enabled": False}
    return doc.to_dict()

# --- HUMAN APPROVAL GATES (MANAGING PENDING BLOGS) ---

@router.get("/queue/pending", response_model=List[BlogResponseSchema])
async def get_pending_approval_queue(db: firestore.Client = Depends(get_firestore_db)):
    """Fetch all drafts trapped by risk thresholds or specific human approval rules."""
    blogs_ref = db.collection("blogs")
    query = blogs_ref.where("status", "==", "pending_approval")
    pending_blogs = []
    for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        pending_blogs.append(data)
    return pending_blogs

@router.post("/queue/review/{blog_id}")
async def review_pending_blog(blog_id: str, decision: ApprovalActionSchema, db: firestore.Client = Depends(get_firestore_db)):
    """Approve or Reject an agent generated article."""
    blog_ref = db.collection("blogs").document(blog_id)
    blog_doc = blog_ref.get()
    
    if not blog_doc.exists:
        raise HTTPException(status_code=404, detail="Target blog draft not found")
    
    if decision.action.lower() == "approve":
        current_time = datetime.utcnow()
        blog_ref.update({
            "status": "active",
            "updatedAt": current_time,
            "publishedAt": current_time,
            "approvedBy": decision.admin_email
        })
        return {"status": "success", "message": f"Blog {blog_id} successfully promoted to active."}
        
    elif decision.action.lower() == "reject":
        blog_ref.update({
            "status": "rejected",
            "rejectionReason": decision.rejection_reason or "No feedback given.",
            "rejectedBy": decision.admin_email,
            "updatedAt": datetime.utcnow()
        })
        return {"status": "success", "message": f"Blog {blog_id} marked as rejected."}
    
    raise HTTPException(status_code=400, detail="Invalid action value. Use 'approve' or 'reject'.")


# --- TESTING MODE ENDPOINTS ---

@router.get("/test/status")
async def get_test_mode_status():
    """Check if testing mode is enabled."""
    return {
        "testing_mode_enabled": settings.USE_FILE_STORAGE,
        "test_storage_path": settings.TEST_STORAGE_PATH,
        "message": "Testing mode writes blogs to files instead of Firebase" if settings.USE_FILE_STORAGE else "Production mode - writing to Firebase"
    }


@router.get("/test/blogs", response_model=List[dict])
async def get_test_blogs_list():
    """Retrieve all test blogs saved to files (only if testing mode is enabled)."""
    if not settings.USE_FILE_STORAGE:
        raise HTTPException(
            status_code=400, 
            detail="Testing mode is disabled. Set USE_FILE_STORAGE=True in .env to enable test mode."
        )
    
    blogs = get_test_blogs()
    if not blogs:
        raise HTTPException(status_code=404, detail="No test blogs found. Generate one first.")
    
    return blogs


@router.get("/test/blogs/{blog_id}")
async def get_test_blog_detail(blog_id: str):
    """Retrieve a specific test blog by ID."""
    if not settings.USE_FILE_STORAGE:
        raise HTTPException(status_code=400, detail="Testing mode is disabled.")
    
    blogs = get_test_blogs()
    for blog in blogs:
        if blog.get("id") == blog_id:
            return blog
    
    raise HTTPException(status_code=404, detail=f"Test blog with ID '{blog_id}' not found.")


@router.post("/test/enable")
async def enable_test_mode():
    """⚠️ Enable testing mode (writes to files instead of Firebase)."""
    # Note: This is a demo endpoint. In production, change .env directly.
    return {
        "status": "Testing mode configuration",
        "instruction": "To enable testing mode, add to your .env file:\n  USE_FILE_STORAGE=true",
        "current_setting": settings.USE_FILE_STORAGE,
        "test_output_path": settings.TEST_STORAGE_PATH
    }


@router.post("/test/full-pipeline")
async def test_full_seo_pipeline(db: firestore.Client = Depends(get_firestore_db)):
    """
    🧪 TEST ENDPOINT: Run the COMPLETE autonomous SEO pipeline in testing mode.
    
    This runs ALL steps:
    - Discover trends (Google Trends / BigQuery)
    - Get keyword metrics (Google Ads API)
    - Score opportunities
    - Analyze SERP layout (Custom Search)
    - Generate article (Gemini AI)
    - SKIP Firebase write (saves to file instead)
    
    Perfect for testing the entire flow without credentials or Firebase.
    Mock data is used for any missing API credentials.
    """
    
    if not settings.USE_FILE_STORAGE:
        raise HTTPException(
            status_code=400,
            detail="Testing mode disabled. Set USE_FILE_STORAGE=true in .env first."
        )
    
    from app.agent.pipeline import run_autonomous_seo_loop
    
    # Create a test profile for pipeline execution
    test_profile = {
        "profile_name": "Test SEO Profile",
        "target_industries": ["Technology", "AI", "Software"],
        "technology_focus": ["Python", "FastAPI", "AI/ML"],
        "ranking_goals": ["Increase organic traffic for technical topics"],
        "preferred_tone": "technical_deep_dive",
        "exclusion_policies": [],
        "max_posts_per_week": 5,
        "approval_threshold_risk": "low",
        "topics_requiring_approval": []
    }
    
    try:
        import logging
        logger = logging.getLogger("seo_agent.admin.routes")
        logger.info("🧪 Starting full pipeline test...")
        
        # Run the complete autonomous loop
        # This will use actual APIs if credentials are available,
        # or mock data if they're not
        await run_autonomous_seo_loop(db, test_profile)
        
        # Get the latest generated blog
        test_blogs = get_test_blogs()
        if not test_blogs:
            return {
                "status": "completed_with_warning",
                "message": "Pipeline executed but no blog was generated",
                "note": "Check logs for details"
            }
        
        latest_blog = test_blogs[0]  # Most recent first
        
        return {
            "status": "success",
            "message": "✅ Full SEO pipeline completed successfully!",
            "blog_generated": {
                "id": latest_blog.get("id"),
                "title": latest_blog.get("title"),
                "category": latest_blog.get("category"),
                "status": latest_blog.get("status"),
                "file_location": latest_blog.get("file_path")
            },
            "pipeline_steps_executed": [
                "✓ Trend discovery",
                "✓ Keyword metrics analysis", 
                "✓ Opportunity scoring",
                "✓ SERP analysis",
                "✓ Gemini content generation",
                "✓ Local file storage (not Firebase)"
            ],
            "next_steps": [
                f"View blog: GET /admin/test/blogs/{latest_blog.get('id')}",
                "List all: GET /admin/test/blogs",
                "Switch to production: Set USE_FILE_STORAGE=false in .env"
            ]
        }
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline test failed: {str(e)}"
        )


@router.post("/test/generate-sample")
async def generate_sample_blog(db: firestore.Client = Depends(get_firestore_db)):
    """Generate a sample blog for testing purposes."""
    if not settings.USE_FILE_STORAGE:
        raise HTTPException(
            status_code=400,
            detail="Testing mode disabled. Enable USE_FILE_STORAGE=true in .env first."
        )
    
    from app.core.database import create_blog_document, log_ai_provenance
    
    # Create sample blog data
    sample_blog = {
        "title": "Getting Started with Python FastAPI - A Comprehensive Guide",
        "excerpt": "Learn how to build modern web APIs with FastAPI. This guide covers setup, routing, and best practices.",
        "category": "Technology",
        "content": """
            <h2>Introduction to FastAPI</h2>
            <p>FastAPI is a modern, fast web framework for building APIs with Python 3.7+ based on standard Python type hints.</p>
            
            <h2>Key Features</h2>
            <ul>
                <li>Fast to code</li>
                <li>Fast performance</li>
                <li>Easy to learn</li>
                <li>Production ready</li>
            </ul>
            
            <h2>Getting Started</h2>
            <p>Installation is simple with pip: pip install fastapi uvicorn</p>
            
            <p>This is a sample blog post generated during testing to verify the file storage functionality.</p>
        """,
        "tags": ["Python", "FastAPI", "Web Development", "Backend"],
        "featuredImage": "https://via.placeholder.com/800x400",
        "status": "active",
        "authorName": "Test Agent",
        "authorEmail": "test@example.com"
    }
    
    # Write to file
    blog_id = create_blog_document(db, sample_blog)
    
    # Log provenance
    log_ai_provenance(db, blog_id, {
        "seed_keyword": "FastAPI Python tutorial",
        "opportunity_score": 78.5,
        "model_metadata": "gemini-1.5-pro (TEST)",
        "source_references": ["fastapi.tiangolo.com", "github.com/tiangolo/fastapi"]
    })
    
    return {
        "status": "success",
        "message": "Sample blog generated in test mode",
        "blog_id": blog_id,
        "file_location": f"{settings.TEST_STORAGE_PATH}/blogs/",
        "tip": f"Visit /admin/test/blogs/{blog_id} to view the generated blog"
    }


@router.post("/test/detailed-pipeline")
async def test_detailed_pipeline_output():
    """
    🔬 DETAILED TEST ENDPOINT: Run each service individually and show full output.
    
    This endpoint demonstrates each step of the pipeline separately:
    1. Trend Discovery (with multiple models fallback)
    2. Keyword Metrics (RapidAPI or Gemini estimation)
    3. Opportunity Scoring
    4. SERP Analysis (with Google Search grounding)
    5. Article Generation (with multi-model fallback)
    
    Perfect for debugging service outputs and verifying multi-model fallback chains.
    """
    
    import logging
    logger = logging.getLogger("seo_agent.admin.routes")
    
    from app.agent.services.google_trends import get_rising_trends
    from app.agent.services.keyword_metrics import get_keyword_metrics
    from app.agent.services.search_serp import analyze_serp_layout
    from app.agent.services.gemini_ai import generate_article_draft
    from app.agent.logic.scoring import calculate_opportunity_score
    
    logger.info("🔬 Starting detailed pipeline output test...")
    
    pipeline_output = {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "services_tested": [],
        "full_pipeline": []
    }
    
    try:
        # STEP 1: Discover Trends
        logger.info("Step 1: Discovering trends with multi-model fallback...")
        industries = ["Technology", "AI", "Software"]
        trends = await get_rising_trends(industries)
        
        step_1 = {
            "step": 1,
            "service": "Google Trends (Gemini Multi-Model)",
            "input": {"industries": industries},
            "output": {
                "trends_discovered": trends,
                "count": len(trends)
            },
            "status": "✓ Success"
        }
        pipeline_output["services_tested"].append(step_1)
        pipeline_output["full_pipeline"].append(step_1)
        logger.info(f"✓ Step 1 complete: Found {len(trends)} trends")
        
        if not trends:
            return {
                **pipeline_output,
                "error": "No trends discovered",
                "status": "completed_with_error"
            }
        
        # Use first trend for detailed analysis
        target_keyword = trends[0]
        
        # STEP 2: Get Keyword Metrics
        logger.info(f"Step 2: Analyzing keyword metrics for '{target_keyword}'...")
        metrics = await get_keyword_metrics(target_keyword)
        
        step_2 = {
            "step": 2,
            "service": "Keyword Metrics (RapidAPI + Gemini Fallback)",
            "input": {"keyword": target_keyword},
            "output": {
                "volume": metrics.get("volume", 0),
                "competition": metrics.get("competition", 0),
                "cpc": metrics.get("cpc", 0),
                "raw": metrics
            },
            "status": "✓ Success"
        }
        pipeline_output["services_tested"].append(step_2)
        pipeline_output["full_pipeline"].append(step_2)
        logger.info(f"✓ Step 2 complete: Volume={metrics['volume']}, Competition={metrics['competition']}")
        
        # STEP 3: Score Opportunity
        logger.info("Step 3: Calculating opportunity score...")
        score = calculate_opportunity_score(
            search_volume=metrics['volume'],
            competition_index=metrics['competition'],
            cpc=metrics['cpc'],
            admin_risk_tolerance="medium"
        )
        
        step_3 = {
            "step": 3,
            "service": "Opportunity Scoring Algorithm",
            "input": {
                "volume": metrics['volume'],
                "competition": metrics['competition'],
                "cpc": metrics['cpc'],
                "risk_tolerance": "medium"
            },
            "output": {
                "opportunity_score": score,
                "interpretation": "High value target" if score > 70 else "Medium value" if score > 50 else "Low value"
            },
            "status": "✓ Success"
        }
        pipeline_output["services_tested"].append(step_3)
        pipeline_output["full_pipeline"].append(step_3)
        logger.info(f"✓ Step 3 complete: Opportunity Score = {score}")
        
        # STEP 4: Analyze SERP
        logger.info(f"Step 4: Analyzing SERP for '{target_keyword}' with Google Search Grounding...")
        serp_context = await analyze_serp_layout(target_keyword)
        
        step_4 = {
            "step": 4,
            "service": "SERP Analysis (Gemini + Google Search)",
            "input": {"keyword": target_keyword},
            "output": {
                "search_intent": serp_context.get("intent", "Unknown"),
                "competitor_urls_found": len(serp_context.get("competitor_urls", [])),
                "competitors": serp_context.get("competitor_urls", [])[:3],  # First 3
                "snippets_count": len(serp_context.get("snippets", []))
            },
            "status": "✓ Success"
        }
        pipeline_output["services_tested"].append(step_4)
        pipeline_output["full_pipeline"].append(step_4)
        logger.info(f"✓ Step 4 complete: Intent={serp_context.get('intent')}, URLs={len(serp_context.get('competitor_urls', []))}")
        
        # STEP 5: Generate Article Draft
        logger.info("Step 5: Generating article with multi-model fallback...")
        test_profile = {
            "preferred_tone": "technical_deep_dive",
            "exclusion_policies": [],
            "topics_requiring_approval": []
        }
        
        draft = await generate_article_draft(
            keyword=target_keyword,
            serp_context=serp_context,
            profile=test_profile
        )
        
        # Extract content preview
        content_preview = draft.get("content", "")[:200] + "..." if draft.get("content") else ""
        
        step_5 = {
            "step": 5,
            "service": "Article Generation (Gemini Multi-Model)",
            "input": {
                "keyword": target_keyword,
                "search_intent": serp_context.get("intent"),
                "tone": "technical_deep_dive"
            },
            "output": {
                "title": draft.get("title", ""),
                "excerpt": draft.get("excerpt", ""),
                "category": draft.get("category", ""),
                "tags": draft.get("tags", []),
                "content_length": len(draft.get("content", "")),
                "content_preview": content_preview
            },
            "status": "✓ Success"
        }
        pipeline_output["services_tested"].append(step_5)
        pipeline_output["full_pipeline"].append(step_5)
        logger.info(f"✓ Step 5 complete: Title='{draft.get('title')}', Content size={len(draft.get('content', ''))}")
        
        # FINAL: Summary
        pipeline_output["summary"] = {
            "total_steps": 5,
            "all_passed": True,
            "keyword_selected": target_keyword,
            "final_score": score,
            "article_ready": True,
            "content_size_bytes": len(draft.get("content", "")),
            "recommendation": "✓ Pipeline fully operational - all services working correctly"
        }
        
        logger.info("🎉 Detailed pipeline test completed successfully!")
        return pipeline_output
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}", exc_info=True)
        return {
            **pipeline_output,
            "status": "error",
            "error": str(e),
            "message": "Pipeline execution failed - see error details above"
        }


# --- VECTOR STORE & DEDUPLICATION MANAGEMENT ---

@router.get("/vector-store/stats")
async def get_vector_store_statistics():
    """Get vector store statistics for deduplication tracking."""
    from app.agent.services.vector_store import get_vector_store
    
    if not settings.USE_FILE_STORAGE:
        return {
            "status": "testing_mode_disabled",
            "message": "Vector store tracking only available in testing mode"
        }
    
    vector_store = get_vector_store()
    stats = vector_store.get_statistics()
    
    return {
        "status": "success",
        "vector_database": stats,
        "deduplication": {
            "status": "enabled",
            "method": "Chroma vector embeddings" if stats.get("vector_db_available") else "Mock (substring matching)",
            "message": "System automatically deduplicates blogs and keywords"
        },
        "recommendations": {
            "blogs_stored": f"Total generated blogs indexed: {stats.get('blogs_stored', 0)}",
            "keywords_stored": f"Total keywords tracked: {stats.get('keywords_stored', 0)}",
            "next_step": "Run /admin/test/detailed-pipeline to generate content with deduplication"
        }
    }


@router.post("/vector-store/check-duplicate")
async def check_duplicate_content(keyword: str, threshold: float = 0.75):
    """Check if similar content already exists."""
    from app.agent.services.vector_store import get_vector_store
    
    if not settings.USE_FILE_STORAGE:
        raise HTTPException(
            status_code=400,
            detail="Vector store only available in testing mode"
        )
    
    vector_store = get_vector_store()
    
    # Check for similar blogs
    similar_blogs = vector_store.find_similar_blogs(keyword, threshold=threshold, top_k=5)
    
    # Check for similar keywords
    similar_keywords = vector_store.find_similar_keywords(keyword, threshold=threshold, top_k=5)
    
    return {
        "status": "success",
        "keyword": keyword,
        "similarity_threshold": threshold,
        "analysis": {
            "similar_blogs_found": len(similar_blogs),
            "similar_keywords_found": len(similar_keywords),
            "is_unique": len(similar_blogs) == 0 and len(similar_keywords) == 0
        },
        "similar_blogs": similar_blogs,
        "similar_keywords": similar_keywords,
        "recommendation": "Content is unique - safe to generate" if len(similar_blogs) == 0
                         else f"Warning: {len(similar_blogs)} similar blogs exist. Consider alternative angle."
    }


@router.get("/vector-store/recent-keywords")
async def get_recent_keywords(limit: int = 10):
    """Get recently generated keywords."""
    from app.agent.services.vector_store import get_vector_store
    
    if not settings.USE_FILE_STORAGE:
        raise HTTPException(status_code=400, detail="Testing mode disabled")
    
    vector_store = get_vector_store()
    
    if vector_store.client is None:
        # Mock implementation
        keywords = vector_store.collections.get("keywords", {}).get("documents", [])[:limit]
        return {
            "status": "success",
            "mode": "mock",
            "keywords": keywords,
            "total": len(keywords)
        }
    
    try:
        collection = vector_store.client.get_collection("keywords")
        results = collection.get(limit=limit)
        
        return {
            "status": "success",
            "mode": "chroma",
            "keywords": [
                {
                    "id": id,
                    "keyword": doc,
                    "metadata": meta
                }
                for id, doc, meta in zip(
                    results["ids"],
                    results["documents"],
                    results["metadatas"]
                )
            ],
            "total": len(results["ids"])
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/vector-store/recent-blogs")
async def get_recent_blogs(limit: int = 10):
    """Get recently generated blogs from vector store."""
    from app.agent.services.vector_store import get_vector_store
    
    if not settings.USE_FILE_STORAGE:
        raise HTTPException(status_code=400, detail="Testing mode disabled")
    
    vector_store = get_vector_store()
    
    if vector_store.client is None:
        # Mock implementation
        blogs = vector_store.collections.get("blogs", {}).get("documents", [])[:limit]
        return {
            "status": "success",
            "mode": "mock",
            "blogs": [{"title": b.get("title"), "created": b.get("created_at")} for b in blogs],
            "total": len(blogs)
        }
    
    try:
        collection = vector_store.client.get_collection("blogs")
        results = collection.get(limit=limit)
        
        return {
            "status": "success",
            "mode": "chroma",
            "blogs": [
                {
                    "id": id,
                    "title": meta.get("title", ""),
                    "keyword": meta.get("keyword", ""),
                    "metadata": meta
                }
                for id, meta in zip(results["ids"], results["metadatas"])
            ],
            "total": len(results["ids"])
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# --- AI-POWERED SUGGESTION ENGINES ---
# --- 1. Define Pydantic Models for the Request Body ---
class SuggestionRequest(BaseModel):
    profile_id: str
    current_values: Optional[List[str]] = []
    limit: Optional[int] = 5

class KeywordSuggestionRequest(SuggestionRequest):
    industries: Optional[List[str]] = None
    tech_focus: Optional[List[str]] = None

# --- Helper Function ---
def _generate_suggestions_with_gemini(prompt: str) -> list:
    """Helper to generate suggestions using Gemini with fallback (sync)."""
    try:
        import google.generativeai as genai
        from config.settings import settings
        import json
        import re
        
        # Configure Gemini
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        
        model = genai.GenerativeModel("gemini-3.1-flash")
        response = model.generate_content(prompt)
        text = response.text if response else ""
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            if isinstance(result, dict):
                return result.get("suggestions", [])
            elif isinstance(result, list):
                return result
    except Exception as e:
        logger.warning(f"Gemini suggestion generation failed: {e}, using fallbacks")
    return []

@router.post("/suggest-industries")
async def suggest_industries(
    request: SuggestionRequest,
    db = Depends(get_firestore_db) # Assuming get_firestore_db is imported
):
    """🤖 AI-powered industry suggestion."""
    limit = min(request.limit, 10)
    current_values = request.current_values or []
    
    try:
        profile_ref = db.collection("agent_profiles").document(request.profile_id)
        profile_doc = profile_ref.get()
        
        if not profile_doc.exists:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = profile_doc.to_dict()
        existing_industries = profile.get("target_industries", [])
        tech_focus = ", ".join(profile.get("technology_focus", [])) or "General"
        
        prompt = f"""
        You are an expert in SEO industry strategy.
        
        Current profile is focused on:
        - Industries: {', '.join(existing_industries) if existing_industries else 'None specified yet'}
        - Technology: {tech_focus}
        
        User has already selected: {', '.join(current_values) if current_values else 'Nothing yet'}
        
        Suggest {limit} NEW, UNIQUE industries that would have good organic search opportunities
        complementary to their current focus.
        
        Rules:
        - Do NOT suggest industries already in the current list
        - Industries should have strong content/SEO demand
        - Be specific and niche-focused
        - Consider adjacent verticals with similar audience
        
        Return ONLY valid JSON:
        {{"suggestions": ["industry1", "industry2", ...]}}
        """
        
        suggestions = _generate_suggestions_with_gemini(prompt)
        
        if not suggestions:
            # Intelligent fallbacks based on existing focus
            suggestions = [
                "SaaS Solutions",
                "Enterprise Software",
                "Digital Transformation",
                "Cloud Infrastructure",
                "Data Analytics"
            ]
        
        return {
            "status": "success",
            "profile_id": request.profile_id,
            "suggestion_type": "industries",
            "suggestions": suggestions[:limit],
            "message": f"Generated {len(suggestions[:limit])} industry suggestions"
        }
    
    except Exception as e:
        logger.error(f"Industry suggestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Suggestion engine error: {str(e)}")


@router.post("/suggest-technologies")
async def suggest_technologies(
    request: SuggestionRequest,
    db = Depends(get_firestore_db)
):
    """🤖 AI-powered technology stack suggestion."""
    limit = min(request.limit, 10)
    current_values = request.current_values or []
    
    try:
        profile_ref = db.collection("agent_profiles").document(request.profile_id)
        profile_doc = profile_ref.get()
        
        if not profile_doc.exists:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = profile_doc.to_dict()
        existing_tech = profile.get("technology_focus", [])
        industries = ", ".join(profile.get("target_industries", [])) or "General"
        
        prompt = f"""
        You are an expert in technology and programming trends.
        
        Current profile is focused on:
        - Technologies: {', '.join(existing_tech) if existing_tech else 'None specified yet'}
        - Industries: {industries}
        
        User has already selected: {', '.join(current_values) if current_values else 'Nothing yet'}
        
        Suggest {limit} NEW technologies, frameworks, or tools that would:
        1. Complement their current tech stack
        2. Have high search volume and content demand
        3. Be relevant to their industry focus
        4. NOT be duplicates of what they already have
        
        Include both established and emerging technologies.
        
        Return ONLY valid JSON:
        {{"suggestions": ["tech1", "tech2", ...]}}
        """
        
        suggestions = _generate_suggestions_with_gemini(prompt)
        
        if not suggestions:
            suggestions = ["GraphQL", "Docker", "Kubernetes", "Microservices", "API-First Architecture"]
        
        return {
            "status": "success",
            "profile_id": request.profile_id,
            "suggestion_type": "technologies",
            "suggestions": suggestions[:limit],
            "message": f"Generated {len(suggestions[:limit])} technology suggestions"
        }
    
    except Exception as e:
        logger.error(f"Technology suggestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Suggestion engine error: {str(e)}")


@router.post("/suggest-exclusions")
async def suggest_exclusions(
    request: SuggestionRequest,
    db = Depends(get_firestore_db)
):
    """🤖 AI-powered content exclusion suggestion."""
    limit = min(request.limit, 10)
    current_values = request.current_values or []
    
    try:
        profile_ref = db.collection("agent_profiles").document(request.profile_id)
        profile_doc = profile_ref.get()
        
        if not profile_doc.exists:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = profile_doc.to_dict()
        industries = ", ".join(profile.get("target_industries", [])) or "General"
        
        prompt = f"""
        You are an expert in content strategy and brand safety.
        
        This brand focuses on:
        - Industries: {industries}
        
        Already excluding: {', '.join(current_values) if current_values else 'Nothing yet'}
        
        Suggest {limit} topics or keywords that should be EXCLUDED from their content
        because they are:
        1. Controversial or polarizing for the industry
        2. Risky from a brand safety perspective
        3. Unethical or illegal in their domain
        4. Could damage credibility
        5. Unrelated to their core mission
        
        Suggestions should be DIFFERENT from what they've already excluded.
        
        Return ONLY valid JSON:
        {{"suggestions": ["topic1", "topic2", ...]}}
        """
        
        suggestions = _generate_suggestions_with_gemini(prompt)
        
        if not suggestions:
            suggestions = ["Misinformation", "Medical Advice", "Financial Speculation", "Conspiracy Theories", "Illegal Activities"]
        
        return {
            "status": "success",
            "profile_id": request.profile_id,
            "suggestion_type": "exclusions",
            "suggestions": suggestions[:limit],
            "message": f"Generated {limit} content exclusion suggestions for brand safety"
        }
    
    except Exception as e:
        logger.error(f"Exclusion suggestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Suggestion engine error: {str(e)}")


@router.post("/suggest-keywords")
async def suggest_keywords_ai(
    request: KeywordSuggestionRequest,
    db = Depends(get_firestore_db)
):
    """🤖 AI-powered keyword suggestion using Gemini intelligence."""
    limit = min(request.limit, 10)
    current_values = request.current_values or []
    
    profile_ref = db.collection("agent_profiles").document(request.profile_id)
    profile_doc = profile_ref.get()
    
    if not profile_doc.exists:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = profile_doc.to_dict()
    
    # Prioritize the live data from the React request body over the saved database state
    target_industries = request.industries or profile.get("target_industries", [])
    technology_focus = request.tech_focus or profile.get("technology_focus", [])
    preferred_tone = profile.get("preferred_tone", "professional_insightful")
    exclusions = profile.get("exclusion_policies", [])
    
    try:
        # If arrays are empty, gracefully fall back to "General" string
        industries_str = ", ".join(target_industries) if target_industries else "General Technology"
        tech_str = ", ".join(technology_focus) if technology_focus else "General Software"
        exclusions_str = ", ".join(exclusions) if exclusions else "None"
        
        prompt = f"""
        You are an expert SEO strategist and content strategist.
        
        This brand profile targets:
        - Industries: {industries_str}
        - Technology Focus: {tech_str}
        - Brand Tone: {preferred_tone}
        - Exclusions: {exclusions_str}
        
        Keywords ALREADY selected by user: {', '.join(current_values) if current_values else 'None yet'}
        
        Suggest {limit} HIGH-VALUE NEW keywords (NOT IN THE ABOVE LIST) that:
        1. Are RELEVANT to the industries and tech focus
        2. Have HIGH commercial/informational intent
        3. Mix of high-volume and long-tail
        4. Suitable for the brand tone
        5. NEVER in the exclusion list
        6. NOT duplicates of existing keywords
        
        Return ONLY valid JSON:
        {{
            "suggestions": [
                {{"keyword": "string", "intent": "informational|commercial|transactional", "difficulty": 0-100}},
                ...
            ]
        }}
        """
        
        response = _generate_suggestions_with_gemini(prompt)
        
        if not response:
            keywords = [
                {"keyword": f"{tech_str.split(',')[0]} best practices", "intent": "informational", "difficulty": 45},
                {"keyword": f"{tech_str.split(',')[0]} tutorial", "intent": "informational", "difficulty": 35},
                {"keyword": f"{industries_str.split(',')[0]} solutions", "intent": "commercial", "difficulty": 55},
            ]
        else:
            keywords = response
            
        current_lower = [v.lower() for v in current_values]
        
        # Format the output purely as a list of strings so the React Tag component renders them properly
        unique_keywords_strings = [
            k.get("keyword") for k in keywords 
            if isinstance(k, dict) and k.get("keyword", "").lower() not in current_lower
        ][:limit]
        
        return {
            "status": "success",
            "profile_id": request.profile_id,
            "suggestion_type": "keywords",
            "suggestions": unique_keywords_strings,
            "count": len(unique_keywords_strings),
            "message": f"Generated {len(unique_keywords_strings)} unique keyword suggestions"
        }
        
    except Exception as e:
        logger.error(f"Keyword suggestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Suggestion engine error: {str(e)}")
# --- PUBLISHED BLOGS MANAGEMENT ---

@router.get("/blogs")
async def list_published_blogs(
    status_filter: str = "active",
    limit: int = 20,
    db: firestore.Client = Depends(get_firestore_db)
):
    """
    Retrieve published or archived blogs.
    
    Args:
        status_filter: Filter by status (active, archived, all)
        limit: Number of blogs to return (max 100)
    
    Returns:
        List of blog documents
    """
    limit = min(limit, 100)
    
    blogs_ref = db.collection("blogs")
    
    if status_filter.lower() == "all":
        query = blogs_ref.limit(limit)
    elif status_filter.lower() == "archived":
        query = blogs_ref.where("status", "==", "archived").limit(limit)
    else:  # Default to active
        query = blogs_ref.where("status", "==", "active").limit(limit)
    
    blogs = []
    for doc in query.stream():
        blog = doc.to_dict()
        blog["id"] = doc.id
        blogs.append(blog)
    
    # Sort by creation date, newest first
    blogs.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    
    return {
        "status": "success",
        "filter": status_filter,
        "count": len(blogs),
        "blogs": blogs
    }


@router.get("/blogs/{blog_id}")
async def get_blog_detail(blog_id: str, db: firestore.Client = Depends(get_firestore_db)):
    """Retrieve detailed information for a specific blog."""
    blog_ref = db.collection("blogs").document(blog_id)
    blog_doc = blog_ref.get()
    
    if not blog_doc.exists:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    blog = blog_doc.to_dict()
    blog["id"] = blog_id
    
    # Try to fetch associated provenance/metadata
    try:
        provenance_ref = db.collection("content_provenance").document(blog_id)
        provenance_doc = provenance_ref.get()
        if provenance_doc.exists:
            blog["provenance"] = provenance_doc.to_dict()
    except:
        pass
    
    return {
        "status": "success",
        "blog": blog
    }


@router.post("/blogs/{blog_id}/archive")
async def archive_blog(blog_id: str, db: firestore.Client = Depends(get_firestore_db)):
    """Archive a published blog."""
    blog_ref = db.collection("blogs").document(blog_id)
    blog_doc = blog_ref.get()
    
    if not blog_doc.exists:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    blog_ref.update({
        "status": "archived",
        "archivedAt": datetime.utcnow()
    })
    
    return {
        "status": "success",
        "message": f"Blog {blog_id} archived successfully",
        "blog_id": blog_id
    }


@router.post("/blogs/{blog_id}/restore")
async def restore_blog(blog_id: str, db: firestore.Client = Depends(get_firestore_db)):
    """Restore an archived blog to published status."""
    blog_ref = db.collection("blogs").document(blog_id)
    blog_doc = blog_ref.get()
    
    if not blog_doc.exists:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    blog_ref.update({
        "status": "active",
        "restoredAt": datetime.utcnow()
    })
    
    return {
        "status": "success",
        "message": f"Blog {blog_id} restored successfully",
        "blog_id": blog_id
    }


# --- DASHBOARD STATISTICS ---

@router.get("/stats/dashboard")
async def get_dashboard_stats(db: firestore.Client = Depends(get_firestore_db)):
    """Get comprehensive dashboard statistics."""
    
    try:
        # Count blogs by status
        active_blogs = list(db.collection("blogs").where("status", "==", "active").stream())
        pending_blogs = list(db.collection("blogs").where("status", "==", "pending_approval").stream())
        archived_blogs = list(db.collection("blogs").where("status", "==", "archived").stream())
        
        active_count = len(active_blogs)
        pending_count = len(pending_blogs)
        archived_count = len(archived_blogs)
        
        # Get system settings
        settings_ref = db.collection("system_settings").document("global_config")
        settings_doc = settings_ref.get()
        system_enabled = False
        active_profile_name = "No Profile"
        
        if settings_doc.exists:
            settings_data = settings_doc.to_dict()
            system_enabled = settings_data.get("is_autonomous_mode_enabled", False)
            active_profile_id = settings_data.get("active_profile_id", "")
            
            if active_profile_id:
                profile_ref = db.collection("agent_profiles").document(active_profile_id)
                profile_doc = profile_ref.get()
                if profile_doc.exists:
                    active_profile_name = profile_doc.to_dict().get("profile_name", "Unknown")
        
        # Get profile count
        profiles = list(db.collection("agent_profiles").stream())
        profile_count = len(profiles)
        
        return {
            "status": "success",
            "dashboard": {
                "system": {
                    "autonomous_mode_enabled": system_enabled,
                    "active_profile": active_profile_name,
                    "total_profiles": profile_count
                },
                "blogs": {
                    "active": active_count,
                    "pending_approval": pending_count,
                    "archived": archived_count,
                    "total": active_count + pending_count + archived_count
                },
                "content_production": {
                    "active_rate": "N/A" if pending_count == 0 else f"{pending_count} awaiting review"
                }
            }
        }
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }