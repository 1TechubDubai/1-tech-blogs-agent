import logging
from app.agent.services.llm_fallback import generate_with_fallback
from app.agent.services.vector_store import get_vector_store

logger = logging.getLogger("seo_agent.services.trends")

async def get_rising_trends(industries: list, exclude_recent_topics: bool = True, rejected_trends: list = None) -> list:
    """
    Generates high-quality, emerging keywords using advanced strategy and Agentic Feedback.
    """
    
    if not industries:
        industries = ["Artificial Intelligence", "SaaS", "Cloud Computing"]
    
    vector_store = get_vector_store()
    industry_str = ", ".join(industries)
    
    # Step 1A: Get recently used keywords to filter (Long-Term Memory)
    recently_used = []
    exclusion_prompt = ""
    if exclude_recent_topics:
        for industry in industries:
            similar = vector_store.find_similar_keywords(industry, threshold=0.5, top_k=10)
            recently_used.extend([k["keyword"] for k in similar])
        
        if recently_used:
            excl_str = "\n- ".join(recently_used[:15])
            exclusion_prompt = f"HISTORICAL EXCLUSIONS (Already covered recently. DO NOT REPEAT):\n- {excl_str}\n\n"
            
    # Step 1B: Process real-time rejections from the Agentic Loop (Short-Term Memory)
    rejection_prompt = ""
    if rejected_trends:
        rej_str = "\n- ".join(rejected_trends)
        rejection_prompt = f"""
        CRITICAL FEEDBACK FROM PREVIOUS FAILED ATTEMPTS JUST NOW:
        The following keywords were REJECTED because they were either too competitive or lacked search volume:
        - {rej_str}
        
        YOU MUST PIVOT YOUR STRATEGY. Do not suggest anything semantically similar to the rejected list. 
        Look for much more obscure, highly specific, long-tail, or alternative angles.
        \n\n"""
    
    # Step 2: Generate diverse keyword angles
    prompt = f"""
    You are an advanced SEO and content strategy expert.
    
    Focus Industries: {industry_str}
    
    {exclusion_prompt}
    {rejection_prompt}
    
    Generate 7 HIGHLY SPECIFIC, DIVERSE long-tail keywords using these angles:
    
    1. PROBLEM-SOLVING: Keywords where users search for solutions
    2. COMPARISON: "X vs Y" style comparisons
    3. HOW-TO: Implementation and tutorial angles
    4. TRENDS: Emerging technologies/methodologies
    5. USE-CASES: Specific industry applications
    6. PAIN-POINTS: Challenges in the industry
    7. FUTURE: Predictions and market evolution
    
    Requirements:
    - Each keyword must be 2-5 words (long-tail)
    - Must be relevant to {industry_str}
    - Must be actionable and search-intent rich
    - Avoid semantically similar keywords
    - Focus on underserved niches with good search volume
    - Include some controversial or debate-worthy angles
    
    Return ONLY a JSON array. Example: ["AI model evaluation methods", "vector database cost comparison", "prompt injection prevention techniques"]
    """
    
    fallback_trends = [
        "AI model evaluation frameworks",
        "LLM cost optimization strategies", 
        "Vector database architecture patterns",
        "Prompt engineering best practices",
        "Semantic search implementation guide"
    ]
    
    result = await generate_with_fallback(
        prompt=prompt,
        task_name="Advanced Trend Generation",
        fallback_value=fallback_trends,
        temperature=0.85  # Higher for more creativity
    )
    
    # Step 3: Validate and filter results
    if not isinstance(result, list):
        logger.warning(f"Unexpected response format: {type(result)}")
        return fallback_trends
    
    # Step 4: De-duplicate against vector store
    unique_trends = []
    for trend in result:
        if not isinstance(trend, str):
            continue
        
        # Check similarity with existing keywords
        similar_keywords = vector_store.find_similar_keywords(trend, threshold=0.75, top_k=3)
        
        if similar_keywords:
            logger.info(f"Skipped duplicate trend: '{trend}' (similar to: {similar_keywords[0]['keyword']})")
            continue
        
        unique_trends.append(trend)
    
    # Step 5: Ensure minimum results
    final_trends = unique_trends[:5] if unique_trends else fallback_trends
    
    logger.info(f"✅ Generated {len(final_trends)} unique trends (filtered from {len(result)} candidates)")
    return final_trends