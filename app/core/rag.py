"""
RAG (Retrieval-Augmented Generation) system with multiple prompt strategies
"""

import os
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from app.models.schemas import DocumentChunk, PromptType, QueryResponse
from app.core.retrieval import RetrievalSystem

logger = logging.getLogger(__name__)


def _response_text(response) -> str:
    """Join the text parts of a Gemini response (newer models return multi-part replies)."""
    try:
        parts = response.candidates[0].content.parts
    except (AttributeError, IndexError):
        return ""
    return "".join(getattr(p, "text", "") or "" for p in parts)

class RAGSystem:
    """RAG system with multiple prompt strategies for evaluation"""
    
    def __init__(self):
        self.retrieval_system = RetrievalSystem()
        self._initialize_llm()
        
        # Prompt templates for different strategies
        self.prompt_templates = {
            PromptType.BASIC: self._get_basic_prompt(),
            PromptType.ENHANCED: self._get_enhanced_prompt(),
            PromptType.CONTEXT_AWARE: self._get_context_aware_prompt()
        }
    
    def _initialize_llm(self):
        """Initialize Google Gemini API"""
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(os.getenv('GEMINI_MODEL', 'gemini-flash-lite-latest'))
            
            logger.info("Google Gemini initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Gemini: {e}")
            raise
    
    def _get_basic_prompt(self) -> str:
        """Basic prompt template"""
        return """Based on the following company information, answer the user's question.

Company Information:
{context}

Question: {query}

Answer:"""
    
    def _get_enhanced_prompt(self) -> str:
        """Enhanced prompt template with more detailed instructions"""
        return """You are an expert business analyst specializing in Indian companies. Using the provided company data, give a comprehensive and accurate answer to the user's question.

Instructions:
- Provide specific details from the company data
- Include relevant financial information when available
- Mention company locations and industry classifications
- Be precise and factual
- If multiple companies are relevant, compare them

Company Data:
{context}

User Question: {query}

Detailed Answer:"""
    
    def _get_context_aware_prompt(self) -> str:
        """Context-aware prompt template that adapts to query type"""
        return """You are an AI assistant specialized in Indian business intelligence. Analyze the user's question and provide a tailored response using the company information provided.

Guidelines:
- For financial queries: Focus on capital structure, financial health, and investment potential
- For location queries: Emphasize geographical distribution, regional trends, and market presence
- For industry queries: Highlight sector analysis, competitive landscape, and business categories
- For company-specific queries: Provide comprehensive company profiles with key details
- Always cite specific data points from the context
- If data is insufficient, clearly state limitations

Available Company Information:
{context}

User Query: {query}

Context-Aware Response:"""
    
    def _prepare_context(self, documents: List[DocumentChunk]) -> str:
        """Prepare context from retrieved documents"""
        if not documents:
            return "No relevant company information found."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            # Format financial information
            financial_info = ""
            if doc.authorized_capital is not None:
                financial_info += f"\nAuthorized Capital: ₹{doc.authorized_capital:,}"
            if doc.paid_up_capital is not None:
                financial_info += f"\nPaid-up Capital: ₹{doc.paid_up_capital:,}"
            if doc.capital_utilization_ratio is not None:
                financial_info += f"\nCapital Utilization: {doc.capital_utilization_ratio}%"
            
            # Format additional company info
            additional_info = ""
            if doc.cin:
                additional_info += f"\nCIN: {doc.cin}"
            if doc.company_category:
                additional_info += f"\nCategory: {doc.company_category}"
            if doc.company_status:
                additional_info += f"\nStatus: {doc.company_status}"
            if doc.registration_date:
                additional_info += f"\nRegistration Date: {doc.registration_date}"
            if doc.listing_status:
                additional_info += f"\nListing Status: {doc.listing_status}"
            
            context_part = f"""
Company {i}: {doc.company_name}
State: {doc.state}
City: {doc.city}
Industry: {doc.industry_classification}{financial_info}{additional_info}
Details: {doc.full_text}
---"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    async def generate_response(self, query: str, documents: List[DocumentChunk],
                              prompt_type: PromptType = PromptType.CONTEXT_AWARE) -> str:
        """Generate response using specified prompt strategy"""
        try:
            # Prepare context from documents
            context = self._prepare_context(documents)
            
            # Get appropriate prompt template
            prompt_template = self.prompt_templates[prompt_type]
            
            # Format prompt with context and query
            formatted_prompt = prompt_template.format(
                context=context,
                query=query
            )
            
            # Generate response using Gemini
            response = self.model.generate_content(formatted_prompt)
            
            if _response_text(response):
                logger.info(f"Generated response using {prompt_type} prompt")
                return _response_text(response).strip()
            else:
                logger.warning("Empty response from Gemini")
                return "I apologize, but I couldn't generate a response for your query."
                
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return f"I encountered an error while processing your query: {str(e)}"
    
    async def process_query(self, query: str, retrieval_method: str = "hybrid",
                          prompt_type: PromptType = PromptType.CONTEXT_AWARE,
                          top_k: int = 5) -> QueryResponse:
        """Process a complete RAG query"""
        import time
        start_time = time.time()
        
        try:
            # Retrieve relevant documents
            documents = await self.retrieval_system.search(
                query=query,
                method=retrieval_method,
                top_k=top_k
            )
            
            # Generate response
            response_text = await self.generate_response(
                query=query,
                documents=documents,
                prompt_type=prompt_type
            )
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Create response object
            response = QueryResponse(
                query=query,
                response=response_text,
                retrieval_method=retrieval_method,
                prompt_type=prompt_type.value,
                retrieved_documents=documents,
                response_time_ms=response_time_ms,
                num_results=len(documents)
            )
            
            logger.info(f"Processed query in {response_time_ms}ms")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            # Return error response
            return QueryResponse(
                query=query,
                response=f"I apologize, but I encountered an error: {str(e)}",
                retrieval_method=retrieval_method,
                prompt_type=prompt_type.value,
                retrieved_documents=[],
                response_time_ms=int((time.time() - start_time) * 1000),
                num_results=0
            )

class QueryRewriter:
    """Query rewriting system to improve retrieval performance"""
    
    def __init__(self):
        self._initialize_rewriter()
    
    def _initialize_rewriter(self):
        """Initialize query rewriter"""
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(os.getenv('GEMINI_MODEL', 'gemini-flash-lite-latest'))
            
        except Exception as e:
            logger.error(f"Failed to initialize query rewriter: {e}")
            raise
    
    async def rewrite_query(self, original_query: str) -> List[str]:
        """Rewrite query to improve retrieval performance"""
        try:
            rewrite_prompt = f"""
Given the following query about Indian companies, generate 3 alternative phrasings that would help find relevant company information. Focus on:
1. Expanding abbreviations and business terms
2. Adding synonyms for industry terms
3. Including relevant keywords for better matching

Original Query: {original_query}

Generate 3 alternative queries (one per line):
"""
            
            response = self.model.generate_content(rewrite_prompt)
            
            if _response_text(response):
                # Parse the response to extract alternative queries
                alternatives = [line.strip() for line in _response_text(response).strip().split('\n') 
                              if line.strip() and not line.strip().startswith('#')]
                
                # Include original query
                all_queries = [original_query] + alternatives[:3]
                
                logger.info(f"Generated {len(all_queries)} query variations")
                return all_queries
            else:
                logger.warning("Failed to generate query alternatives")
                return [original_query]
                
        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")
            return [original_query]

class DocumentReRanker:
    """Document re-ranking system to improve retrieval quality"""
    
    def __init__(self):
        self._initialize_reranker()
    
    def _initialize_reranker(self):
        """Initialize document re-ranker"""
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(os.getenv('GEMINI_MODEL', 'gemini-flash-lite-latest'))
            
        except Exception as e:
            logger.error(f"Failed to initialize document re-ranker: {e}")
            raise
    
    async def rerank_documents(self, query: str, 
                             documents: List[DocumentChunk]) -> List[DocumentChunk]:
        """Re-rank documents based on relevance to query"""
        if len(documents) <= 1:
            return documents
        
        try:
            # Create ranking prompt
            doc_summaries = []
            for i, doc in enumerate(documents):
                summary = f"{i+1}. {doc.company_name} - {doc.industry_classification} in {doc.city}, {doc.state}"
                doc_summaries.append(summary)
            
            ranking_prompt = f"""
Given the query and list of companies, rank them from most relevant (1) to least relevant based on how well they answer the query.

Query: {query}

Companies:
{chr(10).join(doc_summaries)}

Provide only the ranking as numbers separated by commas (e.g., 3,1,5,2,4):
"""
            
            response = self.model.generate_content(ranking_prompt)
            
            if _response_text(response):
                # Parse ranking
                ranking_text = _response_text(response).strip()
                try:
                    rankings = [int(x.strip()) - 1 for x in ranking_text.split(',')]
                    
                    # Validate rankings
                    if len(rankings) == len(documents) and all(0 <= r < len(documents) for r in rankings):
                        # Reorder documents based on ranking
                        reranked_docs = [documents[i] for i in rankings]
                        logger.info("Documents re-ranked successfully")
                        return reranked_docs
                    else:
                        logger.warning("Invalid ranking format, returning original order")
                        return documents
                        
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse ranking: {e}")
                    return documents
            else:
                logger.warning("No ranking response received")
                return documents
                
        except Exception as e:
            logger.error(f"Document re-ranking failed: {e}")
            return documents