#!/usr/bin/env python3
"""
Quick sample data ingestion - processes only 1000 companies for testing
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.ingest_data import DataIngestionPipeline
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def quick_sample_ingestion():
    """Ingest only a small sample for quick testing"""
    
    pipeline = DataIngestionPipeline()
    pipeline.initialize_databases()
    
    # Find the smallest CSV file
    dataset_path = Path("dataset")
    csv_files = list(dataset_path.glob("*.csv"))
    
    if not csv_files:
        logger.error("No CSV files found in dataset directory")
        return
    
    # Use Andhra Pradesh (smallest file)
    sample_file = None
    for csv_file in csv_files:
        if "andhra" in csv_file.name.lower():
            sample_file = csv_file
            break
    
    if not sample_file:
        sample_file = csv_files[0]  # Use first file if Andhra Pradesh not found
    
    logger.info(f"Using sample file: {sample_file.name}")
    
    # Read only first 1000 rows
    df = pd.read_csv(sample_file).head(1000)
    logger.info(f"Processing {len(df)} companies for quick testing")
    
    # Save as temporary file
    temp_file = Path("/tmp/sample_companies.csv")
    df.to_csv(temp_file, index=False)
    
    # Process the sample
    chunks_processed = pipeline.process_csv_file(temp_file)
    
    logger.info(f"✅ Quick sample ingestion completed!")
    logger.info(f"Processed {chunks_processed} chunks from {len(df)} companies")
    
    # Verify results
    from qdrant_client import QdrantClient
    from elasticsearch import Elasticsearch
    
    qdrant_client = QdrantClient(host='localhost', port=6333)
    es_client = Elasticsearch(['http://localhost:9200'])
    
    qdrant_count = qdrant_client.get_collection('indian_companies').points_count
    es_count = es_client.count(index='indian_companies')['count']
    
    logger.info(f"Final counts - Qdrant: {qdrant_count}, Elasticsearch: {es_count}")
    
    # Clean up
    temp_file.unlink()
    
    return qdrant_count, es_count

if __name__ == "__main__":
    quick_sample_ingestion()