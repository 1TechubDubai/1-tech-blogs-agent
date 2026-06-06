import logging
from app.agent.services.llm_fallback import generate_with_fallback
from app.agent.services.vector_store import get_vector_store

logger = logging.getLogger("seo_agent.services.gemini")


async def generate_article_draft(keyword: str, serp_context: dict, profile: dict) -> dict:
    """
    Generates SEO-optimized blog articles with advanced deduplication and differentiation.
    
    Features:
    - Checks vector similarity against existing blogs
    - Uses SERP gap analysis for unique angles
    - Generates distinctive content that stands out
    - Multi-model fallback with high-quality fallback template
    - Uses competitor analysis to create better content
    
    Args:
        keyword: Target keyword for the article
        serp_context: SERP analysis results with content gaps and angles
        profile: User profile with tone preferences
    
    Returns:
        Dict with title, excerpt, content, tags, category
    """
    
    tone = profile.get("preferred_tone", "professional")
    exclusion_list = ", ".join(profile.get("exclusion_policies", []))
    
    vector_store = get_vector_store()
    
    # Step 1: Check if similar blogs already exist
    similar_blogs = vector_store.find_similar_blogs(keyword, threshold=0.75, top_k=3)
    
    if similar_blogs:
        logger.info(f"⚠️  Similar blogs found for '{keyword}': {[b['title'] for b in similar_blogs]}")
        # Adjust prompt to be more unique
        differentiation_prompt = """
        IMPORTANT: The following similar blogs already exist. YOU MUST create something DISTINCTLY DIFFERENT:
        """ + "\n".join([f"- {b['title']}" for b in similar_blogs]) + "\n\n"
    else:
        differentiation_prompt = ""
    
    # Step 2: Extract content gaps and angles from SERP
    content_angles = serp_context.get("content_angles", ["Comprehensive Guide"])
    gap_opportunities = serp_context.get("gap_opportunities", ["Best Practices"])
    search_intent = serp_context.get("intent", "Informational")
    difficulty = serp_context.get("estimated_difficulty", 0.5)
    
    # Step 3: Build advanced generation prompt
    prompt = f"""
    You are an award-winning SEO Content Strategist and Technical Writer.
    Your task is to create EXCEPTIONALLY UNIQUE, high-value content for: "{keyword}"
    
    {differentiation_prompt}
    
    SERP Analysis Context:
    - Search Intent: {search_intent}
    - Content Competition: {difficulty * 100:.0f}% (0=low, 100=high)
    - Unexplored Content Angles: {', '.join(content_angles)}
    - Market Gaps to Exploit: {', '.join(gap_opportunities)}
    
    Requirements:
    1. Choose ONE of the unexplored angles above to differentiate
    2. Include insights from the market gaps
    3. Provide unique perspective (not generic)
    4. Deep, actionable content (not surface-level)
    5. Include real examples and case studies
    6. Tone: {tone}
    7. Exclude policies: {exclusion_list if exclusion_list else 'None'}
    
    Format response as RAW JSON object (NO markdown blocks):
    {{
        "title": "Highly unique, specific title incorporating the unique angle",
        "excerpt": "2 sentences meta description that stands out from competitors",
        "category": "Tech or AI or Marketing or Enterprise or Developer",
        "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
        "content_angle": "The specific unique angle you're using",
        "content": "<p>Write comprehensive, valuable content using HTML tags. Include real examples, code if relevant, and deep insights. Minimum 2000 words of value.</p>"
    }}
    
    The content MUST be:
    - Original and unique (not generic repeats of SERP results)
    - Deep and comprehensive
    - Highly specific to the niche
    - Include actionable takeaways
    - Better than competitors
    """
    
    # Step 4: Define sophisticated fallback
    fallback_draft = {
        "title": f"The Ultimate Guide to {keyword}: Strategies, Tools & Best Practices",
        "excerpt": f"Discover cutting-edge strategies for {keyword}. Expert insights, practical implementation guides, and proven methodologies.",
        "category": "Tech",
        "tags": [keyword, "Guide", "Strategy", "Best Practices", "Tutorial"],
        "content_angle": "Comprehensive Expert Guide",
        "content": f"""
        <h1>{keyword}: The Complete Resource</h1>
        <p>This comprehensive guide explores {keyword} from multiple angles, providing deep insights and actionable strategies.</p>
        
        <h2>Understanding the Fundamentals</h2>
        <p>Before diving into advanced strategies, let's establish a solid foundation of what {keyword} really means and why it matters.</p>
        
        <h2>Why This Matters Now</h2>
        <p>{keyword} is increasingly critical in modern business environments. Organizations that master these principles gain competitive advantages.</p>
        
        <h2>Implementation Strategy</h2>
        <p>Getting started with {keyword} requires a structured approach:</p>
        <ol>
            <li>Assess your current state</li>
            <li>Define clear objectives</li>
            <li>Choose appropriate tools</li>
            <li>Execute and measure</li>
        </ol>
        
        <h2>Real-World Applications</h2>
        <p>Organizations across industries are successfully applying {keyword}. Learn from these practical case studies.</p>
        
        <h2>Advanced Tactics</h2>
        <p>Once you've mastered the basics, explore these advanced techniques to gain competitive advantage.</p>
        
        <h2>Common Mistakes</h2>
        <p>Avoid these pitfalls that many organizations encounter when implementing {keyword}.</p>
        
        <h2>Future Outlook</h2>
        <p>The landscape of {keyword} continues to evolve. Stay ahead with these emerging trends and predictions.</p>
        
        <h2>Conclusion</h2>
        <p>Mastering {keyword} is a journey, not a destination. Use this guide as a foundation for continuous learning and improvement.</p>
        """,
        "featuredImage": ""
    }
    
    # Step 5: Generate with multi-model fallback
    result = await generate_with_fallback(
        prompt=prompt,
        task_name=f"Advanced Article Generation for '{keyword}'",
        fallback_value=fallback_draft,
        temperature=0.75  # Higher for more unique, creative content
    )
    
    # Step 6: Validate and enhance result
    if not isinstance(result, dict):
        logger.warning(f"Unexpected response format: {type(result)}")
        result = fallback_draft
    
    # Step 7: Ensure required fields
    article = {
        "title": result.get("title", fallback_draft["title"]),
        "excerpt": result.get("excerpt", fallback_draft["excerpt"]),
        "category": result.get("category", "Tech"),
        "tags": result.get("tags", [keyword, "Guide"]),
        "content_angle": result.get("content_angle", "Comprehensive Guide"),
        "content": result.get("content", fallback_draft["content"]),
        "featuredImage": result.get("featuredImage", "")
    }
    
    # Step 8: Add to vector store for future deduplication
    vector_store.add_blog(
        blog_id=keyword.replace(" ", "_"),
        title=article["title"],
        content=article["content"],
        metadata={
            "keyword": keyword,
            "angle": article.get("content_angle"),
            "generated_at": "timestamp"
        }
    )
    
    logger.info(f"✅ Generated unique article with angle: {article.get('content_angle', 'Standard')}")
    
    return article