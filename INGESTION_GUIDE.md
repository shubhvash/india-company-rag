# 🚀 Fast Ingestion Guide

## Quick Start Options

### 🔥 Sample Data (Recommended for Testing)
**Best for**: Quick testing, development, demos
```bash
python scripts/clean_and_ingest.py --sample-only
```
- **Time**: ~7 seconds
- **Data**: 1,000 companies from Andhra Pradesh
- **Size**: 16MB file
- **Result**: Clean, fast system for testing

### ⚡ Fast Mode (Recommended for Development)
**Best for**: Development with decent data size
```bash
python scripts/clean_and_ingest.py --max-companies 10000
# or just:
python scripts/clean_and_ingest.py
```
- **Time**: ~35 seconds
- **Data**: 5,000 companies (default) or custom amount
- **Size**: From smallest file first
- **Result**: Good balance of speed and data volume

### 🌍 Complete Dataset (Production)
**Best for**: Full production deployment
```bash
python scripts/clean_and_ingest.py --all-data
```
- **Time**: 20-30 minutes
- **Data**: 1,057,018 companies from 5 states
- **Size**: 321MB total (5 CSV files)
- **Result**: Complete Indian company database

## 📊 Dataset Overview

| State | Companies | File Size | Processing Time |
|-------|-----------|-----------|----------------|
| Delhi | 427,421 | 124MB | ~15 min |
| Uttar Pradesh | 212,326 | 65MB | ~7 min |
| Karnataka | 194,736 | 62MB | ~7 min |
| Telangana | 171,079 | 54MB | ~6 min |
| Andhra Pradesh | 51,456 | 16MB | ~2 min |
| **Total** | **1,057,018** | **321MB** | **~30 min** |

## 🎯 Which Option to Choose?

### For Development & Testing:
```bash
# Quick test
python scripts/clean_and_ingest.py --sample-only

# More comprehensive test
python scripts/clean_and_ingest.py --max-companies 5000
```

### For Production:
```bash
# Full dataset (recommended for production)
python scripts/clean_and_ingest.py --all-data
```

### For Custom Requirements:
```bash
# Specific amount
python scripts/clean_and_ingest.py --max-companies 25000

# Quick rebuild with 2K companies
python scripts/clean_and_ingest.py --max-companies 2000
```

## ⚡ Performance Metrics

- **Processing Speed**: 150-400 companies/second
- **Sample Mode**: 1,000 companies in 7 seconds
- **Fast Mode**: 5,000 companies in 35 seconds  
- **All Data**: 1M+ companies in 30 minutes

## 🔧 Technical Details

### What Gets Cleaned:
- ✅ Qdrant collection `indian_companies` deleted & recreated
- ✅ Elasticsearch index `indian_companies` deleted & recreated
- ✅ Fresh start with consistent naming

### What Gets Indexed:
- ✅ **Qdrant**: Vector embeddings for semantic search
- ✅ **Elasticsearch**: Text indices for keyword search
- ✅ **Unified naming**: Both use `indian_companies` index
- ✅ **Persistent storage**: Data survives container restarts

### Optimizations:
- ✅ Minimal chunks (1 per company vs 3)
- ✅ Small batch sizes (25 for Qdrant, 100 for ES)
- ✅ Retry logic for timeouts
- ✅ Parallel text and vector indexing
- ✅ Progress tracking and error handling

## 🛠️ Troubleshooting

### If Ingestion Fails:
```bash
# Check system status
curl http://localhost:8000/health

# Restart with sample data
python scripts/clean_and_ingest.py --sample-only

# Check Docker services
docker-compose ps
```

### If Performance is Slow:
- Use `--sample-only` for testing
- Reduce `--max-companies` number
- Ensure Docker has sufficient memory (4GB+)
- Close other resource-heavy applications

## 📈 Monitoring Progress

For all-data ingestion, monitor in real-time:
```bash
# In another terminal
curl http://localhost:8000/health

# Check specific counts
curl -s http://localhost:6333/collections/indian_companies | grep points_count
curl -s http://localhost:9200/indian_companies/_count
```

## 🎉 Success Indicators

After ingestion completes:
- ✅ Health check shows `"status": "healthy"`
- ✅ Both Qdrant and Elasticsearch have data
- ✅ System responds to queries in <5 seconds
- ✅ Streamlit UI works at http://localhost:8501