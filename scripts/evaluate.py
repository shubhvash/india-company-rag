#!/usr/bin/env python3
"""
Comprehensive evaluation system for retrieval and RAG approaches

This script evaluates:
1. Multiple retrieval methods (vector, Elasticsearch, hybrid)
2. Multiple RAG approaches (basic, enhanced, context-aware prompts)
3. Query rewriting and document re-ranking effectiveness
"""

import os
import sys
import asyncio
import logging
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.retrieval import RetrievalSystem
from app.core.rag import RAGSystem, QueryRewriter, DocumentReRanker
from app.models.schemas import RetrievalMethod, PromptType, DocumentChunk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EvaluationSuite:
    """Comprehensive evaluation suite for RAG system"""
    
    def __init__(self):
        self.retrieval_system = RetrievalSystem()
        self.rag_system = RAGSystem()
        self.query_rewriter = QueryRewriter()
        self.document_reranker = DocumentReRanker()
        
        # Test queries for evaluation
        self.test_queries = [
            "Show me technology companies in Karnataka",
            "What are the capital trends in Delhi manufacturing companies?",
            "List companies with high authorized capital in business services",
            "Find trading companies in Bangalore",
            "Which companies are in the food manufacturing sector?",
            "Show me private limited companies in Mumbai",
            "What are the largest companies by paid-up capital?",
            "Find companies registered after 2020",
            "List active companies in pharmaceutical industry",
            "Show me companies with foreign investment"
        ]
        
        # Ground truth for evaluation (simplified - in real scenario, would be manually curated)
        self.ground_truth = self._create_ground_truth()
    
    def _create_ground_truth(self) -> Dict[str, List[str]]:
        """Create ground truth mappings for evaluation"""
        return {
            "Show me technology companies in Karnataka": [
                "COMPULINX TECHNOLOGIES PRIVATE LIMITED",
                "CHAZON SOLUTIONS PRIVATE LIMITED"
            ],
            "What are the capital trends in Delhi manufacturing companies?": [
                "HOAC FOODS INDIA LIMITED",
                "MAHAVIRA FOODS LIMITED",
                "BASTI SUGAR MILLS CO LTD"
            ],
            "Find trading companies in Bangalore": [
                "NGSG OVERSEAS PRIVATE LIMITED",
                "LAAVISH ELLIXIR PRIVATE LIMITED",
                "FORCEA AUTOMOTIVE PRIVATE LIMITED"
            ],
            "Which companies are in the food manufacturing sector?": [
                "HOAC FOODS INDIA LIMITED",
                "MAHAVIRA FOODS LIMITED",
                "VISISTH CHAY VYAPAR LIMITED"
            ]
        }
    
    async def evaluate_retrieval_methods(self) -> Dict[str, Dict[str, float]]:
        """Evaluate different retrieval methods"""
        logger.info("Starting retrieval method evaluation...")
        
        methods = [RetrievalMethod.VECTOR, RetrievalMethod.ELASTICSEARCH, RetrievalMethod.HYBRID]
        results = {}
        
        for method in methods:
            logger.info(f"Evaluating {method.value} retrieval...")
            
            precision_scores = []
            recall_scores = []
            response_times = []
            
            for query in self.test_queries:
                if query not in self.ground_truth:
                    continue
                
                start_time = time.time()
                
                # Retrieve documents
                documents = await self.retrieval_system.search(query, method, top_k=5)
                
                response_time = (time.time() - start_time) * 1000
                response_times.append(response_time)
                
                # Calculate precision and recall
                retrieved_companies = [doc.company_name for doc in documents]
                relevant_companies = self.ground_truth[query]
                
                precision = self._calculate_precision(retrieved_companies, relevant_companies)
                recall = self._calculate_recall(retrieved_companies, relevant_companies)
                
                precision_scores.append(precision)
                recall_scores.append(recall)
            
            results[method.value] = {
                "precision_at_5": sum(precision_scores) / len(precision_scores) if precision_scores else 0,
                "recall_at_5": sum(recall_scores) / len(recall_scores) if recall_scores else 0,
                "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                "query_count": len(precision_scores)
            }
        
        logger.info("Retrieval evaluation completed")
        return results
    
    async def evaluate_rag_approaches(self) -> Dict[str, Dict[str, float]]:
        """Evaluate different RAG prompt approaches"""
        logger.info("Starting RAG approach evaluation...")
        
        prompt_types = [PromptType.BASIC, PromptType.ENHANCED, PromptType.CONTEXT_AWARE]
        results = {}
        
        for prompt_type in prompt_types:
            logger.info(f"Evaluating {prompt_type.value} prompt...")
            
            relevance_scores = []
            accuracy_scores = []
            response_times = []
            
            for query in self.test_queries[:5]:  # Limit for API cost
                # Process query with specific prompt type
                response = await self.rag_system.process_query(
                    query=query,
                    retrieval_method="hybrid",
                    prompt_type=prompt_type,
                    top_k=5
                )
                
                response_times.append(response.response_time_ms)
                
                # Evaluate response quality (simplified scoring)
                relevance_score = await self._evaluate_response_relevance(query, response.response)
                accuracy_score = await self._evaluate_response_accuracy(query, response.response, response.retrieved_documents)
                
                relevance_scores.append(relevance_score)
                accuracy_scores.append(accuracy_score)
            
            results[prompt_type.value] = {
                "relevance_score": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0,
                "accuracy_score": sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0,
                "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                "query_count": len(relevance_scores)
            }
        
        logger.info("RAG evaluation completed")
        return results
    
    async def evaluate_query_rewriting(self) -> Dict[str, float]:
        """Evaluate query rewriting effectiveness"""
        logger.info("Evaluating query rewriting...")
        
        improvement_scores = []
        
        for query in self.test_queries[:3]:  # Limit for API cost
            # Get baseline results
            baseline_docs = await self.retrieval_system.search(query, RetrievalMethod.HYBRID, top_k=5)
            
            # Get rewritten queries
            rewritten_queries = await self.query_rewriter.rewrite_query(query)
            
            # Evaluate each rewritten query
            best_score = 0
            for rewritten_query in rewritten_queries:
                rewritten_docs = await self.retrieval_system.search(rewritten_query, RetrievalMethod.HYBRID, top_k=5)
                
                if query in self.ground_truth:
                    retrieved_companies = [doc.company_name for doc in rewritten_docs]
                    relevant_companies = self.ground_truth[query]
                    precision = self._calculate_precision(retrieved_companies, relevant_companies)
                    best_score = max(best_score, precision)
            
            # Calculate improvement
            if query in self.ground_truth:
                baseline_companies = [doc.company_name for doc in baseline_docs]
                baseline_precision = self._calculate_precision(baseline_companies, self.ground_truth[query])
                improvement = (best_score - baseline_precision) / max(baseline_precision, 0.1)
                improvement_scores.append(improvement)
        
        return {
            "avg_improvement": sum(improvement_scores) / len(improvement_scores) if improvement_scores else 0,
            "queries_evaluated": len(improvement_scores)
        }
    
    async def evaluate_document_reranking(self) -> Dict[str, float]:
        """Evaluate document re-ranking effectiveness"""
        logger.info("Evaluating document re-ranking...")
        
        improvement_scores = []
        
        for query in self.test_queries[:3]:  # Limit for API cost
            # Get baseline results
            baseline_docs = await self.retrieval_system.search(query, RetrievalMethod.HYBRID, top_k=10)
            
            if len(baseline_docs) < 2:
                continue
            
            # Re-rank documents
            reranked_docs = await self.document_reranker.rerank_documents(query, baseline_docs)
            
            if query in self.ground_truth:
                # Calculate precision for top 5 of both
                baseline_companies = [doc.company_name for doc in baseline_docs[:5]]
                reranked_companies = [doc.company_name for doc in reranked_docs[:5]]
                relevant_companies = self.ground_truth[query]
                
                baseline_precision = self._calculate_precision(baseline_companies, relevant_companies)
                reranked_precision = self._calculate_precision(reranked_companies, relevant_companies)
                
                improvement = (reranked_precision - baseline_precision) / max(baseline_precision, 0.1)
                improvement_scores.append(improvement)
        
        return {
            "avg_improvement": sum(improvement_scores) / len(improvement_scores) if improvement_scores else 0,
            "queries_evaluated": len(improvement_scores)
        }
    
    def _calculate_precision(self, retrieved: List[str], relevant: List[str]) -> float:
        """Calculate precision at k"""
        if not retrieved:
            return 0.0
        
        retrieved_set = set(retrieved)
        relevant_set = set(relevant)
        
        intersection = retrieved_set.intersection(relevant_set)
        return len(intersection) / len(retrieved_set)
    
    def _calculate_recall(self, retrieved: List[str], relevant: List[str]) -> float:
        """Calculate recall at k"""
        if not relevant:
            return 0.0
        
        retrieved_set = set(retrieved)
        relevant_set = set(relevant)
        
        intersection = retrieved_set.intersection(relevant_set)
        return len(intersection) / len(relevant_set)
    
    async def _evaluate_response_relevance(self, query: str, response: str) -> float:
        """Evaluate response relevance using LLM (simplified)"""
        try:
            # For now, return a mock score based on response length and key terms
            # In practice, would use more sophisticated evaluation
            
            query_terms = set(query.lower().split())
            response_terms = set(response.lower().split())
            
            # Simple overlap-based scoring
            overlap = len(query_terms.intersection(response_terms))
            relevance = min(overlap / max(len(query_terms), 1), 1.0)
            
            # Bonus for longer, more detailed responses
            length_bonus = min(len(response) / 500, 0.2)
            
            return min(relevance + length_bonus, 1.0)
            
        except Exception as e:
            logger.error(f"Error evaluating relevance: {e}")
            return 0.5
    
    async def _evaluate_response_accuracy(self, query: str, response: str, 
                                        documents: List[DocumentChunk]) -> float:
        """Evaluate response accuracy based on source documents"""
        try:
            # Check if response mentions companies from retrieved documents
            company_names = [doc.company_name for doc in documents]
            mentioned_companies = []
            
            for company in company_names:
                if company.lower() in response.lower():
                    mentioned_companies.append(company)
            
            # Accuracy based on how many retrieved companies are mentioned
            if company_names:
                accuracy = len(mentioned_companies) / len(company_names)
            else:
                accuracy = 0.0
            
            # Bonus for specific data mentions (capital, location, etc.)
            data_terms = ['capital', 'rupees', '₹', 'registered', 'limited', 'private']
            data_mentions = sum(1 for term in data_terms if term.lower() in response.lower())
            data_bonus = min(data_mentions * 0.1, 0.3)
            
            return min(accuracy + data_bonus, 1.0)
            
        except Exception as e:
            logger.error(f"Error evaluating accuracy: {e}")
            return 0.5
    
    async def run_comprehensive_evaluation(self) -> Dict[str, Any]:
        """Run complete evaluation suite"""
        logger.info("Starting comprehensive evaluation suite...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "retrieval_evaluation": {},
            "rag_evaluation": {},
            "query_rewriting_evaluation": {},
            "document_reranking_evaluation": {}
        }
        
        try:
            # Evaluate retrieval methods
            results["retrieval_evaluation"] = await self.evaluate_retrieval_methods()
            
            # Evaluate RAG approaches
            results["rag_evaluation"] = await self.evaluate_rag_approaches()
            
            # Evaluate query rewriting
            results["query_rewriting_evaluation"] = await self.evaluate_query_rewriting()
            
            # Evaluate document re-ranking
            results["document_reranking_evaluation"] = await self.evaluate_document_reranking()
            
            # Save results
            self._save_results(results)
            
            logger.info("Comprehensive evaluation completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise
    
    def _save_results(self, results: Dict[str, Any]):
        """Save evaluation results to file"""
        try:
            results_dir = Path("evaluation_results")
            results_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = results_dir / f"evaluation_{timestamp}.json"
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Results saved to {results_file}")
            
            # Also save a summary
            self._save_summary(results, results_dir / f"summary_{timestamp}.txt")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def _save_summary(self, results: Dict[str, Any], summary_file: Path):
        """Save evaluation summary"""
        with open(summary_file, 'w') as f:
            f.write("RAG System Evaluation Summary\n")
            f.write("=" * 40 + "\n\n")
            
            # Retrieval evaluation summary
            f.write("Retrieval Method Evaluation:\n")
            f.write("-" * 30 + "\n")
            for method, metrics in results["retrieval_evaluation"].items():
                f.write(f"{method.upper()}:\n")
                f.write(f"  Precision@5: {metrics['precision_at_5']:.3f}\n")
                f.write(f"  Recall@5: {metrics['recall_at_5']:.3f}\n")
                f.write(f"  Avg Response Time: {metrics['avg_response_time_ms']:.1f}ms\n\n")
            
            # RAG evaluation summary
            f.write("RAG Approach Evaluation:\n")
            f.write("-" * 25 + "\n")
            for approach, metrics in results["rag_evaluation"].items():
                f.write(f"{approach.upper()}:\n")
                f.write(f"  Relevance Score: {metrics['relevance_score']:.3f}\n")
                f.write(f"  Accuracy Score: {metrics['accuracy_score']:.3f}\n")
                f.write(f"  Avg Response Time: {metrics['avg_response_time_ms']:.1f}ms\n\n")
            
            # Best practices evaluation
            f.write("Best Practices Evaluation:\n")
            f.write("-" * 27 + "\n")
            f.write(f"Query Rewriting Improvement: {results['query_rewriting_evaluation']['avg_improvement']:.3f}\n")
            f.write(f"Document Re-ranking Improvement: {results['document_reranking_evaluation']['avg_improvement']:.3f}\n")

async def main():
    """Main evaluation entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG System Evaluation Suite")
    parser.add_argument("--eval-type", choices=["retrieval", "rag", "all"], 
                       default="all", help="Type of evaluation to run")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run evaluation
    evaluator = EvaluationSuite()
    
    if args.eval_type == "retrieval":
        results = await evaluator.evaluate_retrieval_methods()
        print("Retrieval Evaluation Results:")
        print(json.dumps(results, indent=2))
    elif args.eval_type == "rag":
        results = await evaluator.evaluate_rag_approaches()
        print("RAG Evaluation Results:")
        print(json.dumps(results, indent=2))
    else:
        results = await evaluator.run_comprehensive_evaluation()
        print("Comprehensive Evaluation Completed!")
        print(f"Results saved with timestamp: {results['timestamp']}")

if __name__ == "__main__":
    asyncio.run(main())