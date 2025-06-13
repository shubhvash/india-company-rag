"""
Data models and schemas for the RAG application
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class RetrievalMethod(str, Enum):
    """Available retrieval methods"""
    VECTOR = "vector"
    ELASTICSEARCH = "elasticsearch"
    HYBRID = "hybrid"

class PromptType(str, Enum):
    """Available prompt types for RAG evaluation"""
    BASIC = "basic"
    ENHANCED = "enhanced"
    CONTEXT_AWARE = "context_aware"

class QueryRequest(BaseModel):
    """Request model for queries"""
    query: str
    retrieval_method: RetrievalMethod = RetrievalMethod.HYBRID
    prompt_type: PromptType = PromptType.CONTEXT_AWARE
    top_k: int = 5
    user_id: Optional[str] = None

class DocumentChunk(BaseModel):
    """Document chunk model"""
    id: str
    company_name: str
    state: str
    city: str
    industry_classification: str
    full_text: str
    score: float
    chunk_type: str
    
    # Financial fields
    cin: Optional[str] = None
    authorized_capital: Optional[int] = None
    paid_up_capital: Optional[int] = None
    capital_utilization_ratio: Optional[float] = None
    
    # Additional company fields
    company_category: Optional[str] = None
    company_status: Optional[str] = None
    registration_date: Optional[str] = None
    listing_status: Optional[str] = None
    registered_office_address: Optional[str] = None

class QueryResponse(BaseModel):
    """Response model for queries"""
    query: str
    response: str
    retrieval_method: str
    prompt_type: str
    retrieved_documents: List[DocumentChunk]
    response_time_ms: int
    num_results: int

class UserFeedback(BaseModel):
    """User feedback model"""
    query_id: int
    rating: int  # 1-5 scale
    feedback_text: Optional[str] = None
    user_id: Optional[str] = None

class RetrievalEvaluation(BaseModel):
    """Retrieval evaluation results"""
    method: str
    precision_at_k: float
    recall_at_k: float
    response_time_ms: int
    query_count: int

class RAGEvaluation(BaseModel):
    """RAG evaluation results"""
    prompt_type: str
    relevance_score: float
    accuracy_score: float
    query_count: int

class SystemMetrics(BaseModel):
    """System metrics model"""
    query_volume_24h: int
    avg_response_time_ms: float
    user_satisfaction_avg: float
    system_uptime_percent: float
    active_users_24h: int