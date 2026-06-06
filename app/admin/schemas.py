from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from datetime import datetime

class AgentProfileSchema(BaseModel):
    id: Optional[str] = Field(None, description="Firestore document identifier")
    profile_name: str = Field(..., example="Enterprise SaaS Tech Profile")
    target_industries: List[str] = Field(..., example=["Cloud Computing", "AI/ML", "DevOps"])
    technology_focus: List[str] = Field(..., example=["Java", "Spring Boot", "FastAPI", "Vector Databases"])
    ranking_goals: List[str] = Field(..., example=["Rank for vector storage comparison", "Increase organic traffic for AI lead generation"])
    preferred_tone: str = Field("professional_insightful", description="e.g., casual, technical_deep_dive, witty")
    exclusion_policies: List[str] = Field(default=[], description="Keywords or topics completely banned from generation")
    
    # Action Footprint Limits & Governance
    max_posts_per_week: int = Field(default=3, ge=1, le=14)
    approval_threshold_risk: str = Field("medium", description="low, medium, high - risk tier determining auto-publish behavior")
    topics_requiring_approval: List[str] = Field(default=[], description="Specific high-impact topics that always hold for approval")

class SystemSettingsSchema(BaseModel):
    active_profile_id: str = Field(..., description="The ID of the AgentProfileSchema document currently running the loops")
    is_autonomous_mode_enabled: bool = Field(default=False)
    last_run_timestamp: Optional[datetime] = None

class ApprovalActionSchema(BaseModel):
    action: str = Field(..., example="approve", description="Must be either 'approve' or 'reject'")
    admin_email: EmailStr
    rejection_reason: Optional[str] = None

class BlogResponseSchema(BaseModel):
    id: str
    title: str
    authorName: str
    authorEmail: str
    category: str
    content: str
    excerpt: str
    featuredImage: str
    status: str
    tags: List[str] = []
    views: int = 0
    createdAt: datetime
    updatedAt: datetime