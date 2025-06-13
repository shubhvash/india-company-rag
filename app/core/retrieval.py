"""
Multiple retrieval approaches for the RAG system
"""

import os
import logging
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from elasticsearch import Elasticsearch
import asyncio
from app.models.schemas import DocumentChunk, RetrievalMethod

logger = logging.getLogger(__name__)

class RetrievalSystem:
    """Multi-modal retrieval system with vector, text, and hybrid search"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.qdrant_client = None
        self.es_client = None
        self.collection_name = "indian_companies"
        self.es_index = "indian_companies"
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize database clients"""
        try:
            # Initialize Qdrant
            self.qdrant_client = QdrantClient(
                host=os.getenv("QDRANT_HOST", "localhost"),
                port=int(os.getenv("QDRANT_PORT", "6333"))
            )
            
            # Initialize Elasticsearch
            self.es_client = Elasticsearch([
                os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
            ])
            
            logger.info("Retrieval system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize retrieval system: {e}")
            raise
    
    async def vector_search(self, query: str, top_k: int = 5) -> List[DocumentChunk]:
        """Perform vector similarity search using Qdrant"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Search in Qdrant
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                with_payload=True
            )
            
            # Convert to DocumentChunk objects
            documents = []
            for hit in search_result:
                payload = hit.payload
                document = DocumentChunk(
                    id=str(hit.id),
                    company_name=payload.get('company_name', ''),
                    state=payload.get('state', ''),
                    city=payload.get('city', ''),
                    industry_classification=payload.get('industry_classification', ''),
                    full_text=payload.get('full_text', ''),
                    score=hit.score,
                    chunk_type=payload.get('chunk_type', 'unknown'),
                    # Financial fields
                    cin=payload.get('cin'),
                    authorized_capital=payload.get('authorized_capital'),
                    paid_up_capital=payload.get('paid_up_capital'),
                    capital_utilization_ratio=payload.get('capital_utilization_ratio'),
                    # Additional fields
                    company_category=payload.get('company_category'),
                    company_status=payload.get('company_status'),
                    registration_date=payload.get('registration_date'),
                    listing_status=payload.get('listing_status'),
                    registered_office_address=payload.get('registered_office_address')
                )
                documents.append(document)
            
            logger.info(f"Vector search returned {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def elasticsearch_search(self, query: str, top_k: int = 5) -> List[DocumentChunk]:
        """Perform text search using Elasticsearch"""
        try:
            # Build Elasticsearch query with financial search support
            should_clauses = [
                {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "company_name^3",
                            "industry_classification^2",
                            "full_text",
                            "registered_office_address",
                            "city",
                            "state",
                            "company_category",
                            "company_status"
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                },
                {
                    "match_phrase": {
                        "full_text": {
                            "query": query,
                            "boost": 2
                        }
                    }
                }
            ]
            
            # Add financial range queries for capital-related searches
            query_lower = query.lower()
            if any(word in query_lower for word in ['capital', 'high capital', 'low capital', 'rich', 'large', 'big']):
                # Add range queries for capital searches
                should_clauses.extend([
                    {
                        "range": {
                            "authorized_capital": {
                                "gte": 1000000 if 'high' in query_lower or 'large' in query_lower or 'big' in query_lower else 0,
                                "boost": 1.5
                            }
                        }
                    },
                    {
                        "range": {
                            "paid_up_capital": {
                                "gte": 500000 if 'high' in query_lower or 'large' in query_lower or 'big' in query_lower else 0,
                                "boost": 1.5
                            }
                        }
                    }
                ])
            
            es_query = {
                "query": {
                    "bool": {
                        "should": should_clauses
                    }
                },
                "size": top_k,
                "_source": True
            }
            
            # Execute search
            response = self.es_client.search(
                index=self.es_index,
                body=es_query
            )
            
            # Convert to DocumentChunk objects
            documents = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                document = DocumentChunk(
                    id=hit['_id'],
                    company_name=source.get('company_name', ''),
                    state=source.get('state', ''),
                    city=source.get('city', ''),
                    industry_classification=source.get('industry_classification', ''),
                    full_text=source.get('full_text', ''),
                    score=hit['_score'],
                    chunk_type=source.get('chunk_type', 'unknown'),
                    # Financial fields
                    cin=source.get('cin'),
                    authorized_capital=source.get('authorized_capital'),
                    paid_up_capital=source.get('paid_up_capital'),
                    capital_utilization_ratio=source.get('capital_utilization_ratio'),
                    # Additional fields
                    company_category=source.get('company_category'),
                    company_status=source.get('company_status'),
                    registration_date=source.get('registration_date'),
                    listing_status=source.get('listing_status'),
                    registered_office_address=source.get('registered_office_address')
                )
                documents.append(document)
            
            logger.info(f"Elasticsearch search returned {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Elasticsearch search failed: {e}")
            return []
    
    async def hybrid_search(self, query: str, top_k: int = 5, 
                          vector_weight: float = 0.6, 
                          text_weight: float = 0.4) -> List[DocumentChunk]:
        """Perform hybrid search combining vector and text search"""
        try:
            # Get results from both methods
            vector_results, es_results = await asyncio.gather(
                self.vector_search(query, top_k * 2),  # Get more to have options for fusion
                self.elasticsearch_search(query, top_k * 2)
            )
            
            # Normalize scores
            vector_results = self._normalize_scores(vector_results)
            es_results = self._normalize_scores(es_results)
            
            # Create a combined ranking using reciprocal rank fusion
            combined_results = self._reciprocal_rank_fusion(
                vector_results, es_results, vector_weight, text_weight
            )
            
            # Return top_k results
            hybrid_results = combined_results[:top_k]
            
            logger.info(f"Hybrid search returned {len(hybrid_results)} documents")
            return hybrid_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    def _normalize_scores(self, documents: List[DocumentChunk]) -> List[DocumentChunk]:
        """Normalize scores to 0-1 range"""
        if not documents:
            return documents
        
        scores = [doc.score for doc in documents]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            for doc in documents:
                doc.score = 1.0
        else:
            for doc in documents:
                doc.score = (doc.score - min_score) / (max_score - min_score)
        
        return documents
    
    def _reciprocal_rank_fusion(self, vector_results: List[DocumentChunk], 
                               es_results: List[DocumentChunk],
                               vector_weight: float, text_weight: float) -> List[DocumentChunk]:
        """Combine results using reciprocal rank fusion"""
        
        # Create score dictionaries
        vector_scores = {doc.company_name + doc.full_text[:50]: (doc, 1/(i+1)) 
                        for i, doc in enumerate(vector_results)}
        es_scores = {doc.company_name + doc.full_text[:50]: (doc, 1/(i+1)) 
                    for i, doc in enumerate(es_results)}
        
        # Combine scores
        combined_scores = {}
        
        # Add vector scores
        for key, (doc, rank_score) in vector_scores.items():
            combined_scores[key] = {
                'doc': doc,
                'score': vector_weight * rank_score,
                'methods': ['vector']
            }
        
        # Add elasticsearch scores
        for key, (doc, rank_score) in es_scores.items():
            if key in combined_scores:
                combined_scores[key]['score'] += text_weight * rank_score
                combined_scores[key]['methods'].append('elasticsearch')
            else:
                combined_scores[key] = {
                    'doc': doc,
                    'score': text_weight * rank_score,
                    'methods': ['elasticsearch']
                }
        
        # Sort by combined score
        sorted_results = sorted(combined_scores.items(), 
                              key=lambda x: x[1]['score'], reverse=True)
        
        # Create final document list
        final_documents = []
        for key, result in sorted_results:
            doc = result['doc']
            doc.score = result['score']
            final_documents.append(doc)
        
        return final_documents
    
    async def search(self, query: str, method: RetrievalMethod, 
                    top_k: int = 5) -> List[DocumentChunk]:
        """Main search interface"""
        if method == RetrievalMethod.VECTOR:
            return await self.vector_search(query, top_k)
        elif method == RetrievalMethod.ELASTICSEARCH:
            return await self.elasticsearch_search(query, top_k)
        elif method == RetrievalMethod.HYBRID:
            return await self.hybrid_search(query, top_k)
        else:
            raise ValueError(f"Unknown retrieval method: {method}")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all retrieval systems"""
        status = {
            "qdrant": False,
            "elasticsearch": False,
            "overall": False
        }
        
        try:
            # Check Qdrant
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            status["qdrant"] = True
            status["qdrant_points"] = collection_info.points_count
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
        
        try:
            # Check Elasticsearch
            es_health = self.es_client.cluster.health()
            status["elasticsearch"] = es_health['status'] in ['green', 'yellow']
            
            # Get document count
            count_result = self.es_client.count(index=self.es_index)
            status["elasticsearch_docs"] = count_result['count']
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
        
        status["overall"] = status["qdrant"] and status["elasticsearch"]
        return status