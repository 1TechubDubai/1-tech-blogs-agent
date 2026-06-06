import json
import logging
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
from config.settings import settings

logger = logging.getLogger("seo_agent.services.llm_fallback")

# Initialize Gemini Client globally
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Model fallback chain - tries each in order
MODEL_CHAIN = [
    "gemini-3.1-flash-lite", # Fallback 1: Lean but reliable
    "gemini-2.5-flash",      # Primary: Fast, optimized for real-time
    "gemini-2.5-pro",        # Fallback 2: More capable
    "gemini-3.1-pro"         # Fallback 3: Most powerful but slowest
]


def _extract_json_from_response(raw_text: str) -> str:
    """Strips markdown code blocks from LLM response."""
    raw_text = raw_text.strip()
    
    # Remove markdown JSON blocks
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    elif raw_text.startswith("```"):
        raw_text = raw_text[3:]
    
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    
    return raw_text.strip()


async def generate_with_fallback(
    prompt: str,
    schema: Optional[Dict[str, Any]] = None,
    task_name: str = "LLM Generation",
    fallback_value: Optional[Dict[str, Any]] = None,
    use_search_tool: bool = False,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """
    Robust LLM generation with multi-model fallback chain.
    
    Args:
        prompt: The generation prompt
        schema: Expected output schema (for validation)
        task_name: Human-readable task name for logging
        fallback_value: Default value if all models fail
        use_search_tool: Enable Google Search grounding (for SERP analysis)
        temperature: Model temperature (0-1)
    
    Returns:
        Parsed JSON response as dictionary, or fallback_value
    """
    
    if fallback_value is None:
        fallback_value = {}
    
    logger.info(f"Starting {task_name}... (attempting {len(MODEL_CHAIN)} models)")
    
    for attempt, model in enumerate(MODEL_CHAIN, 1):
        try:
            logger.info(f"  [{attempt}/{len(MODEL_CHAIN)}] Trying model: {model}")
            
            # Build config with optional search tool
            config_kwargs = {
                "temperature": temperature,
            }
            
            if use_search_tool:
                config_kwargs["tools"] = [{"google_search": {}}]
            
            config = types.GenerateContentConfig(**config_kwargs)
            
            # Make the async call
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            
            raw_text = response.text
            if not raw_text:
                logger.warning(f"  Model {model} returned empty response")
                continue
            
            # Extract JSON from markdown
            clean_text = _extract_json_from_response(raw_text)
            
            # Parse JSON
            parsed = json.loads(clean_text)
            
            logger.info(f"  ✓ Model {model} succeeded for {task_name}")
            return parsed
            
        except json.JSONDecodeError as je:
            logger.warning(f"  Model {model} returned invalid JSON: {je}")
            continue
        
        except Exception as e:
            logger.warning(f"  Model {model} failed: {type(e).__name__}: {str(e)}")
            continue
    
    # All models failed - return fallback
    logger.error(f"All {len(MODEL_CHAIN)} models failed for {task_name}. Using fallback.")
    return fallback_value


async def generate_text_with_fallback(
    prompt: str,
    task_name: str = "Text Generation",
    fallback_text: str = "",
    temperature: float = 0.7,
) -> str:
    """
    Robust text generation with multi-model fallback chain.
    
    Args:
        prompt: The generation prompt
        task_name: Human-readable task name for logging
        fallback_text: Default text if all models fail
        temperature: Model temperature (0-1)
    
    Returns:
        Generated text string, or fallback_text
    """
    
    logger.info(f"Starting {task_name}... (attempting {len(MODEL_CHAIN)} models)")
    
    for attempt, model in enumerate(MODEL_CHAIN, 1):
        try:
            logger.info(f"  [{attempt}/{len(MODEL_CHAIN)}] Trying model: {model}")
            
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature),
            )
            
            text = response.text
            if not text:
                logger.warning(f"  Model {model} returned empty response")
                continue
            
            logger.info(f"  ✓ Model {model} succeeded for {task_name}")
            return text.strip()
            
        except Exception as e:
            logger.warning(f"  Model {model} failed: {type(e).__name__}: {str(e)}")
            continue
    
    # All models failed - return fallback
    logger.error(f"All {len(MODEL_CHAIN)} models failed for {task_name}. Using fallback.")
    return fallback_text
