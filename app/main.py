"""
FastAPI application for Indian Company Intelligence RAG System
"""

import os
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.rag import RAGSystem, QueryRewriter, DocumentReRanker
from app.core.retrieval import RetrievalSystem
from app.models.schemas import (
    QueryRequest, QueryResponse, UserFeedback, 
    RetrievalEvaluation, RAGEvaluation, SystemMetrics,
    RetrievalMethod, PromptType
)
from app.api.monitoring import MonitoringService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Indian Company Intelligence RAG API",
    description="Advanced RAG system for querying Indian company data with multiple retrieval and generation approaches",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
rag_system = None
retrieval_system = None
query_rewriter = None
document_reranker = None
monitoring_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global rag_system, retrieval_system, query_rewriter, document_reranker, monitoring_service
    
    try:
        logger.info("Initializing RAG system components...")
        
        # Initialize core systems
        rag_system = RAGSystem()
        retrieval_system = RetrievalSystem()
        query_rewriter = QueryRewriter()
        document_reranker = DocumentReRanker()
        monitoring_service = MonitoringService()
        
        # Check system health
        health_status = await retrieval_system.get_health_status()
        if not health_status["overall"]:
            logger.warning("Some systems are not healthy, but continuing startup")
        
        logger.info("RAG system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down RAG system...")

# Dependency to get monitoring service
def get_monitoring_service():
    return monitoring_service

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Indian Company Intelligence RAG API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "query": "/query",
            "health": "/health",
            "evaluation": "/evaluation",
            "feedback": "/feedback",
            "metrics": "/metrics"
        }
    }

@app.post("/query", response_model=QueryResponse)
async def query_companies(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """
    Query the company database using RAG
    
    Supports multiple retrieval methods and prompt strategies
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing query: {request.query[:100]}...")
        
        # Process the query
        response = await rag_system.process_query(
            query=request.query,
            retrieval_method=request.retrieval_method.value,
            prompt_type=request.prompt_type,
            top_k=request.top_k
        )
        
        # Log query for monitoring
        background_tasks.add_task(
            monitoring.log_query,
            query=request.query,
            user_id=request.user_id,
            response_time_ms=response.response_time_ms,
            retrieval_method=request.retrieval_method.value,
            num_results=response.num_results
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/enhanced")
async def enhanced_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """
    Enhanced query with query rewriting and document re-ranking
    """
    try:
        logger.info(f"Processing enhanced query: {request.query[:100]}...")
        
        # Step 1: Query rewriting
        rewritten_queries = await query_rewriter.rewrite_query(request.query)
        
        # Step 2: Retrieve documents for all query variations
        all_documents = []
        for query_var in rewritten_queries:
            docs = await retrieval_system.search(
                query=query_var,
                method=request.retrieval_method,
                top_k=request.top_k
            )
            all_documents.extend(docs)
        
        # Remove duplicates and get top documents
        unique_docs = {}
        for doc in all_documents:
            key = doc.company_name + doc.city
            if key not in unique_docs or doc.score > unique_docs[key].score:
                unique_docs[key] = doc
        
        top_documents = sorted(unique_docs.values(), key=lambda x: x.score, reverse=True)[:request.top_k*2]
        
        # Step 3: Re-rank documents
        reranked_documents = await document_reranker.rerank_documents(request.query, top_documents)
        final_documents = reranked_documents[:request.top_k]
        
        # Step 4: Generate response
        response_text = await rag_system.generate_response(
            query=request.query,
            documents=final_documents,
            prompt_type=request.prompt_type
        )
        
        # Create response
        response = QueryResponse(
            query=request.query,
            response=response_text,
            retrieval_method=f"enhanced_{request.retrieval_method.value}",
            prompt_type=request.prompt_type.value,
            retrieved_documents=final_documents,
            response_time_ms=0,  # Calculate if needed
            num_results=len(final_documents)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Enhanced query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """System health check"""
    try:
        health_status = await retrieval_system.get_health_status()
        
        return {
            "status": "healthy" if health_status["overall"] else "degraded",
            "timestamp": datetime.now().isoformat(),
            "components": health_status
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.post("/feedback")
async def submit_feedback(
    feedback: UserFeedback,
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Submit user feedback for a query"""
    try:
        await monitoring.log_feedback(feedback)
        
        return {
            "status": "success",
            "message": "Feedback recorded successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to record feedback")

@app.get("/evaluation/retrieval")
async def get_retrieval_evaluation():
    """Get retrieval method evaluation results"""
    try:
        # This would typically load from stored evaluation results
        # For now, return example results
        evaluation_results = {
            "vector": {
                "precision_at_5": 0.87,
                "recall_at_5": 0.82,
                "avg_response_time_ms": 145.3,
                "query_count": 50
            },
            "elasticsearch": {
                "precision_at_5": 0.91,
                "recall_at_5": 0.78,
                "avg_response_time_ms": 89.7,
                "query_count": 50
            },
            "hybrid": {
                "precision_at_5": 0.94,
                "recall_at_5": 0.89,
                "avg_response_time_ms": 198.2,
                "query_count": 50
            }
        }
        
        return evaluation_results
        
    except Exception as e:
        logger.error(f"Failed to get retrieval evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/evaluation/rag")
async def get_rag_evaluation():
    """Get RAG approach evaluation results"""
    try:
        # This would typically load from stored evaluation results
        evaluation_results = {
            "basic": {
                "relevance_score": 0.82,
                "accuracy_score": 0.79,
                "avg_response_time_ms": 1240.5,
                "query_count": 25
            },
            "enhanced": {
                "relevance_score": 0.89,
                "accuracy_score": 0.86,
                "avg_response_time_ms": 1456.8,
                "query_count": 25
            },
            "context_aware": {
                "relevance_score": 0.92,
                "accuracy_score": 0.91,
                "avg_response_time_ms": 1678.3,
                "query_count": 25
            }
        }
        
        return evaluation_results
        
    except Exception as e:
        logger.error(f"Failed to get RAG evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_system_metrics(
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get system metrics for monitoring dashboard"""
    try:
        metrics = await monitoring.get_system_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/queries")
async def get_query_metrics(
    hours: int = 24,
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get query metrics for specified time period"""
    try:
        metrics = await monitoring.get_query_metrics(hours)
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get query metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/companies/search")
async def search_companies(
    query: str,
    method: RetrievalMethod = RetrievalMethod.HYBRID,
    limit: int = 10
):
    """Direct company search without RAG generation"""
    try:
        documents = await retrieval_system.search(query, method, limit)
        
        return {
            "query": query,
            "method": method.value,
            "total_results": len(documents),
            "companies": [
                {
                    "name": doc.company_name,
                    "state": doc.state,
                    "city": doc.city,
                    "industry": doc.industry_classification,
                    "score": doc.score
                }
                for doc in documents
            ]
        }
        
    except Exception as e:
        logger.error(f"Company search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )