import logging
from app.agent.services.llm_fallback import generate_with_fallback
from app.agent.services.vector_store import get_vector_store

logger = logging.getLogger("seo_agent.services.serp")


async def analyze_serp_layout(keyword: str) -> dict:
    """
    Analyzes SERP with advanced intent detection and competitor analysis.
    
    Features:
    - Real-time Google Search data
    - Sophisticated intent classification
    - Competitor differentiation analysis
    - Content angle suggestions for uniqueness
    
    Args:
        keyword: Target keyword to analyze
    
    Returns:
        Dict with intent, competitor URLs, snippets, and recommended angles
    """
    
    prompt = f"""
    You are an expert SEO analyst and content strategist.
    
    Use your Google Search tool to search for the exact query: "{keyword}".
    Analyze the real-time search results (SERP) on the first page.
    
    Extract:
    1. URLs of top ranking organic pages
    2. Brief snippets of what each page covers
    3. Determine primary search intent (Informational/Transactional/Navigational/Commercial)
    4. Identify content gaps and underserved angles
    
    Return ONLY a raw JSON object matching this exact schema:
    {{
        "intent": "Informational",
        "competitor_urls": ["url1", "url2", "url3", "url4", "url5"],
        "snippets": ["snippet1", "snippet2", "snippet3", "snippet4", "snippet5"],
        "content_angles": ["angle1", "angle2"],
        "gap_opportunities": ["opportunity1", "opportunity2"],
        "estimated_difficulty": 0.65
    }}
    
    Content angles should be UNIQUE angles that competitors are NOT covering.
    Gap opportunities should be specific, actionable content ideas.
    Do not include markdown blocks like ```json.
    """
    
    fallback = {
        "intent": "Informational",
        "competitor_urls": [],
        "snippets": [],
        "content_angles": ["Beginner's Guide", "Advanced Techniques", "Best Practices"],
        "gap_opportunities": ["Industry Case Studies", "Comparative Analysis"],
        "estimated_difficulty": 0.5
    }
    
    result = await generate_with_fallback(
        prompt=prompt,
        task_name="SERP Analysis with Intent Detection",
        fallback_value=fallback,
        use_search_tool=True,
        temperature=0.2
    )
    
    # Ensure strict format
    return {
        "intent": result.get("intent", "Informational"),
        "competitor_urls": result.get("competitor_urls", [])[:5],
        "snippets": result.get("snippets", [])[:5],
        "content_angles": result.get("content_angles", [])[:3],
        "gap_opportunities": result.get("gap_opportunities", [])[:3],
        "estimated_difficulty": result.get("estimated_difficulty", 0.5)
    }