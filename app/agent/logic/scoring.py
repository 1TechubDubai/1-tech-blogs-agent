import logging
import math
from typing import Optional

logger = logging.getLogger("seo_agent.logic.scoring")


def calculate_opportunity_score(
    search_volume: int,
    competition_index: float,
    cpc: float,
    admin_risk_tolerance: str = "medium",
    uniqueness_score: float = 0.5,
    content_difficulty: float = 0.5,
    recently_covered: bool = False
) -> float:
    """
    Advanced opportunity scoring algorithm incorporating multiple factors.
    
    Features:
    - Volume vs Competition balance (80% weight)
    - CPC monetization potential (10% weight)
    - Content uniqueness penalty (5% weight)
    - Difficulty adjustment (5% weight)
    
    Score Range: 0-100
    - 75+: Excellent opportunity (pursue)
    - 50-75: Good opportunity (consider)
    - 25-50: Mediocre opportunity (research)
    - <25: Poor opportunity (skip)
    
    Args:
        search_volume: Monthly search volume (higher is better)
        competition_index: SEO difficulty 0-1 (lower is better)
        cpc: Cost per click in USD (higher indicates monetization potential)
        admin_risk_tolerance: 'low', 'medium', or 'high'
        uniqueness_score: 0-1 (1 = completely unique, 0 = already covered)
        content_difficulty: 0-1 (0.5 = moderate difficulty)
        recently_covered: Has similar content been created recently?
    
    Returns:
        Opportunity score 0-100
    """
    
    # Step 1: Volume Analysis
    if search_volume < 50:
        logger.info(f"Score: Rejecting keyword with volume {search_volume} (too low)")
        return 0.0
    
    # Logarithmic normalization: rewards good volume, diminishes extreme volume
    # 1000 = 50 points, 100,000 = ~80 points, 1M = ~95 points
    normalized_volume = min((math.log10(search_volume) / 6.0) * 100, 100)
    volume_score = normalized_volume  # 0-100
    
    # Step 2: Competition Analysis
    # Lower competition is better
    competition_score = (1.0 - competition_index) * 100  # Invert (0-100)
    
    # Step 3: CPC Value
    # Higher CPC means better monetization potential
    cpc_score = min((cpc * 10), 100)  # 0-100 (assumes CPC rarely >$10)
    
    # Step 4: Uniqueness Bonus
    # Reward unique angles that haven't been covered
    uniqueness_bonus = uniqueness_score * 10  # 0-10 point bonus
    
    # Step 5: Difficulty Adjustment
    # Content that's moderate difficulty is often optimal (not too easy, not impossible)
    optimal_difficulty = 0.5
    difficulty_penalty = abs(content_difficulty - optimal_difficulty) * 10  # 0-5 penalty
    
    # Step 6: Recently Covered Penalty
    recency_penalty = 30 if recently_covered else 0
    
    # Step 7: Calculate weighted composite score
    # Focus on volume vs competition balance, then monetization
    base_score = (
        (volume_score * 0.40) +           # Volume is critical
        (competition_score * 0.40) +      # Competition is critical
        (cpc_score * 0.10) +              # Monetization matters
        uniqueness_bonus +                 # Unique content bonus (0-10)
        (5 - difficulty_penalty)           # Difficulty score (5-0)
    )
    
    final_score = base_score - recency_penalty
    
    # Step 8: Risk Tolerance Adjustment
    if admin_risk_tolerance == "low":
        # Conservative: penalize high competition harder
        if competition_index > 0.7:
            final_score -= 25
        elif competition_index > 0.5:
            final_score -= 10
    elif admin_risk_tolerance == "high":
        # Aggressive: reward challenging opportunities with good volume
        if search_volume > 50000 and competition_index > 0.6:
            final_score += 15
    
    # Step 9: Ensure bounds and return
    final_score = max(min(round(final_score, 2), 100.0), 0.0)
    
    logger.info(
        f"Opportunity Score: {final_score} "
        f"(volume:{normalized_volume:.0f}, comp:{competition_score:.0f}, unique:{uniqueness_score:.0f})"
    )
    
    return final_score


def calculate_content_quality_score(
    title_length: int,
    content_length: int,
    has_examples: bool = False,
    has_code_samples: bool = False,
    has_visuals: bool = False,
    readability_grade: int = 8
) -> float:
    """
    Rates generated content quality on 0-100 scale.
    
    Factors:
    - Title quality (40-70 char optimal)
    - Content depth (2000+ words optimal)
    - Example inclusion
    - Code samples for technical content
    - Readability level
    
    Returns:
        Quality score 0-100
    """
    
    quality_score = 0.0
    
    # Title scoring (20 points possible)
    if 40 <= title_length <= 70:
        quality_score += 20
    elif 30 <= title_length <= 85:
        quality_score += 15
    elif title_length > 0:
        quality_score += 5
    
    # Content depth (50 points possible)
    if content_length >= 3000:
        quality_score += 50
    elif content_length >= 2000:
        quality_score += 40
    elif content_length >= 1000:
        quality_score += 25
    elif content_length >= 500:
        quality_score += 10
    
    # Real examples (15 points)
    if has_examples:
        quality_score += 15
    
    # Code samples (10 points)
    if has_code_samples:
        quality_score += 10
    
    # Visuals/formatting (5 points)
    if has_visuals:
        quality_score += 5
    
    # Readability adjustment
    # Grade 6-8 is optimal (20-points baseline)
    readability_score = 20
    if readability_grade < 6:
        readability_score = 10  # Too simple
    elif readability_grade > 10:
        readability_score = 15  # Too complex
    
    quality_score += readability_score
    
    return min(round(quality_score, 2), 100.0)