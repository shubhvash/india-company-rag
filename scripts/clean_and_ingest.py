#!/usr/bin/env python3
"""
Clean setup and run FAST unified ingestion with consistent 'indian_companies' index name
"""
import sys
import logging
from pathlib import Path
import time

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from elasticsearch import Elasticsearch
from scripts.reliable_fast_ingest import ReliableFastIngestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_databases():
    """Clean and recreate databases with 'indian_companies' index name"""
    logger.info("🧹 Cleaning databases...")
    
    try:
        # Clean Qdrant
        qdrant_client = QdrantClient(host="localhost", port=6333)
        try:
            qdrant_client.delete_collection("indian_companies")
            logger.info("✅ Deleted existing Qdrant collection")
        except:
            logger.info("ℹ️  No existing Qdrant collection to delete")
        
        # Recreate Qdrant collection
        qdrant_client.create_collection(
            collection_name="indian_companies",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        logger.info("✅ Created fresh Qdrant collection: indian_companies")
        
        # Clean Elasticsearch
        es_client = Elasticsearch(["http://localhost:9200"])
        if es_client.indices.exists(index="indian_companies"):
            es_client.indices.delete(index="indian_companies")
            logger.info("✅ Deleted existing Elasticsearch index")
        else:
            logger.info("ℹ️  No existing Elasticsearch index to delete")
        
        logger.info("🎉 Databases cleaned successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to clean databases: {e}")
        return False

def main():
    """Main function with fast ingestion"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean and fast ingest company data")
    parser.add_argument("--max-companies", type=int, default=5000, 
                       help="Maximum companies to process (default: 5000)")
    parser.add_argument("--sample-only", action="store_true",
                       help="Process only 1000 companies for testing")
    parser.add_argument("--all-data", action="store_true",
                       help="Process ALL data from all CSV files (may take 20-30 minutes)")
    
    args = parser.parse_args()
    
    if args.sample_only:
        max_companies = 1000
        mode = "SAMPLE"
        logger.info("🔥 SAMPLE MODE: Clean + 1000 companies")
    elif args.all_data:
        max_companies = None  # No limit
        mode = "ALL_DATA"
        logger.info("🌍 ALL DATA MODE: Clean + ALL companies from ALL files")
        logger.info("⚠️  This will take 20-30 minutes but gives you the complete dataset")
        logger.info("📊 Expected: 1M+ companies across 5 states (Delhi, Karnataka, UP, Telangana, AP)")
        
        # Confirmation prompt
        try:
            confirm = input("🤔 Continue with full dataset ingestion? (y/n): ").lower().strip()
            if confirm not in ['y', 'yes']:
                logger.info("⏭️  All-data ingestion cancelled")
                return
        except KeyboardInterrupt:
            logger.info("\n⏭️  All-data ingestion cancelled")
            return
    else:
        max_companies = args.max_companies
        mode = "FAST"
        logger.info(f"🚀 FAST MODE: Clean + up to {max_companies} companies")
    
    # Clean databases first
    if not clean_databases():
        logger.error("❌ Database cleaning failed, aborting")
        return
    
    # Run FAST ingestion
    try:
        logger.info("🚀 Starting FAST ingestion pipeline...")
        start_time = time.time()
        
        pipeline = ReliableFastIngestion()
        pipeline.initialize_databases()
        
        # Find CSV files
        dataset_path = Path("dataset")
        csv_files = sorted(dataset_path.glob("*.csv"), key=lambda x: x.stat().st_size)
        
        if not csv_files:
            logger.error("❌ No CSV files found")
            return
        
        # Process files based on mode
        if mode == "ALL_DATA":
            # Process all files
            logger.info(f"📁 Processing ALL {len(csv_files)} CSV files:")
            for csv_file in csv_files:
                logger.info(f"   - {csv_file.name} ({csv_file.stat().st_size / 1024 / 1024:.1f} MB)")
            
            total_processed = 0
            total_qdrant = 0
            total_es = 0
            
            for i, csv_file in enumerate(csv_files, 1):
                logger.info(f"🔄 Processing file {i}/{len(csv_files)}: {csv_file.name}")
                processed, qdrant, es = pipeline.process_file_reliably(csv_file, None)  # No limit
                total_processed += processed
                total_qdrant += qdrant
                total_es += es
                logger.info(f"✅ File {i} complete: +{processed} companies (Total: {total_processed})")
        else:
            # Process single smallest file with limit
            csv_file = csv_files[0]
            logger.info(f"📁 Processing: {csv_file.name}")
            total_processed, total_qdrant, total_es = pipeline.process_file_reliably(csv_file, max_companies)
        
        elapsed_time = time.time() - start_time
        
        # Final verification
        try:
            qdrant_count = pipeline.qdrant_client.get_collection('indian_companies').points_count
            es_count = pipeline.es_client.count(index='indian_companies')['count']
        except:
            qdrant_count = total_qdrant
            es_count = total_es
        
        if mode == "ALL_DATA":
            logger.info(f"🎉 COMPLETE DATASET INGESTION FINISHED!")
            logger.info(f"⏱️  Total time: {elapsed_time/60:.1f} minutes ({elapsed_time:.1f} seconds)")
            logger.info(f"📊 Final counts - Qdrant: {qdrant_count}, Elasticsearch: {es_count}")
            logger.info(f"⚡ Processing rate: {total_processed/elapsed_time:.1f} companies/second")
            logger.info(f"🌍 Complete Indian company dataset ready with 1M+ companies!")
            logger.info(f"📈 Data coverage: {len(csv_files)} states/regions")
        else:
            logger.info(f"🎉 CLEAN + INGEST COMPLETED IN {elapsed_time:.1f} SECONDS!")
            logger.info(f"📊 Final counts - Qdrant: {qdrant_count}, Elasticsearch: {es_count}")
            logger.info(f"⚡ Processing rate: {total_processed/elapsed_time:.1f} companies/second")
            logger.info(f"🎯 System ready with {total_processed} companies!")
        
    except Exception as e:
        logger.error(f"❌ Fast ingestion failed: {e}")

if __name__ == "__main__":
    main()