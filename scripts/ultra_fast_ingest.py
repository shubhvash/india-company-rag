#!/usr/bin/env python3
"""
Ultra-fast ingestion - optimized for speed with minimal chunks per company
"""
import sys
import logging
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from tqdm import tqdm

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltraFastIngestion:
    """Ultra-fast ingestion with minimal processing"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.qdrant_client = None
        self.es_client = None
        self.collection_name = "indian_companies"
        self.es_index = "indian_companies"
        self.batch_size = 100  # Larger batches for speed
        self.point_id_counter = int(datetime.now().timestamp() * 1000000)
        
    def initialize_databases(self):
        """Initialize database connections"""
        # Qdrant
        self.qdrant_client = QdrantClient(host="localhost", port=6333, timeout=60.0)
        
        try:
            self.qdrant_client.get_collection(self.collection_name)
            logger.info("Using existing Qdrant collection")
        except:
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info("Created new Qdrant collection")
        
        # Elasticsearch
        self.es_client = Elasticsearch(["http://localhost:9200"])
        
        if not self.es_client.indices.exists(index=self.es_index):
            mapping = {
                "mappings": {
                    "properties": {
                        "company_name": {"type": "text"},
                        "state": {"type": "keyword"},
                        "city": {"type": "keyword"},
                        "industry_classification": {"type": "text"},
                        "full_text": {"type": "text"}
                    }
                }
            }
            self.es_client.indices.create(index=self.es_index, body=mapping)
            logger.info("Created new Elasticsearch index")
    
    def create_minimal_chunk(self, row: pd.Series) -> Dict[str, Any]:
        """Create single minimal chunk per company"""
        company_name = str(row.get('CompanyName', ''))
        state = str(row.get('CompanyStateCode', ''))
        industry = str(row.get('CompanyIndustrialClassification', ''))
        
        # Minimal text for embedding
        text = f"{company_name} {industry} {state}"
        
        return {
            'company_name': company_name,
            'state': state,
            'city': state,  # Use state as city for simplicity
            'industry_classification': industry,
            'full_text': text,
            'chunk_type': 'minimal'
        }
    
    def process_file_ultra_fast(self, csv_path: Path, max_rows: int = None):
        """Process file with maximum speed optimizations"""
        logger.info(f"Ultra-fast processing: {csv_path.name}")
        
        # Read CSV in chunks
        chunk_size = 5000
        total_processed = 0
        
        for chunk_df in pd.read_csv(csv_path, chunksize=chunk_size):
            if max_rows and total_processed >= max_rows:
                break
                
            # Limit chunk if needed
            if max_rows:
                remaining = max_rows - total_processed
                if len(chunk_df) > remaining:
                    chunk_df = chunk_df.head(remaining)
            
            # Process chunk
            chunks = []
            for _, row in chunk_df.iterrows():
                try:
                    chunk = self.create_minimal_chunk(row)
                    chunks.append(chunk)
                except:
                    continue
            
            if chunks:
                # Batch process
                self.index_batch_fast(chunks)
                total_processed += len(chunks)
                
                logger.info(f"Processed {total_processed} companies...")
        
        logger.info(f"Ultra-fast processing completed: {total_processed} companies")
        return total_processed
    
    def index_batch_fast(self, chunks: List[Dict[str, Any]]):
        """Fast batch indexing to both databases"""
        if not chunks:
            return
        
        # Generate embeddings
        texts = [chunk['full_text'] for chunk in chunks]
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False).tolist()
        
        # Index to Qdrant
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            point = PointStruct(
                id=self.point_id_counter,
                vector=embedding,
                payload=chunk
            )
            points.append(point)
            self.point_id_counter += 1
        
        try:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception as e:
            logger.error(f"Qdrant indexing failed: {e}")
        
        # Index to Elasticsearch
        actions = []
        for chunk in chunks:
            actions.append({
                "_index": self.es_index,
                "_source": chunk
            })
        
        try:
            bulk(self.es_client, actions)
        except Exception as e:
            logger.error(f"Elasticsearch indexing failed: {e}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ultra-fast company data ingestion")
    parser.add_argument("--max-companies", type=int, default=10000, 
                       help="Maximum companies to process (default: 10000)")
    parser.add_argument("--sample-only", action="store_true",
                       help="Process only 1000 companies for testing")
    
    args = parser.parse_args()
    
    if args.sample_only:
        max_companies = 1000
        logger.info("🔥 SAMPLE MODE: Processing 1000 companies only")
    else:
        max_companies = args.max_companies
        logger.info(f"🚀 ULTRA-FAST MODE: Processing up to {max_companies} companies")
    
    pipeline = UltraFastIngestion()
    pipeline.initialize_databases()
    
    # Find smallest CSV file
    dataset_path = Path("dataset")
    csv_files = sorted(dataset_path.glob("*.csv"), key=lambda x: x.stat().st_size)
    
    if not csv_files:
        logger.error("No CSV files found")
        return
    
    # Start with smallest file
    csv_file = csv_files[0]
    logger.info(f"Processing: {csv_file.name}")
    
    total_processed = pipeline.process_file_ultra_fast(csv_file, max_companies)
    
    # Verify results
    qdrant_count = pipeline.qdrant_client.get_collection('indian_companies').points_count
    es_count = pipeline.es_client.count(index='indian_companies')['count']
    
    logger.info(f"🎉 COMPLETED!")
    logger.info(f"📊 Final counts - Qdrant: {qdrant_count}, Elasticsearch: {es_count}")
    logger.info(f"⚡ Processed {total_processed} companies in ultra-fast mode")

if __name__ == "__main__":
    main()