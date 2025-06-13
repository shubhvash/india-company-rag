#!/usr/bin/env python3
"""
Migrate data from Qdrant to Elasticsearch using indian_companies index
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_qdrant_to_elasticsearch():
    """Migrate all data from Qdrant to Elasticsearch"""
    
    # Initialize clients
    qdrant_client = QdrantClient(host='localhost', port=6333)
    es_client = Elasticsearch(['http://localhost:9200'])
    
    logger.info("Starting migration from Qdrant to Elasticsearch...")
    
    try:
        # Get collection info
        collection_info = qdrant_client.get_collection('indian_companies')
        total_points = collection_info.points_count
        logger.info(f"Found {total_points} points in Qdrant")
        
        if total_points == 0:
            logger.warning("No data in Qdrant to migrate")
            return
        
        # Create ES index if it doesn't exist
        if not es_client.indices.exists(index='indian_companies'):
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
                        "full_text": {"type": "text", "analyzer": "standard"},
                        "address": {"type": "text"},
                        "company_status": {"type": "keyword"},
                        "listing_status": {"type": "keyword"},
                        "chunk_type": {"type": "keyword"}
                    }
                }
            }
            es_client.indices.create(index='indian_companies', body=mapping)
            logger.info("Created Elasticsearch index with proper mapping")
        
        # Scroll through all points in batches
        batch_size = 1000
        total_migrated = 0
        
        # Get first batch
        scroll_result = qdrant_client.scroll(
            collection_name='indian_companies',
            limit=batch_size,
            with_payload=True
        )
        
        points = scroll_result[0]
        next_offset = scroll_result[1]
        
        with tqdm(total=total_points, desc="Migrating to Elasticsearch") as pbar:
            while points:
                # Prepare batch for Elasticsearch
                actions = []
                for point in points:
                    action = {
                        '_index': 'indian_companies',
                        '_id': str(point.id),
                        '_source': point.payload
                    }
                    actions.append(action)
                
                # Bulk index to Elasticsearch
                if actions:
                    success_count, failed = bulk(es_client, actions, index='indian_companies')
                    total_migrated += success_count
                    
                    if failed:
                        logger.warning(f"Failed to index {len(failed)} documents")
                
                pbar.update(len(points))
                
                # Get next batch
                if next_offset:
                    scroll_result = qdrant_client.scroll(
                        collection_name='indian_companies',
                        offset=next_offset,
                        limit=batch_size,
                        with_payload=True
                    )
                    points = scroll_result[0]
                    next_offset = scroll_result[1]
                else:
                    break
        
        # Final verification
        es_count = es_client.count(index='indian_companies')['count']
        
        logger.info(f"Migration completed!")
        logger.info(f"Total points in Qdrant: {total_points}")
        logger.info(f"Total documents migrated: {total_migrated}")
        logger.info(f"Final Elasticsearch count: {es_count}")
        
        if es_count >= total_points * 0.95:  # Allow 5% tolerance
            logger.info("✅ Migration successful!")
            return True
        else:
            logger.warning(f"⚠️ Migration incomplete. Expected ~{total_points}, got {es_count}")
            return False
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def main():
    """Main function"""
    success = migrate_qdrant_to_elasticsearch()
    if success:
        print("\n🎉 Migration completed successfully!")
        print("Both databases now use the 'indian_companies' index")
    else:
        print("\n❌ Migration failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()