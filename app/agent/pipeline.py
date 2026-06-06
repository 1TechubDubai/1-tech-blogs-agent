import logging
from google.cloud import firestore
from app.agent.services.google_trends import get_rising_trends
from app.agent.services.keyword_metrics import get_keyword_metrics
from app.agent.services.search_serp import analyze_serp_layout
from app.agent.services.gemini_ai import generate_article_draft
from app.agent.services.vector_store import get_vector_store
from app.agent.logic.scoring import calculate_opportunity_score, calculate_content_quality_score
from app.core.database import create_blog_document, log_ai_provenance, update_system_last_run, is_weekly_quota_met

logger = logging.getLogger("seo_agent.agent.pipeline")

async def run_autonomous_seo_loop(db: firestore.Client, profile: dict):
    """Advanced master orchestrator with Agentic Retry Logic."""
    try:
        vector_store = get_vector_store()
        target_industries = profile.get("target_industries", [])
        
        logger.info("🎯 Starting Advanced Agentic SEO Pipeline...")

        if is_weekly_quota_met(db, profile):
            logger.info("🛑 Weekly publishing quota met. Agent is resting until the next window.")
            return # Exit early! Do not hit Gemini or SerpAPI.
        
        # --- AGENTIC LOOP SETTINGS ---
        max_attempts = 3
        current_attempt = 1
        best_candidate = None
        rejected_trends = [] # Agent memory to avoid repeating mistakes
        
        while current_attempt <= max_attempts and not best_candidate:
            logger.info(f"\n🔄 --- DISCOVERY ATTEMPT {current_attempt}/{max_attempts} ---")
            
            # Pass rejected trends to Gemini so it learns from its failures
            raw_trends = await get_rising_trends(
                industries=target_industries, 
                exclude_recent_topics=True,
                rejected_trends=rejected_trends 
            )
            
            if not raw_trends:
                logger.warning("No trends generated on this attempt.")
                current_attempt += 1
                continue
                
            candidates = []
            
            for trend in raw_trends[:5]:
                logger.info(f"📊 Evaluating: '{trend}'")
                metrics = await get_keyword_metrics(trend)
                if not metrics:
                    continue
                
                similar_keywords = vector_store.find_similar_keywords(trend, threshold=0.75, top_k=2)
                recently_covered = len(similar_keywords) > 0
                
                # Uniqueness is 1.0 if NOT covered recently, 0.0 if covered
                uniqueness_score = 0.0 if recently_covered else 1.0
                
                score = calculate_opportunity_score(
                    search_volume=metrics['volume'],
                    competition_index=metrics['competition'],
                    cpc=metrics['cpc'],
                    admin_risk_tolerance=profile.get("approval_threshold_risk", "medium"),
                    uniqueness_score=uniqueness_score,
                    content_difficulty=0.5,
                    recently_covered=recently_covered
                )
                
                logger.info(f"   Score: {score:.1f} | Vol: {metrics['volume']} | Comp: {metrics['competition']:.2f} | Unique: {uniqueness_score}")
                
                if score >= 40:
                    candidates.append({
                        "keyword": trend,
                        "metrics": metrics,
                        "score": score,
                        "uniqueness": uniqueness_score,
                        "recently_covered": recently_covered
                    })
                else:
                    # Commit failure to agent short-term memory
                    rejected_trends.append(trend)
            
            if candidates:
                # We found winners! Pick the best one and break the loop.
                best_candidate = max(candidates, key=lambda x: x["score"])
                logger.info(f"✅ Found viable candidate: {best_candidate['keyword']} (Score: {best_candidate['score']:.1f})")
                break
            else:
                logger.warning(f"❌ Attempt {current_attempt} failed to meet threshold 40. Adapting strategy...")
                current_attempt += 1

        # --- GENERATION PHASE ---
        if not best_candidate:
            logger.error("🛑 Agent exhausted all attempts. No viable keywords found today to maintain quality standards.")
            return

        target_keyword = best_candidate["keyword"]
        highest_score = best_candidate["score"]
        
        # Step 4: Analyze SERP
        logger.info("\n🔍 Analyzing SERP for content gaps...")
        serp_context = await analyze_serp_layout(target_keyword)
        
        # Step 5: Generate
        logger.info("✍️ Generating unique, differentiated content...")
        draft_payload = await generate_article_draft(
            keyword=target_keyword,
            serp_context=serp_context,
            profile=profile
        )
        
        # Step 6: Validate Quality
        content_length = len(draft_payload.get("content", ""))
        title_length = len(draft_payload.get("title", ""))
        quality_score = calculate_content_quality_score(
            title_length=title_length,
            content_length=content_length,
            has_examples=True,
            has_code_samples=False,
            readability_grade=8
        )
        
        # Step 7: Publishing Status
        status = "active"
        if profile.get("approval_threshold_risk") == "high" or \
           draft_payload.get('category') in profile.get("topics_requiring_approval", []):
            status = "pending_approval"
        
        draft_payload["status"] = status
        draft_payload["quality_score"] = quality_score
        
        # Step 8: Save to Storage (Firestore is Synchronous!)
        logger.info("💾 Saving generated blog...")
        blog_id = await create_blog_document(db, draft_payload) 
        
        # Step 9: Provenance
        provenance_data = {
            "seed_keyword": target_keyword,
            "opportunity_score": highest_score,
            "quality_score": quality_score,
            "uniqueness_score": best_candidate['uniqueness'],
            "content_difficulty": serp_context.get("estimated_difficulty", 0.5),
            "content_angle": draft_payload.get("content_angle", "Standard"),
            "model_metadata": "gemini-2.5-flash",
            "source_references": serp_context.get("competitor_urls", []),
            "gap_opportunities": serp_context.get("gap_opportunities", []),
            "recently_covered": best_candidate['recently_covered']
        }
        await log_ai_provenance(db, blog_id, provenance_data) 
        
        # Step 10: Update Vector Store (Long-term memory for future runs)
        logger.info("🧠 Saving successful topic to Vector DB to prevent future duplicates...")
        
        # Save the actual blog content
        vector_store.add_blog(
            blog_id=blog_id,
            title=draft_payload.get("title", ""),
            content=draft_payload.get("content", ""),
            metadata={
                "keyword": target_keyword, 
                "score": highest_score,
                "angle": draft_payload.get("content_angle", "Standard")
            }
        )
        
        # Save the keyword to explicitly block it tomorrow
        vector_store.add_keyword(
            keyword=target_keyword,
            industry=", ".join(target_industries),
            metadata={"source": "published_blog", "blog_id": blog_id}
        )
        
        # Step 11: Heartbeat
        await update_system_last_run(db) 
        
        logger.info(f"\n✅ PIPELINE COMPLETE")
        logger.info(f"   Blog ID: {blog_id}")
        logger.info(f"   Keyword: {target_keyword}")
        logger.info(f"   Opportunity Score: {highest_score:.2f}")
        logger.info(f"   Quality Score: {quality_score:.2f}")
        logger.info(f"   Status: {status}")

    except Exception as e:
        logger.error(f"❌ Critical failure in autonomous loop: {str(e)}", exc_info=True)