#!/usr/bin/env python3
"""
Turbo-fast ingestion with GPU acceleration, larger batches, and parallel processing
"""
import sys
import logging
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from tqdm import tqdm
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import torch
import multiprocessing as mp

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, parallel_bulk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TurboFastIngestion:
    """Turbo-fast ingestion with all optimizations"""
    
    def __init__(self):
        # GPU acceleration
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"🚀 Using device: {self.device}")
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        if self.device == 'cuda':
            self.embedding_model = self.embedding_model.to(self.device)
            logger.info("✅ GPU acceleration enabled")
        
        self.qdrant_client = None
        self.es_client = None
        self.collection_name = "indian_companies"
        self.es_index = "indian_companies"
        
        # Optimized batch sizes
        self.qdrant_batch_size = 500 if self.device == 'cuda' else 100
        self.es_batch_size = 2000 if self.device == 'cuda' else 500
        self.embedding_batch_size = 512 if self.device == 'cuda' else 128
        
        self.point_id_counter = int(datetime.now().timestamp() * 1000000)
        
        logger.info(f"📊 Batch sizes - Qdrant: {self.qdrant_batch_size}, ES: {self.es_batch_size}, Embeddings: {self.embedding_batch_size}")
        
    def initialize_databases(self):
        """Initialize database connections with optimized settings"""
        # Qdrant with gRPC for better performance
        try:
            self.qdrant_client = QdrantClient(
                host="localhost", 
                port=6334,  # Try gRPC port first
                timeout=300.0,
                prefer_grpc=True
            )
            logger.info("✅ Using Qdrant gRPC connection")
        except:
            # Fallback to HTTP
            self.qdrant_client = QdrantClient(
                host="localhost", 
                port=6333, 
                timeout=300.0
            )
            logger.info("✅ Using Qdrant HTTP connection")
        
        try:
            self.qdrant_client.get_collection(self.collection_name)
            logger.info("Using existing Qdrant collection")
        except:
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info("Created new Qdrant collection")
        
        # Elasticsearch with optimized settings
        self.es_client = Elasticsearch(
            ["http://localhost:9200"],
            timeout=300,
            max_retries=3,
            retry_on_timeout=True
        )
        
        if not self.es_client.indices.exists(index=self.es_index):
            mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,  # No replicas for faster indexing
                    "refresh_interval": "30s",  # Less frequent refresh
                    "index.translog.durability": "async"  # Faster writes
                },
                "mappings": {
                    "properties": {
                        # Core company information
                        "cin": {"type": "keyword"},
                        "company_name": {"type": "text", "analyzer": "standard"},
                        "company_roc_code": {"type": "keyword"},
                        "company_category": {"type": "keyword"},
                        "company_sub_category": {"type": "keyword"},
                        "company_class": {"type": "keyword"},
                        
                        # Financial information
                        "authorized_capital": {"type": "long"},
                        "paid_up_capital": {"type": "long"},
                        "capital_utilization_ratio": {"type": "float"},
                        
                        # Dates
                        "registration_date": {"type": "date", "format": "yyyy-MM-dd||dd/MM/yyyy||dd-MM-yyyy"},
                        
                        # Location
                        "state": {"type": "keyword"},
                        "city": {"type": "keyword"},
                        "registered_office_address": {"type": "text"},
                        
                        # Status and classification
                        "listing_status": {"type": "keyword"},
                        "company_status": {"type": "keyword"},
                        "company_origin": {"type": "keyword"},
                        "nic_code": {"type": "keyword"},
                        "industry_classification": {"type": "text", "analyzer": "standard"},
                        
                        # Search and system fields
                        "full_text": {"type": "text", "analyzer": "standard"},
                        "chunk_type": {"type": "keyword"}
                    }
                }
            }
            self.es_client.indices.create(index=self.es_index, body=mapping)
            logger.info("Created new optimized Elasticsearch index")
    
    def create_comprehensive_chunk(self, row: pd.Series) -> Dict[str, Any]:
        """Create comprehensive chunk with all available company data"""
        
        # Core company information
        cin = str(row.get('CIN', '')).strip()
        company_name = str(row.get('CompanyName', '')).strip()
        company_roc_code = str(row.get('CompanyROCcode', '')).strip()
        company_category = str(row.get('CompanyCategory', '')).strip()
        company_sub_category = str(row.get('CompanySubCategory', '')).strip()
        company_class = str(row.get('CompanyClass', '')).strip()
        
        # Financial information
        try:
            authorized_capital = float(row.get('AuthorizedCapital', 0)) if pd.notna(row.get('AuthorizedCapital')) else 0
        except (ValueError, TypeError):
            authorized_capital = 0
            
        try:
            paid_up_capital = float(row.get('PaidupCapital', 0)) if pd.notna(row.get('PaidupCapital')) else 0
        except (ValueError, TypeError):
            paid_up_capital = 0
        
        # Calculate capital utilization ratio
        capital_utilization_ratio = 0
        if authorized_capital > 0:
            capital_utilization_ratio = round(paid_up_capital / authorized_capital * 100, 2)
        
        # Registration date
        registration_date = str(row.get('CompanyRegistrationdate_date', '')).strip()
        if registration_date and registration_date.lower() not in ['', 'nan', 'null']:
            try:
                from datetime import datetime
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        parsed_date = datetime.strptime(registration_date, fmt)
                        registration_date = parsed_date.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
            except:
                pass
        else:
            registration_date = None
        
        # Location information
        state = str(row.get('CompanyStateCode', '')).strip()
        registered_office_address = str(row.get('Registered_Office_Address', '')).strip()
        
        # Extract city from address
        city = state
        if registered_office_address and ',' in registered_office_address:
            parts = [p.strip() for p in registered_office_address.split(',') if p.strip()]
            if len(parts) > 2:
                city = parts[-3] if len(parts) > 3 else parts[0]
            elif len(parts) > 1:
                city = parts[0]
        
        # Status and classification
        listing_status = str(row.get('Listingstatus', '')).strip()
        company_status = str(row.get('CompanyStatus', '')).strip()
        company_origin = str(row.get('CompanyIndian/Foreign Company', '')).strip()
        nic_code = str(row.get('nic_code', '')).strip()
        industry_classification = str(row.get('CompanyIndustrialClassification', '')).strip()
        
        # Create comprehensive text for embedding
        text_parts = [
            company_name,
            industry_classification,
            company_category,
            state,
            city,
            company_status
        ]
        text = ' '.join([part for part in text_parts if part and part.lower() != 'nan'])
        
        return {
            # Core information
            'cin': cin,
            'company_name': company_name,
            'company_roc_code': company_roc_code,
            'company_category': company_category,
            'company_sub_category': company_sub_category,
            'company_class': company_class,
            
            # Financial
            'authorized_capital': int(authorized_capital),
            'paid_up_capital': int(paid_up_capital),
            'capital_utilization_ratio': capital_utilization_ratio,
            
            # Dates
            'registration_date': registration_date,
            
            # Location
            'state': state,
            'city': city,
            'registered_office_address': registered_office_address,
            
            # Status and classification
            'listing_status': listing_status,
            'company_status': company_status,
            'company_origin': company_origin,
            'nic_code': nic_code,
            'industry_classification': industry_classification,
            
            # Search fields
            'full_text': text,
            'chunk_type': 'comprehensive'
        }
    
    def generate_embeddings_fast(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with GPU acceleration and optimal batching"""
        all_embeddings = []
        
        for i in range(0, len(texts), self.embedding_batch_size):
            batch_texts = texts[i:i + self.embedding_batch_size]
            batch_embeddings = self.embedding_model.encode(
                batch_texts,
                device=self.device,
                show_progress_bar=False,
                convert_to_tensor=False,
                normalize_embeddings=True
            )
            all_embeddings.extend(batch_embeddings.tolist())
        
        return all_embeddings
    
    def index_to_qdrant_turbo(self, chunks: List[Dict[str, Any]]) -> int:
        """Turbo Qdrant indexing with larger batches"""
        if not chunks:
            return 0
        
        # Generate embeddings in optimized batches
        texts = [chunk['full_text'] for chunk in chunks]
        embeddings = self.generate_embeddings_fast(texts)
        
        # Create points
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            point = PointStruct(
                id=self.point_id_counter,
                vector=embedding,
                payload=chunk
            )
            points.append(point)
            self.point_id_counter += 1
        
        # Index in larger batches
        indexed_count = 0
        for i in range(0, len(points), self.qdrant_batch_size):
            batch = points[i:i + self.qdrant_batch_size]
            
            try:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                    wait=False  # Don't wait for completion
                )
                indexed_count += len(batch)
            except Exception as e:
                logger.warning(f"Qdrant batch failed: {e}, retrying smaller batch...")
                # Retry with smaller batch
                for point in batch:
                    try:
                        self.qdrant_client.upsert(
                            collection_name=self.collection_name,
                            points=[point]
                        )
                        indexed_count += 1
                    except:
                        continue
        
        return indexed_count
    
    def index_to_es_turbo(self, chunks: List[Dict[str, Any]]) -> int:
        """Turbo Elasticsearch indexing with parallel bulk"""
        if not chunks:
            return 0
        
        def doc_generator():
            for chunk in chunks:
                yield {
                    "_index": self.es_index,
                    "_source": chunk
                }
        
        try:
            # Use parallel bulk for faster indexing
            success_count = 0
            for success, info in parallel_bulk(
                self.es_client, 
                doc_generator(), 
                chunk_size=self.es_batch_size,
                thread_count=4,
                max_chunk_bytes=10485760  # 10MB chunks
            ):
                if success:
                    success_count += 1
                else:
                    logger.debug(f"ES indexing failed: {info}")
            
            return success_count
        except Exception as e:
            logger.error(f"Elasticsearch parallel indexing failed: {e}")
            # Fallback to regular bulk
            try:
                actions = [{"_index": self.es_index, "_source": chunk} for chunk in chunks]
                success_count, failed = bulk(self.es_client, actions, chunk_size=self.es_batch_size)
                return success_count
            except:
                return 0
    
    def process_chunk_batch(self, chunk_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Process a chunk of DataFrame into company documents"""
        chunks = []
        for _, row in chunk_df.iterrows():
            try:
                chunk = self.create_comprehensive_chunk(row)
                chunks.append(chunk)
            except Exception as e:
                logger.debug(f"Skipping row due to error: {e}")
                continue
        return chunks
    
    def process_file_turbo(self, csv_path: Path, max_rows: int = None):
        """Process file with all turbo optimizations"""
        logger.info(f"🚀 Turbo processing: {csv_path.name}")
        
        total_processed = 0
        total_qdrant = 0
        total_es = 0
        
        # Larger chunk size for better throughput
        chunk_size = 5000 if self.device == 'cuda' else 2000
        
        try:
            # Use ThreadPoolExecutor for I/O bound operations
            with ThreadPoolExecutor(max_workers=4) as executor:
                for chunk_df in pd.read_csv(csv_path, chunksize=chunk_size):
                    if max_rows and total_processed >= max_rows:
                        break
                        
                    # Limit chunk if needed
                    if max_rows:
                        remaining = max_rows - total_processed
                        if len(chunk_df) > remaining:
                            chunk_df = chunk_df.head(remaining)
                    
                    # Process chunk in parallel
                    chunks = self.process_chunk_batch(chunk_df)
                    
                    if chunks:
                        # Submit both indexing operations to thread pool
                        qdrant_future = executor.submit(self.index_to_qdrant_turbo, chunks)
                        es_future = executor.submit(self.index_to_es_turbo, chunks)
                        
                        # Get results
                        qdrant_count = qdrant_future.result()
                        es_count = es_future.result()
                        
                        total_processed += len(chunks)
                        total_qdrant += qdrant_count
                        total_es += es_count
                        
                        rate = total_processed / (time.time() - self.start_time) if hasattr(self, 'start_time') else 0
                        logger.info(f"⚡ Processed {total_processed} companies (Q:{total_qdrant}, ES:{total_es}) - Rate: {rate:.0f}/sec")
                
        except Exception as e:
            logger.error(f"File processing error: {e}")
        
        logger.info(f"🎉 Turbo completed: {total_processed} processed, Qdrant: {total_qdrant}, ES: {total_es}")
        return total_processed, total_qdrant, total_es

def process_file_worker(args):
    """Worker function for multiprocessing"""
    csv_path, max_rows_per_file = args
    pipeline = TurboFastIngestion()
    pipeline.initialize_databases()
    return pipeline.process_file_turbo(csv_path, max_rows_per_file)

def main():
    """Main function with all optimizations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Turbo-fast company data ingestion with GPU acceleration")
    parser.add_argument("--max-companies", type=int, default=50000, 
                       help="Maximum companies to process (default: 50000)")
    parser.add_argument("--sample-only", action="store_true",
                       help="Process only 2000 companies for testing")
    parser.add_argument("--all-data", action="store_true",
                       help="Process ALL data from all CSV files")
    parser.add_argument("--parallel-files", action="store_true",
                       help="Process multiple CSV files in parallel")
    
    args = parser.parse_args()
    
    # Setup
    if args.sample_only:
        max_companies = 2000
        logger.info("🔥 TURBO SAMPLE MODE: Processing 2000 companies")
    elif args.all_data:
        max_companies = None
        logger.info("🌍 TURBO ALL DATA MODE: Processing ALL companies")
        try:
            confirm = input("🤔 Continue with turbo all-data ingestion? (y/n): ").lower().strip()
            if confirm not in ['y', 'yes']:
                logger.info("⏭️  Turbo all-data ingestion cancelled")
                return
        except KeyboardInterrupt:
            logger.info("\n⏭️  Turbo all-data ingestion cancelled")
            return
    else:
        max_companies = args.max_companies
        logger.info(f"🚀 TURBO FAST MODE: Processing up to {max_companies} companies")
    
    pipeline = TurboFastIngestion()
    pipeline.initialize_databases()
    pipeline.start_time = time.time()
    
    # Find CSV files
    dataset_path = Path("dataset")
    csv_files = sorted(dataset_path.glob("*.csv"), key=lambda x: x.stat().st_size)
    
    if not csv_files:
        logger.error("❌ No CSV files found")
        return
    
    start_time = time.time()
    
    # Process based on mode
    if args.all_data and args.parallel_files and len(csv_files) > 1:
        # Parallel file processing for all-data mode
        logger.info(f"🔥 PARALLEL MODE: Processing {len(csv_files)} files simultaneously")
        max_per_file = None
        
        file_args = [(csv_file, max_per_file) for csv_file in csv_files]
        
        with ProcessPoolExecutor(max_workers=min(len(csv_files), mp.cpu_count())) as executor:
            results = list(executor.map(process_file_worker, file_args))
        
        total_processed = sum(r[0] for r in results)
        total_qdrant = sum(r[1] for r in results)
        total_es = sum(r[2] for r in results)
        
    elif args.all_data:
        # Sequential all-data processing
        logger.info(f"📁 Processing ALL {len(csv_files)} CSV files sequentially:")
        total_processed = 0
        total_qdrant = 0
        total_es = 0
        
        for i, csv_file in enumerate(csv_files, 1):
            logger.info(f"🔄 Processing file {i}/{len(csv_files)}: {csv_file.name}")
            processed, qdrant, es = pipeline.process_file_turbo(csv_file, None)
            total_processed += processed
            total_qdrant += qdrant
            total_es += es
            logger.info(f"✅ File {i} complete: +{processed} companies (Total: {total_processed})")
    
    else:
        # Single file processing
        csv_file = csv_files[0]
        logger.info(f"📁 Processing: {csv_file.name}")
        total_processed, total_qdrant, total_es = pipeline.process_file_turbo(csv_file, max_companies)
    
    elapsed_time = time.time() - start_time
    
    # Final verification with ES refresh
    try:
        # Force Elasticsearch refresh to make documents searchable
        pipeline.es_client.indices.refresh(index='indian_companies')
        time.sleep(1)  # Brief wait for refresh
        
        qdrant_count = pipeline.qdrant_client.get_collection('indian_companies').points_count
        es_count = pipeline.es_client.count(index='indian_companies')['count']
    except Exception as e:
        logger.warning(f"Final verification failed: {e}")
        qdrant_count = total_qdrant
        es_count = total_es
    
    # Results
    if args.all_data:
        logger.info(f"🎉 TURBO ALL-DATA INGESTION COMPLETED!")
        logger.info(f"⏱️  Total time: {elapsed_time/60:.1f} minutes ({elapsed_time:.1f} seconds)")
    else:
        logger.info(f"🎉 TURBO INGESTION COMPLETED IN {elapsed_time:.1f} SECONDS!")
    
    logger.info(f"📊 Final counts - Qdrant: {qdrant_count}, Elasticsearch: {es_count}")
    logger.info(f"⚡ Processing rate: {total_processed/elapsed_time:.1f} companies/second")
    
    # Performance metrics
    if pipeline.device == 'cuda':
        logger.info(f"🚀 GPU acceleration provided significant speedup!")
    
    logger.info(f"🎯 Turbo system ready with {total_processed} companies!")

if __name__ == "__main__":
    main()