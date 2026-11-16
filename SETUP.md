# Indian Company Intelligence RAG System - Setup Guide

This guide provides step-by-step instructions to set up and run the complete RAG system.

## Prerequisites

- Docker and Docker Compose (latest versions)
- 8GB+ RAM recommended
- Google Gemini API key
- Git (for cloning the repository)

## Quick Start (5-minute setup)

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd india-company-rag

# Copy environment configuration
cp .env.example .env

# Edit .env file with your Google API key
nano .env
# Set: GOOGLE_API_KEY=your_actual_api_key_here
```

### 2. Start the System

```bash
# Start all services (databases, API, UI, monitoring)
docker-compose up -d

# Check if all services are running
docker-compose ps
```

### 3. Initialize Data

```bash
# Run data ingestion (first time only)
docker-compose --profile ingestion up ingestion

# Wait for ingestion to complete (check logs)
docker-compose logs ingestion
```

### 4. Access Applications

- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Health Check**: http://localhost:8000/health

## Detailed Setup Instructions

### Environment Configuration

The `.env` file should contain:

```bash
# Required: Google Gemini API Key
GOOGLE_API_KEY=your_google_api_key_here

# Database URLs (defaults work for Docker setup)
QDRANT_HOST=qdrant
QDRANT_PORT=6333
ELASTICSEARCH_URL=http://elasticsearch:9200
POSTGRES_URL=postgresql://raguser:ragpassword@postgres:5432/monitoring

# Optional: Application settings
DEBUG=false
LOG_LEVEL=INFO
```

### Service Architecture

The system consists of 6 Docker services:

1. **qdrant**: Vector database for semantic search
2. **elasticsearch**: Text search engine
3. **postgres**: Monitoring data storage
4. **grafana**: Analytics dashboard
5. **api**: FastAPI backend
6. **streamlit**: Web UI

### Initial Data Ingestion

The ingestion process:

1. Discovers all CSV files in the `dataset/` directory
2. Processes and chunks company data
3. Generates embeddings using sentence-transformers
4. Indexes to both Qdrant (vector) and Elasticsearch (text)

To add new state data:
```bash
# 1. Add new CSV file to dataset/ directory
cp new_state_data.csv dataset/

# 2. Re-run ingestion
docker-compose --profile ingestion up ingestion
```

### Monitoring Setup

Access Grafana at http://localhost:3000:
- Username: `admin`
- Password: `admin`

The dashboard includes 7 monitoring charts:
1. Query Volume Over Time
2. Response Time Metrics  
3. Retrieval Method Usage
4. User Satisfaction Trends
5. Rating Distribution
6. Retrieval Precision by Method
7. RAG Relevance by Prompt Type

### API Endpoints

Key endpoints available at http://localhost:8000:

- `POST /query` - Basic RAG queries
- `POST /query/enhanced` - Enhanced queries with rewriting/re-ranking
- `GET /health` - System health check
- `POST /feedback` - Submit user feedback
- `GET /evaluation/retrieval` - Retrieval method performance
- `GET /evaluation/rag` - RAG approach performance
- `GET /metrics` - System metrics
- `GET /companies/search` - Direct company search

## Usage Examples

### Basic Query via API

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me technology companies in Karnataka",
    "retrieval_method": "hybrid",
    "prompt_type": "context_aware",
    "top_k": 5
  }'
```

### Enhanced Query

```bash
curl -X POST "http://localhost:8000/query/enhanced" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find companies with high capital in manufacturing",
    "retrieval_method": "hybrid",
    "prompt_type": "context_aware",
    "top_k": 5
  }'
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Evaluation

Run comprehensive evaluation:

```bash
# Inside the API container
docker-compose exec api python scripts/evaluate.py --eval-type all

# Or run specific evaluations
docker-compose exec api python scripts/evaluate.py --eval-type retrieval
docker-compose exec api python scripts/evaluate.py --eval-type rag
```

Results are saved in `evaluation_results/` directory with timestamps.

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check logs
   docker-compose logs [service-name]
   
   # Restart specific service
   docker-compose restart [service-name]
   ```

2. **API key errors**
   - Verify your Google Gemini API key in `.env`
   - Ensure the key has proper permissions

3. **Database connection issues**
   ```bash
   # Check database health
   docker-compose exec postgres pg_isready -U raguser -d monitoring
   docker-compose exec elasticsearch curl -f http://localhost:9200/_cluster/health
   ```

4. **Memory issues**
   - Ensure you have at least 8GB RAM
   - Reduce `top_k` parameter in queries
   - Use fewer Docker services if needed

5. **Ingestion failures**
   ```bash
   # Check ingestion logs
   docker-compose --profile ingestion logs ingestion
   
   # Verify CSV file format
   head -5 dataset/delhi.csv
   ```

### Performance Optimization

1. **For better performance**:
   - Use SSD storage
   - Increase Docker memory allocation
   - Use `hybrid` retrieval method for best results

2. **For development**:
   ```bash
   # Run services individually
   docker-compose up -d qdrant elasticsearch postgres
   
   # Run API locally
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

### Data Validation

Verify data ingestion:

```bash
# Check Qdrant collection
curl http://localhost:6333/collections/indian_companies

# Check Elasticsearch index
curl http://localhost:9200/company_documents/_count

# Test basic search
curl "http://localhost:8000/companies/search?query=technology&limit=3"
```

## Adding New States

To extend the system with data from additional states:

1. **Prepare CSV file**: Ensure it follows the same schema as existing files
2. **Add to dataset**: Place CSV in `dataset/` directory
3. **Run ingestion**: `docker-compose --profile ingestion up ingestion`
4. **Verify**: Check via search API or Streamlit UI

Required CSV columns:
- `CIN`, `CompanyName`, `CompanyCategory`
- `AuthorizedCapital`, `PaidupCapital`
- `Registered_Office_Address`, `CompanyStateCode`
- `CompanyIndustrialClassification`

## Production Deployment

For production deployment:

1. **Security**:
   - Change default passwords
   - Use environment-specific `.env` files
   - Enable HTTPS/SSL
   - Restrict CORS origins

2. **Scaling**:
   - Use managed databases (cloud providers)
   - Add load balancing
   - Configure horizontal scaling

3. **Monitoring**:
   - Set up alerting in Grafana
   - Monitor resource usage
   - Configure log aggregation

## Support

For issues and questions:
1. Check this documentation
2. Review Docker logs: `docker-compose logs`
3. Test individual components
4. Check API health endpoints
5. Verify database connectivity

The system is designed to be resilient and will gracefully handle most failures while providing detailed error messages for debugging.