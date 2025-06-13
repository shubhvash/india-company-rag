#!/usr/bin/env python3
"""
Automated Data Ingestion Pipeline for Indian Company Intelligence RAG System

This script automatically processes all CSV files in the dataset directory,
supporting easy addition of new state data by simply placing CSV files
in the dataset folder.

Features:
- Automatic discovery of CSV files in dataset directory
- Extensible to handle additional states
- Document chunking and embedding generation
- Dual indexing: Qdrant (vector) + Elasticsearch (text)
- Progress tracking and error handling
"""

import os
import sys
import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import asyncio
from datetime import datetime
import json
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing
from functools import partial

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from elasticsearch import Elasticsearch
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataIngestionPipeline:
    """Extensible data ingestion pipeline for Indian company data"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.qdrant_client = None
        self.es_client = None
        self.collection_name = "indian_companies"
        self.es_index = "indian_companies"
        self.batch_size = 50  # Much smaller batch size for reliability
        self.max_workers = min(multiprocessing.cpu_count(), 8)  # Limit workers
        self.point_id_counter = int(datetime.now().timestamp() * 1000000)  # Global ID counter
        
    def initialize_databases(self):
        """Initialize connections to Qdrant and Elasticsearch"""
        try:
            # Initialize Qdrant with timeout
            self.qdrant_client = QdrantClient(
                host=os.getenv("QDRANT_HOST", "localhost"),
                port=int(os.getenv("QDRANT_PORT", "6333")),
                timeout=120.0  # Increase timeout to 2 minutes
            )
            
            # Create collection if it doesn't exist
            try:
                self.qdrant_client.get_collection(self.collection_name)
                logger.info(f"Collection {self.collection_name} already exists")
            except:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                logger.info(f"Created collection {self.collection_name}")
            
            # Initialize Elasticsearch
            self.es_client = Elasticsearch([
                os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
            ])
            
            # Create index if it doesn't exist
            if not self.es_client.indices.exists(index=self.es_index):
                mapping = {
                    "mappings": {
                        "properties": {
                            "company_name": {"type": "text", "analyzer": "standard"},
                            "company_category": {"type": "keyword"},
                            "industry_classification": {"type": "text"},
                            "state": {"type": "keyword"},
                            "city": {"type": "keyword"},
                            "authorized_capital": {"type": "long"},
                            "paid_up_capital": {"type": "long"},
                            "registration_date": {"type": "date"},
                            "full_text": {"type": "text", "analyzer": "standard"},
                            "address": {"type": "text"},
                            "company_status": {"type": "keyword"},
                            "listing_status": {"type": "keyword"}
                        }
                    }
                }
                self.es_client.indices.create(index=self.es_index, body=mapping)
                logger.info(f"Created Elasticsearch index {self.es_index}")
            
        except Exception as e:
            logger.error(f"Failed to initialize databases: {e}")
            raise
    
    def discover_csv_files(self, dataset_dir: str) -> List[Path]:
        """Discover all CSV files in the dataset directory"""
        dataset_path = Path(dataset_dir)
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
        
        csv_files = list(dataset_path.glob("*.csv"))
        logger.info(f"Discovered {len(csv_files)} CSV files: {[f.name for f in csv_files]}")
        return csv_files
    
    def load_and_validate_csv(self, csv_path: Path) -> pd.DataFrame:
        """Load and validate CSV file structure"""
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} records from {csv_path.name}")
            
            # Required columns for processing
            required_columns = [
                'CIN', 'CompanyName', 'CompanyCategory', 
                'AuthorizedCapital', 'PaidupCapital',
                'Registered_Office_Address', 'CompanyStateCode',
                'CompanyIndustrialClassification'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.warning(f"Missing columns in {csv_path.name}: {missing_columns}")
            
            # Clean and standardize data
            df = self.clean_dataframe(df)
            return df
            
        except Exception as e:
            logger.error(f"Failed to load {csv_path.name}: {e}")
            raise
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize dataframe"""
        # Handle missing values
        df = df.fillna('')
        
        # Standardize column names
        column_mapping = {
            'CompanyName': 'company_name',
            'CompanyCategory': 'company_category',
            'CompanyIndustrialClassification': 'industry_classification',
            'CompanyStateCode': 'state',
            'AuthorizedCapital': 'authorized_capital',
            'PaidupCapital': 'paid_up_capital',
            'Registered_Office_Address': 'address',
            'CompanyStatus': 'company_status',
            'Listingstatus': 'listing_status',
            'CompanyRegistrationdate_date': 'registration_date'
        }
        
        # Rename columns that exist
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # Convert numeric columns
        numeric_columns = ['authorized_capital', 'paid_up_capital']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Extract city from address
        if 'address' in df.columns:
            df['city'] = df['address'].str.extract(r',([^,]+),')[0].str.strip()
            df['city'] = df['city'].fillna('Unknown')
        
        return df
    
    def create_document_chunks(self, row: pd.Series) -> List[Dict[str, Any]]:
        """Create searchable document chunks from company record"""
        base_info = {
            'cin': row.get('CIN', ''),
            'company_name': row.get('company_name', ''),
            'state': row.get('state', ''),
            'city': row.get('city', ''),
            'company_category': row.get('company_category', ''),
            'industry_classification': row.get('industry_classification', ''),
            'authorized_capital': float(row.get('authorized_capital', 0)),
            'paid_up_capital': float(row.get('paid_up_capital', 0)),
            'address': row.get('address', ''),
            'company_status': row.get('company_status', ''),
            'listing_status': row.get('listing_status', '')
        }
        
        # Create multiple document chunks for different search scenarios
        chunks = []
        
        # Main company profile chunk
        main_text = f"""
        Company: {base_info['company_name']}
        State: {base_info['state']}
        City: {base_info['city']}
        Category: {base_info['company_category']}
        Industry: {base_info['industry_classification']}
        Authorized Capital: ₹{base_info['authorized_capital']:,.0f}
        Paid-up Capital: ₹{base_info['paid_up_capital']:,.0f}
        Status: {base_info['company_status']}
        Address: {base_info['address']}
        """.strip()
        
        chunks.append({
            **base_info,
            'chunk_type': 'company_profile',
            'full_text': main_text
        })
        
        # Financial information chunk
        if base_info['authorized_capital'] > 0 or base_info['paid_up_capital'] > 0:
            financial_text = f"""
            {base_info['company_name']} Financial Details:
            Authorized Capital: ₹{base_info['authorized_capital']:,.0f}
            Paid-up Capital: ₹{base_info['paid_up_capital']:,.0f}
            Capital Utilization: {(base_info['paid_up_capital']/max(base_info['authorized_capital'], 1)*100):.1f}%
            State: {base_info['state']}
            Industry: {base_info['industry_classification']}
            """.strip()
            
            chunks.append({
                **base_info,
                'chunk_type': 'financial_info',
                'full_text': financial_text
            })
        
        # Location and industry chunk
        location_text = f"""
        {base_info['industry_classification']} company in {base_info['city']}, {base_info['state']}
        Company Name: {base_info['company_name']}
        Business Category: {base_info['company_category']}
        Registration Status: {base_info['company_status']}
        """.strip()
        
        chunks.append({
            **base_info,
            'chunk_type': 'location_industry',
            'full_text': location_text
        })
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text chunks with batch processing"""
        # Process in larger batches for better GPU utilization
        batch_size = 64
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.embedding_model.encode(
                batch_texts, 
                show_progress_bar=False,
                batch_size=batch_size,
                normalize_embeddings=True
            ).tolist()
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    def index_to_qdrant(self, chunks: List[Dict[str, Any]]):
        """Index document chunks to Qdrant vector database"""
        if not chunks:
            return
        
        texts = [chunk['full_text'] for chunk in chunks]
        embeddings = self.generate_embeddings(texts)
        
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=self.point_id_counter,
                vector=embedding,
                payload=chunk
            )
            points.append(point)
            self.point_id_counter += 1
        
        # Batch upsert to Qdrant with larger batches
        for i in range(0, len(points), self.batch_size):
            batch = points[i:i + self.batch_size]
            try:
                result = self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                logger.debug(f"Qdrant batch {i//self.batch_size + 1}: {len(batch)} points indexed")
            except Exception as e:
                logger.error(f"Failed to index Qdrant batch {i//self.batch_size + 1}: {e}")
                raise
    
    def index_to_elasticsearch(self, chunks: List[Dict[str, Any]]):
        """Index document chunks to Elasticsearch"""
        if not chunks:
            return
        
        actions = []
        for chunk in chunks:
            action = {
                "_index": self.es_index,
                "_source": chunk
            }
            actions.append(action)
        
        # Bulk index to Elasticsearch
        if actions:
            from elasticsearch.helpers import bulk
            bulk(self.es_client, actions)
    
    def process_batch_of_rows(self, rows_batch: List[pd.Series]) -> List[Dict[str, Any]]:
        """Process a batch of rows to create document chunks"""
        batch_chunks = []
        for row in rows_batch:
            try:
                chunks = self.create_document_chunks(row)
                batch_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Error processing row: {e}")
                continue
        return batch_chunks
    
    def process_csv_file(self, csv_path: Path):
        """Process a single CSV file with parallel processing"""
        logger.info(f"Processing {csv_path.name}...")
        
        df = self.load_and_validate_csv(csv_path)
        
        # Split dataframe into batches for parallel processing
        row_batch_size = 1000
        row_batches = []
        for i in range(0, len(df), row_batch_size):
            batch_df = df.iloc[i:i + row_batch_size]
            row_batches.append([row for _, row in batch_df.iterrows()])
        
        all_chunks = []
        
        # Process batches in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            with tqdm(total=len(df), desc=f"Processing {csv_path.name}") as pbar:
                # Submit all batch processing jobs
                future_to_batch = {
                    executor.submit(self.process_batch_of_rows, batch): batch 
                    for batch in row_batches
                }
                
                # Collect results as they complete
                for future in future_to_batch:
                    try:
                        batch_chunks = future.result()
                        all_chunks.extend(batch_chunks)
                        pbar.update(len(future_to_batch[future]))
                    except Exception as e:
                        logger.error(f"Error processing batch: {e}")
                        pbar.update(len(future_to_batch[future]))
        
        # Index to both databases sequentially to avoid threading issues
        logger.info(f"Indexing {len(all_chunks)} chunks from {csv_path.name}")
        
        # Index to Qdrant first
        logger.info("Indexing to Qdrant...")
        self.index_to_qdrant(all_chunks)
        
        # Then index to Elasticsearch
        logger.info("Indexing to Elasticsearch...")
        self.index_to_elasticsearch(all_chunks)
        
        logger.info(f"Completed processing {csv_path.name}")
        return len(all_chunks)
    
    def run_pipeline(self, dataset_dir: str = "dataset"):
        """Run the complete ingestion pipeline"""
        logger.info("Starting Indian Company Data Ingestion Pipeline")
        
        try:
            # Initialize databases
            self.initialize_databases()
            
            # Discover CSV files
            csv_files = self.discover_csv_files(dataset_dir)
            if not csv_files:
                logger.warning("No CSV files found in dataset directory")
                return
            
            # Process each CSV file
            total_chunks = 0
            for csv_file in csv_files:
                chunks_processed = self.process_csv_file(csv_file)
                total_chunks += chunks_processed
            
            logger.info(f"Pipeline completed successfully!")
            logger.info(f"Total chunks processed: {total_chunks}")
            logger.info(f"Files processed: {len(csv_files)}")
            
            # Log statistics
            self.log_ingestion_stats()
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def log_ingestion_stats(self):
        """Log ingestion statistics"""
        try:
            # Qdrant stats
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            qdrant_count = collection_info.points_count
            
            # Elasticsearch stats
            es_stats = self.es_client.count(index=self.es_index)
            es_count = es_stats['count']
            
            logger.info(f"Ingestion Statistics:")
            logger.info(f"  Qdrant documents: {qdrant_count}")
            logger.info(f"  Elasticsearch documents: {es_count}")
            
        except Exception as e:
            logger.error(f"Failed to get ingestion stats: {e}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Indian Company Data Ingestion Pipeline")
    parser.add_argument("--dataset-dir", default="dataset", 
                       help="Directory containing CSV files (default: dataset)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the pipeline
    pipeline = DataIngestionPipeline()
    pipeline.run_pipeline(args.dataset_dir)

if __name__ == "__main__":
    main()