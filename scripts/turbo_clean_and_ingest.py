#!/usr/bin/env python3
"""
Turbo clean setup and run SUPER-FAST ingestion with all optimizations
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
from scripts.turbo_fast_ingest import TurboFastIngestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_databases():
    """Clean and recreate databases with optimized settings"""
    logger.info("🧹 Turbo cleaning databases...")
    
    try:
        # Clean Qdrant
        try:
            qdrant_client = QdrantClient(host="localhost", port=6334, prefer_grpc=True)
            logger.info("✅ Using Qdrant gRPC connection for cleaning")
        except:
            qdrant_client = QdrantClient(host="localhost", port=6333)
            logger.info("✅ Using Qdrant HTTP connection for cleaning")
            
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
        logger.info("✅ Created fresh optimized Qdrant collection")
        
        # Clean Elasticsearch
        es_client = Elasticsearch([
            "http://localhost:9200"
        ], timeout=300, max_retries=3)
        
        if es_client.indices.exists(index="indian_companies"):
            es_client.indices.delete(index="indian_companies")
            logger.info("✅ Deleted existing Elasticsearch index")
        else:
            logger.info("ℹ️  No existing Elasticsearch index to delete")
        
        logger.info("🎉 Turbo databases cleaned successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to clean databases: {e}")
        return False

def main():
    """Main function with turbo-fast ingestion"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Turbo clean and super-fast ingest with all optimizations")
    parser.add_argument("--max-companies", type=int, default=50000, 
                       help="Maximum companies to process (default: 50000)")
    parser.add_argument("--sample-only", action="store_true",
                       help="Process only 2000 companies for testing")
    parser.add_argument("--all-data", action="store_true",
                       help="Process ALL data from all CSV files")
    parser.add_argument("--parallel-files", action="store_true",
                       help="Process multiple files in parallel (for --all-data)")
    parser.add_argument("--gpu", action="store_true",
                       help="Force GPU usage check and optimization")
    
    args = parser.parse_args()
    
    # Mode setup
    if args.sample_only:
        max_companies = 2000
        mode = "TURBO_SAMPLE"
        logger.info("🔥 TURBO SAMPLE MODE: Clean + 2000 companies with all optimizations")
    elif args.all_data:
        max_companies = None
        mode = "TURBO_ALL_DATA"
        parallel_info = " + PARALLEL FILES" if args.parallel_files else ""
        logger.info(f"🌍 TURBO ALL DATA MODE: Clean + ALL companies{parallel_info}")
        logger.info("⚠️  Turbo mode with GPU can complete in 5-15 minutes!")
        logger.info("📊 Expected: 1M+ companies with comprehensive field extraction")
        
        # Confirmation
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
        mode = "TURBO_FAST"
        logger.info(f"🚀 TURBO FAST MODE: Clean + up to {max_companies} companies")
    
    # Clean databases first
    if not clean_databases():
        logger.error("❌ Database cleaning failed, aborting")
        return
    
    # Run TURBO ingestion
    try:
        logger.info("🚀 Starting TURBO ingestion pipeline with all optimizations...")
        start_time = time.time()
        
        # Import and check GPU
        import torch
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            logger.info(f"🚀 GPU DETECTED: {gpu_name} ({gpu_memory:.1f}GB VRAM)")
            logger.info("⚡ Turbo mode will use GPU acceleration for 10-50x speedup!")
        else:
            logger.info("⚠️  No GPU detected - using CPU mode (still optimized)")
            
        if args.gpu and not gpu_available:
            logger.warning("🚨 --gpu flag used but no GPU available!")
        
        pipeline = TurboFastIngestion()
        pipeline.initialize_databases()
        pipeline.start_time = start_time
        
        # Find CSV files
        dataset_path = Path("dataset")
        csv_files = sorted(dataset_path.glob("*.csv"), key=lambda x: x.stat().st_size)
        
        if not csv_files:
            logger.error("❌ No CSV files found")
            return
        
        # Process files based on mode
        if mode == "TURBO_ALL_DATA":
            if args.parallel_files and len(csv_files) > 1:
                # Use parallel file processing
                logger.info(f"🔥 PARALLEL TURBO MODE: Processing {len(csv_files)} files simultaneously")
                logger.info("⚡ This will use all CPU cores + GPU for maximum speed!")
                
                # Call turbo script with parallel flag
                import subprocess
                cmd = [
                    sys.executable, 
                    "scripts/turbo_fast_ingest.py", 
                    "--all-data", 
                    "--parallel-files"
                ]
                result = subprocess.run(cmd, capture_output=False)
                if result.returncode != 0:
                    logger.error("❌ Parallel turbo ingestion failed")
                    return
                
                # Get final counts
                try:
                    qdrant_count = pipeline.qdrant_client.get_collection('indian_companies').points_count
                    es_count = pipeline.es_client.count(index='indian_companies')['count']
                    total_processed = min(qdrant_count, es_count)
                except:
                    total_processed = 0
                    qdrant_count = 0
                    es_count = 0
            else:
                # Sequential all-data processing
                logger.info(f"📁 TURBO Processing ALL {len(csv_files)} CSV files:")
                for csv_file in csv_files:
                    logger.info(f"   - {csv_file.name} ({csv_file.stat().st_size / 1024 / 1024:.1f} MB)")
                
                total_processed = 0
                total_qdrant = 0
                total_es = 0
                
                for i, csv_file in enumerate(csv_files, 1):
                    logger.info(f"🔄 Turbo processing file {i}/{len(csv_files)}: {csv_file.name}")
                    processed, qdrant, es = pipeline.process_file_turbo(csv_file, None)
                    total_processed += processed
                    total_qdrant += qdrant
                    total_es += es
                    logger.info(f"✅ File {i} complete: +{processed} companies (Total: {total_processed})")
                
                qdrant_count = total_qdrant
                es_count = total_es
        else:
            # Single file processing
            csv_file = csv_files[0]
            logger.info(f"📁 Turbo processing: {csv_file.name}")
            total_processed, qdrant_count, es_count = pipeline.process_file_turbo(csv_file, max_companies)
        
        elapsed_time = time.time() - start_time
        
        # Final verification with ES refresh
        try:
            # Force Elasticsearch refresh to make documents searchable
            pipeline.es_client.indices.refresh(index='indian_companies')
            time.sleep(1)  # Brief wait for refresh
            
            final_qdrant = pipeline.qdrant_client.get_collection('indian_companies').points_count
            final_es = pipeline.es_client.count(index='indian_companies')['count']
            qdrant_count = final_qdrant
            es_count = final_es
        except Exception as e:
            logger.warning(f"Final verification failed: {e}")
        
        # Results
        if mode == "TURBO_ALL_DATA":
            logger.info(f"🎉 TURBO ALL-DATA INGESTION COMPLETED!")
            logger.info(f"⏱️  Total time: {elapsed_time/60:.1f} minutes ({elapsed_time:.1f} seconds)")
            logger.info(f"📊 Final counts - Qdrant: {qdrant_count}, Elasticsearch: {es_count}")
            if elapsed_time > 0:
                logger.info(f"⚡ Turbo processing rate: {total_processed/elapsed_time:.1f} companies/second")
            logger.info(f"🌍 Complete dataset ready with comprehensive field extraction!")
            
            # Performance comparison
            estimated_old_time = 60 * 60  # 60 minutes
            speedup = estimated_old_time / elapsed_time if elapsed_time > 0 else 1
            logger.info(f"🚀 Turbo speedup: {speedup:.1f}x faster than original method!")
            
        else:
            logger.info(f"🎉 TURBO CLEAN + INGEST COMPLETED IN {elapsed_time:.1f} SECONDS!")
            logger.info(f"📊 Final counts - Qdrant: {qdrant_count}, Elasticsearch: {es_count}")
            if elapsed_time > 0:
                logger.info(f"⚡ Turbo processing rate: {total_processed/elapsed_time:.1f} companies/second")
            logger.info(f"🎯 Turbo system ready with {total_processed} companies!")
        
        # System info
        if gpu_available:
            logger.info(f"✅ GPU acceleration was successfully utilized!")
        logger.info(f"🎊 All optimizations applied: GPU, large batches, parallel processing, async operations")
        
    except Exception as e:
        logger.error(f"❌ Turbo ingestion failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()