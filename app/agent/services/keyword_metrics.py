import httpx
import urllib.parse
import logging
from app.agent.services.llm_fallback import generate_with_fallback
from config.settings import settings

# Updated logger name
logger = logging.getLogger("seo_agent.services.keyword_metrics")


async def _estimate_metrics_with_gemini_fallback(keyword: str) -> dict:
    """Fallback mechanism: Uses Gemini with multi-model chain to estimate SEO metrics if RapidAPI fails."""
    logger.info(f"Triggering Gemini fallback to estimate metrics for '{keyword}'...")
    
    prompt = f"""
    You are an expert SEO analyst. Estimate the keyword metrics for the B2B Tech keyword: "{keyword}".
    
    Return ONLY a raw JSON object matching this exact schema:
    {{
        "volume": <integer representing estimated monthly searches>,
        "competition": <float between 0.0 and 1.0 representing SEO difficulty>,
        "cpc": <float representing estimated cost per click in USD>
    }}
    Do not include markdown code blocks.
    """
    
    fallback_metrics = {"volume": 500, "competition": 0.5, "cpc": 1.50}
    
    result = await generate_with_fallback(
        prompt=prompt,
        task_name=f"Keyword Metrics Estimation for '{keyword}'",
        fallback_value=fallback_metrics,
        temperature=0.3
    )
    
    return result


async def get_keyword_metrics(keyword: str) -> dict:
    """Uses RapidAPI Google Keyword Insight API to get search volumes and competition levels."""
    
    if not settings.RAPIDAPI_KEY:
        logger.warning("RAPIDAPI_KEY missing. Diverting to Gemini Fallback.")
        return await _estimate_metrics_with_gemini_fallback(keyword)

    try:
        # 1. URL encode the keyword to handle spaces (e.g., "Sustainable Living" -> "Sustainable%20Living")
        encoded_keyword = urllib.parse.quote(keyword)
        
        # 2. Construct the Endpoint URL
        url = f"https://google-keyword-insight1.p.rapidapi.com/keysuggest/?keyword={encoded_keyword}&location=US&lang=en"
        
        # 3. Apply RapidAPI Auth Headers
        headers = {
            'x-rapidapi-key': settings.RAPIDAPI_KEY,
            'x-rapidapi-host': "google-keyword-insight1.p.rapidapi.com"
        }

        # 4. Execute Asynchronous Request
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status() # Raise exception for 4xx/5xx errors
            data = response.json()
            
            # 5. Parse the Response
            if data and isinstance(data, list) and len(data) > 0:
                target_data = data[0]
                
                raw_competition = target_data.get("competition", 0.3)
                normalized_comp = float(raw_competition) / 100.0 if float(raw_competition) > 1 else float(raw_competition)
                
                logger.info(f"RapidAPI returned metrics for '{keyword}'")
                return {
                    "volume": int(target_data.get("search_volume", 0)),
                    "competition": normalized_comp,
                    "cpc": float(target_data.get("cpc", 0.0))
                }
            
        logger.warning(f"No metric data returned for '{keyword}'. Diverting to Gemini Fallback.")
        return await _estimate_metrics_with_gemini_fallback(keyword)
        
    except httpx.HTTPStatusError as http_err:
        logger.error(f"RapidAPI HTTP error for '{keyword}': {http_err.response.status_code}")
        # Trigger Fallback on 429 Too Many Requests or 403 Forbidden
        return await _estimate_metrics_with_gemini_fallback(keyword)
        
    except Exception as e:
        logger.error(f"RapidAPI Keyword fetch failed for '{keyword}': {str(e)}")
        return await _estimate_metrics_with_gemini_fallback(keyword)