import logging
from typing import Dict, List, Tuple
import re

logger = logging.getLogger("seo_agent.services.data_quality")


class ContentQualityValidator:
    """Validates and scores content quality with detailed recommendations."""
    
    @staticmethod
    def validate_title(title: str) -> Tuple[float, List[str]]:
        """
        Validate title quality (0-100).
        
        Criteria:
        - Length 40-70 characters (optimal)
        - Contains target keyword
        - Engaging/action-oriented language
        - No keyword stuffing
        - Proper capitalization
        """
        issues = []
        score = 0.0
        
        # Length check
        length = len(title)
        if length < 30:
            issues.append("Title too short (< 30 chars)")
        elif length > 85:
            issues.append("Title too long (> 85 chars)")
        elif 40 <= length <= 70:
            score += 30
        elif 30 <= length < 40 or 70 < length <= 85:
            score += 20
        else:
            score += 10
        
        # Action/emotional words
        power_words = ["ultimate", "essential", "proven", "guaranteed", "best", "top", "advanced", 
                      "powerful", "complete", "comprehensive", "expert", "secret", "hidden"]
        if any(word in title.lower() for word in power_words):
            score += 25
        
        # Number presence (often performs better)
        if re.search(r'\d+', title):
            score += 15
        
        # Question format
        if title.endswith('?'):
            score += 10
        
        # Capitalization
        if title[0].isupper():
            score += 10
        
        # Keyword stuffing
        words = title.lower().split()
        if len(words) != len(set(words)):
            issues.append("Possible keyword stuffing detected")
            score -= 10
        
        return min(score, 100.0), issues
    
    @staticmethod
    def validate_content(content: str, min_words: int = 500) -> Tuple[float, List[str]]:
        """
        Validate content quality (0-100).
        
        Criteria:
        - Sufficient length (500+ words minimum)
        - Proper HTML structure
        - Headings (h1, h2, h3)
        - Lists/bullets
        - Paragraphs not too long
        """
        issues = []
        score = 0.0
        
        # Remove HTML tags for word count
        clean_content = re.sub(r'<[^>]+>', '', content)
        word_count = len(clean_content.split())
        
        # Word count validation
        if word_count < min_words:
            issues.append(f"Content too short ({word_count} words, minimum {min_words})")
        elif word_count < 1500:
            score += 30
        elif word_count < 2500:
            score += 50
        elif word_count < 4000:
            score += 60
        else:
            score += 70
        
        # HTML structure
        if '<h1>' in content or '<H1>' in content:
            score += 10
        if '<h2>' in content or '<H2>' in content:
            score += 10
        
        # Variety in formatting
        if '<li>' in content:
            score += 10  # Lists increase engagement
        if '<strong>' in content or '<b>' in content:
            score += 5   # Bold text
        if '<em>' in content or '<i>' in content:
            score += 5   # Italic text
        
        # Paragraph length check
        paragraphs = re.findall(r'<p>(.*?)</p>', content, re.DOTALL)
        if paragraphs:
            avg_p_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
            if avg_p_length > 200:
                issues.append(f"Paragraphs too long (avg {avg_p_length:.0f} words)")
            elif avg_p_length > 100:
                score += 10
        
        return min(score, 100.0), issues
    
    @staticmethod
    def validate_excerpt(excerpt: str) -> Tuple[float, List[str]]:
        """
        Validate meta description/excerpt (0-100).
        
        Criteria:
        - 120-160 characters (optimal for SERPs)
        - Compelling and relevant
        - Clear call to action
        """
        issues = []
        score = 0.0
        
        length = len(excerpt)
        
        # Length check
        if length < 80:
            issues.append(f"Excerpt too short ({length} chars, optimal 120-160)")
        elif length > 160:
            issues.append(f"Excerpt too long ({length} chars, optimal 120-160)")
        elif 120 <= length <= 160:
            score += 50
        elif 100 <= length < 120 or 160 < length <= 170:
            score += 35
        else:
            score += 20
        
        # Has period (complete sentence)
        if excerpt.endswith('.'):
            score += 20
        
        # Action words
        action_words = ["discover", "learn", "find", "understand", "explore", "master", "guide"]
        if any(word in excerpt.lower() for word in action_words):
            score += 20
        
        # Not generic
        generic_phrases = ["this article is about", "learn more about", "in this guide we"]
        if not any(phrase in excerpt.lower() for phrase in generic_phrases):
            score += 10
        
        return min(score, 100.0), issues
    
    @staticmethod
    def get_seo_score(title: str, excerpt: str, content: str, category: str) -> Dict:
        """Get comprehensive SEO score for generated blog."""
        
        title_score, title_issues = ContentQualityValidator.validate_title(title)
        excerpt_score, excerpt_issues = ContentQualityValidator.validate_excerpt(excerpt)
        content_score, content_issues = ContentQualityValidator.validate_content(content)
        
        # Category score
        valid_categories = ["Tech", "AI", "Marketing", "Enterprise", "Developer"]
        category_score = 100.0 if category in valid_categories else 50.0
        
        # Overall score (weighted average)
        overall_score = (
            (title_score * 0.20) +
            (excerpt_score * 0.15) +
            (content_score * 0.50) +
            (category_score * 0.15)
        )
        
        return {
            "overall_score": round(overall_score, 1),
            "scores": {
                "title": round(title_score, 1),
                "excerpt": round(excerpt_score, 1),
                "content": round(content_score, 1),
                "category": round(category_score, 1)
            },
            "issues": {
                "title_issues": title_issues,
                "excerpt_issues": excerpt_issues,
                "content_issues": content_issues
            },
            "quality_rating": _get_rating(overall_score),
            "recommendations": _get_recommendations(overall_score, title_issues + excerpt_issues + content_issues)
        }


def _get_rating(score: float) -> str:
    """Convert score to rating."""
    if score >= 85:
        return "Excellent ⭐⭐⭐⭐⭐"
    elif score >= 75:
        return "Very Good ⭐⭐⭐⭐"
    elif score >= 65:
        return "Good ⭐⭐⭐"
    elif score >= 50:
        return "Fair ⭐⭐"
    else:
        return "Needs Improvement ⭐"


def _get_recommendations(score: float, issues: List[str]) -> List[str]:
    """Get improvement recommendations."""
    recommendations = []
    
    if score < 65:
        recommendations.append("Consider regenerating this blog with updated parameters")
    
    if "Title too short" in issues:
        recommendations.append("Expand title to 40-70 characters for better SEO")
    
    if "Title too long" in issues:
        recommendations.append("Shorten title to under 85 characters")
    
    if "Content too short" in issues:
        recommendations.append("Expand content to at least 1500-2000 words")
    
    if "Paragraphs too long" in issues:
        recommendations.append("Break up long paragraphs into smaller, more digestible chunks")
    
    if not recommendations:
        recommendations.append("✅ Content meets quality standards - ready for publication")
    
    return recommendations


async def validate_generated_blog(blog_data: Dict) -> Dict:
    """Validate complete generated blog and return quality report."""
    
    validator = ContentQualityValidator()
    
    seo_score = validator.get_seo_score(
        title=blog_data.get("title", ""),
        excerpt=blog_data.get("excerpt", ""),
        content=blog_data.get("content", ""),
        category=blog_data.get("category", "")
    )
    
    # Add validation results
    blog_data["quality_analysis"] = seo_score
    blog_data["is_publishable"] = seo_score["overall_score"] >= 65
    
    return {
        "blog_id": blog_data.get("id", "unknown"),
        "title": blog_data.get("title", ""),
        "quality_score": seo_score["overall_score"],
        "rating": seo_score["quality_rating"],
        "detailed_scores": seo_score["scores"],
        "issues": seo_score["issues"],
        "recommendations": seo_score["recommendations"],
        "is_publishable": blog_data["is_publishable"],
        "next_action": "Ready for publication" if blog_data["is_publishable"] 
                      else "Please review recommendations before publishing"
    }
