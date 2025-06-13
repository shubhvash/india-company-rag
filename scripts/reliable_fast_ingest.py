#!/usr/bin/env python3
"""
Reliable fast ingestion - optimized for speed with proper timeout handling
"""
import sys
import logging
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from tqdm import tqdm
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReliableFastIngestion:
    """Reliable fast ingestion with proper error handling"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.qdrant_client = None
        self.es_client = None
        self.collection_name = "indian_companies"
        self.es_index = "indian_companies"
        self.qdrant_batch_size = 25  # Smaller for Qdrant stability
        self.es_batch_size = 100     # Larger for ES efficiency
        self.point_id_counter = int(datetime.now().timestamp() * 1000000)
        
    def initialize_databases(self):
        """Initialize database connections with proper timeouts"""
        # Qdrant with longer timeout
        self.qdrant_client = QdrantClient(
            host="localhost", 
            port=6333, 
            timeout=300.0  # 5 minutes
        )
        
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
                        "company_origin": {"type": "keyword"},  # Indian/Foreign
                        "nic_code": {"type": "keyword"},
                        "industry_classification": {"type": "text", "analyzer": "standard"},
                        
                        # Search and system fields
                        "full_text": {"type": "text", "analyzer": "standard"},
                        "chunk_type": {"type": "keyword"}
                    }
                }
            }
            self.es_client.indices.create(index=self.es_index, body=mapping)
            logger.info("Created new Elasticsearch index")
    
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
            # Try to standardize date format
            try:
                from datetime import datetime
                # Try different date formats
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
        city = state  # Default to state
        if registered_office_address and ',' in registered_office_address:
            parts = [p.strip() for p in registered_office_address.split(',') if p.strip()]
            if len(parts) > 2:
                # Try to get city from address parts
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
    
    def index_to_qdrant_safe(self, chunks: List[Dict[str, Any]]) -> int:
        """Safely index to Qdrant with retry logic"""
        if not chunks:
            return 0
        
        # Generate embeddings
        texts = [chunk['full_text'] for chunk in chunks]
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False).tolist()
        
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
        
        # Index in small batches with retry
        indexed_count = 0
        for i in range(0, len(points), self.qdrant_batch_size):
            batch = points[i:i + self.qdrant_batch_size]
            
            for attempt in range(3):  # Retry up to 3 times
                try:
                    self.qdrant_client.upsert(
                        collection_name=self.collection_name,
                        points=batch
                    )
                    indexed_count += len(batch)
                    break
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        logger.error(f"Qdrant batch failed after 3 attempts: {e}")
                    else:
                        logger.warning(f"Qdrant attempt {attempt + 1} failed: {e}, retrying...")
                        time.sleep(1)  # Wait before retry
        
        return indexed_count
    
    def index_to_es_safe(self, chunks: List[Dict[str, Any]]) -> int:
        """Safely index to Elasticsearch"""
        if not chunks:
            return 0
        
        actions = []
        for chunk in chunks:
            actions.append({
                "_index": self.es_index,
                "_source": chunk
            })
        
        try:
            success_count, failed = bulk(self.es_client, actions, chunk_size=self.es_batch_size)
            if failed:
                logger.warning(f"ES: {len(failed)} documents failed to index")
            return success_count
        except Exception as e:
            logger.error(f"Elasticsearch indexing failed: {e}")
            return 0
    
    def process_file_reliably(self, csv_path: Path, max_rows: int = None):
        """Process file with reliable error handling"""
        logger.info(f"Reliable processing: {csv_path.name}")
        
        total_processed = 0
        total_qdrant = 0
        total_es = 0
        
        # Process in chunks
        chunk_size = 1000
        
        try:
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
                        chunk = self.create_comprehensive_chunk(row)
                        chunks.append(chunk)
                    except Exception as e:
                        logger.debug(f"Skipping row due to error: {e}")
                        continue
                
                if chunks:
                    # Index to both databases
                    qdrant_count = self.index_to_qdrant_safe(chunks)
                    es_count = self.index_to_es_safe(chunks)
                    
                    total_processed += len(chunks)
                    total_qdrant += qdrant_count
                    total_es += es_count
                    
                    logger.info(f"Processed {total_processed} companies (Q:{total_qdrant}, ES:{total_es})")
                
        except Exception as e:
            logger.error(f"File processing error: {e}")
        
        logger.info(f"✅ Completed: {total_processed} processed, Qdrant: {total_qdrant}, ES: {total_es}")
        return total_processed, total_qdrant, total_es

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reliable fast company data ingestion")
    parser.add_argument("--max-companies", type=int, default=10000, 
                       help="Maximum companies to process (default: 10000)")
    parser.add_argument("--sample-only", action="store_true",
                       help="Process only 2000 companies for testing")
    
    args = parser.parse_args()
    
    if args.sample_only:
        max_companies = 2000
        logger.info("🔥 SAMPLE MODE: Processing 2000 companies")
    else:
        max_companies = args.max_companies
        logger.info(f"🚀 RELIABLE FAST MODE: Processing up to {max_companies} companies")
    
    pipeline = ReliableFastIngestion()
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
    
    start_time = time.time()
    total_processed, total_qdrant, total_es = pipeline.process_file_reliably(csv_file, max_companies)
    elapsed_time = time.time() - start_time
    
    # Final verification
    try:
        qdrant_count = pipeline.qdrant_client.get_collection('indian_companies').points_count
        es_count = pipeline.es_client.count(index='indian_companies')['count']
    except:
        qdrant_count = total_qdrant
        es_count = total_es
    
    logger.info(f"🎉 COMPLETED IN {elapsed_time:.1f} SECONDS!")
    logger.info(f"📊 Final counts - Qdrant: {qdrant_count}, Elasticsearch: {es_count}")
    logger.info(f"⚡ Processing rate: {total_processed/elapsed_time:.1f} companies/second")

if __name__ == "__main__":
    main()