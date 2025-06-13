"""
Monitoring service for tracking system metrics and user feedback
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import asyncpg
from app.models.schemas import UserFeedback, SystemMetrics

logger = logging.getLogger(__name__)

class MonitoringService:
    """Service for monitoring system performance and user feedback"""
    
    def __init__(self):
        self.db_pool = None
        self._initialize_db_pool()
    
    def _initialize_db_pool(self):
        """Initialize database connection pool"""
        try:
            postgres_url = os.getenv("POSTGRES_URL", "postgresql://raguser:ragpassword@localhost:5432/monitoring")
            # Note: In production, would properly initialize asyncpg pool
            logger.info("Monitoring service initialized (database connection configured)")
        except Exception as e:
            logger.error(f"Failed to initialize monitoring database: {e}")
    
    async def log_query(self, query: str, user_id: Optional[str], response_time_ms: int,
                       retrieval_method: str, num_results: int) -> int:
        """Log a user query for monitoring"""
        try:
            # In production, would execute actual database insert
            query_id = hash(query + str(datetime.now())) % 1000000
            
            logger.info(f"Logged query {query_id}: {query[:50]}... "
                       f"(method: {retrieval_method}, time: {response_time_ms}ms)")
            
            return query_id
            
        except Exception as e:
            logger.error(f"Failed to log query: {e}")
            return -1
    
    async def log_feedback(self, feedback: UserFeedback):
        """Log user feedback"""
        try:
            # In production, would execute actual database insert
            logger.info(f"Logged feedback for query {feedback.query_id}: "
                       f"rating {feedback.rating}/5")
            
        except Exception as e:
            logger.error(f"Failed to log feedback: {e}")
    
    async def log_retrieval_metrics(self, query_id: int, method: str,
                                   precision_score: float, recall_score: float,
                                   response_time_ms: int, num_documents: int):
        """Log retrieval performance metrics"""
        try:
            # In production, would execute actual database insert
            logger.info(f"Logged retrieval metrics for query {query_id}: "
                       f"method={method}, precision={precision_score:.3f}")
            
        except Exception as e:
            logger.error(f"Failed to log retrieval metrics: {e}")
    
    async def log_rag_evaluation(self, query: str, prompt_type: str,
                                response: str, relevance_score: float,
                                accuracy_score: float):
        """Log RAG evaluation metrics"""
        try:
            # In production, would execute actual database insert
            logger.info(f"Logged RAG evaluation: prompt={prompt_type}, "
                       f"relevance={relevance_score:.3f}, accuracy={accuracy_score:.3f}")
            
        except Exception as e:
            logger.error(f"Failed to log RAG evaluation: {e}")
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        try:
            # In production, would query actual database
            # For now, return mock metrics
            
            now = datetime.now()
            metrics = SystemMetrics(
                query_volume_24h=156,
                avg_response_time_ms=245.8,
                user_satisfaction_avg=4.2,
                system_uptime_percent=99.5,
                active_users_24h=23
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            # Return default metrics on error
            return SystemMetrics(
                query_volume_24h=0,
                avg_response_time_ms=0.0,
                user_satisfaction_avg=0.0,
                system_uptime_percent=0.0,
                active_users_24h=0
            )
    
    async def get_query_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get query metrics for specified time period"""
        try:
            # In production, would query actual database
            # For now, return mock data
            
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Generate mock hourly data
            hourly_data = []
            for i in range(hours):
                hour_time = start_time + timedelta(hours=i)
                hourly_data.append({
                    "timestamp": hour_time.isoformat(),
                    "query_count": max(0, 10 + (i % 12) - 6),  # Simulate daily pattern
                    "avg_response_time": 200 + (i % 5) * 50,
                    "success_rate": 0.95 + (i % 3) * 0.01
                })
            
            # Method distribution
            method_distribution = {
                "hybrid": 0.6,
                "vector": 0.25,
                "elasticsearch": 0.15
            }
            
            # Response time by method
            response_times_by_method = {
                "hybrid": 245.8,
                "vector": 189.3,
                "elasticsearch": 156.7
            }
            
            return {
                "time_period_hours": hours,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "hourly_data": hourly_data,
                "method_distribution": method_distribution,
                "response_times_by_method": response_times_by_method,
                "total_queries": sum(h["query_count"] for h in hourly_data),
                "avg_response_time": sum(h["avg_response_time"] for h in hourly_data) / len(hourly_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to get query metrics: {e}")
            return {}
    
    async def get_user_feedback_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get user feedback summary"""
        try:
            # In production, would query actual database
            # For now, return mock data
            
            return {
                "time_period_days": days,
                "total_feedback_count": 89,
                "average_rating": 4.2,
                "rating_distribution": {
                    "5": 45,
                    "4": 32,
                    "3": 8,
                    "2": 3,
                    "1": 1
                },
                "satisfaction_trend": [4.1, 4.0, 4.2, 4.3, 4.2, 4.1, 4.2],  # Daily averages
                "common_feedback_themes": [
                    {"theme": "response_accuracy", "count": 34, "sentiment": "positive"},
                    {"theme": "response_speed", "count": 28, "sentiment": "positive"},
                    {"theme": "result_relevance", "count": 22, "sentiment": "positive"},
                    {"theme": "interface_usability", "count": 15, "sentiment": "mixed"},
                    {"theme": "missing_companies", "count": 8, "sentiment": "negative"}
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get feedback summary: {e}")
            return {}
    
    async def get_retrieval_performance(self) -> Dict[str, Any]:
        """Get retrieval method performance comparison"""
        try:
            # In production, would calculate from stored metrics
            # For now, return mock data based on evaluation results
            
            return {
                "methods": {
                    "vector": {
                        "precision_at_5": 0.87,
                        "recall_at_5": 0.82,
                        "avg_response_time_ms": 145.3,
                        "usage_percentage": 25.0,
                        "user_satisfaction": 4.1
                    },
                    "elasticsearch": {
                        "precision_at_5": 0.91,
                        "recall_at_5": 0.78,
                        "avg_response_time_ms": 89.7,
                        "usage_percentage": 15.0,
                        "user_satisfaction": 4.0
                    },
                    "hybrid": {
                        "precision_at_5": 0.94,
                        "recall_at_5": 0.89,
                        "avg_response_time_ms": 198.2,
                        "usage_percentage": 60.0,
                        "user_satisfaction": 4.3
                    }
                },
                "trends": {
                    "hybrid_adoption": [0.45, 0.52, 0.58, 0.60, 0.62],  # Weekly trend
                    "avg_precision": [0.89, 0.90, 0.91, 0.92, 0.91],
                    "avg_response_time": [210, 205, 200, 198, 195]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get retrieval performance: {e}")
            return {}
    
    async def get_rag_performance(self) -> Dict[str, Any]:
        """Get RAG approach performance comparison"""
        try:
            # In production, would calculate from stored metrics
            return {
                "prompt_types": {
                    "basic": {
                        "relevance_score": 0.82,
                        "accuracy_score": 0.79,
                        "avg_response_time_ms": 1240.5,
                        "usage_percentage": 15.0,
                        "user_satisfaction": 3.8
                    },
                    "enhanced": {
                        "relevance_score": 0.89,
                        "accuracy_score": 0.86,
                        "avg_response_time_ms": 1456.8,
                        "usage_percentage": 25.0,
                        "user_satisfaction": 4.1
                    },
                    "context_aware": {
                        "relevance_score": 0.92,
                        "accuracy_score": 0.91,
                        "avg_response_time_ms": 1678.3,
                        "usage_percentage": 60.0,
                        "user_satisfaction": 4.4
                    }
                },
                "best_practices": {
                    "query_rewriting_improvement": 0.15,
                    "document_reranking_improvement": 0.12,
                    "hybrid_search_adoption": 0.78
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get RAG performance: {e}")
            return {}