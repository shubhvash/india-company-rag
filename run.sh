#!/bin/bash

# Indian Company Intelligence RAG System - Quick Start Script

set -e  # Exit on any error

echo "🏢 Indian Company Intelligence RAG System"
echo "==========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env file and add your GOOGLE_API_KEY"
    echo "   nano .env"
    echo ""
    read -p "Press Enter when you've added your API key..."
fi

# Check if GOOGLE_API_KEY is set
if ! grep -q "GOOGLE_API_KEY=" .env || grep -q "GOOGLE_API_KEY=your_" .env; then
    echo "❌ Please set your GOOGLE_API_KEY in the .env file"
    exit 1
fi

echo "🚀 Starting RAG system..."

# Start all services
echo "📦 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

# Check Qdrant
if curl -f http://localhost:6333/collections >/dev/null 2>&1; then
    echo "✅ Qdrant is running"
else
    echo "❌ Qdrant is not responding"
fi

# Check Elasticsearch
if curl -f http://localhost:9200/_cluster/health >/dev/null 2>&1; then
    echo "✅ Elasticsearch is running"
else
    echo "❌ Elasticsearch is not responding"
fi

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U raguser -d monitoring >/dev/null 2>&1; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL is not responding"
fi

# Check if data needs to be ingested
echo "🔍 Checking if data ingestion is needed..."

# Check Qdrant collection points count
QDRANT_POINTS=$(curl -s http://localhost:6333/collections/indian_companies 2>/dev/null | grep -o '"points_count":[0-9]*' | grep -o '[0-9]*' || echo "0")

# Check Elasticsearch index document count  
ES_DOCS=$(curl -s http://localhost:9200/indian_companies/_count 2>/dev/null | grep -o '"count":[0-9]*' | grep -o '[0-9]*' || echo "0")

echo "📊 Current data status (indian_companies index):"
echo "   Qdrant points: $QDRANT_POINTS"
echo "   Elasticsearch docs: $ES_DOCS"

# Consider data ingested if we have reasonable amounts in both databases
if [ "$QDRANT_POINTS" -gt 10000 ] && [ "$ES_DOCS" -gt 10000 ]; then
    echo "✅ Sufficient data already ingested (Qdrant: $QDRANT_POINTS, ES: $ES_DOCS)"
    echo "💡 To re-ingest data, run: python scripts/ingest_data.py"
else
    echo "📥 Data ingestion needed..."
    echo "⚠️  This may take 20-30 minutes for the full dataset"
    echo "📊 Current: Qdrant=$QDRANT_POINTS, Elasticsearch=$ES_DOCS"
    
    # Check if we have partial data that needs completing
    if [ "$QDRANT_POINTS" -gt 1000 ] && [ "$ES_DOCS" -lt 1000 ]; then
        echo "🔄 Elasticsearch needs data migration from Qdrant..."
        echo "💡 Run this command to sync: python scripts/migrate_es.py"
    elif [ "$QDRANT_POINTS" -lt 1000 ] && [ "$ES_DOCS" -gt 1000 ]; then
        echo "🔄 Qdrant needs data migration from Elasticsearch..."
        echo "💡 Run this command to sync: python scripts/migrate_qdrant.py"
    else
        # Ask user if they want to proceed with full ingestion
        read -p "🤔 Continue with full data ingestion? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🚀 Starting ingestion process..."
            echo "💡 Due to Docker networking issues, using direct Python execution:"
            echo "   cd /your/project/directory"
            echo "   source .venv/bin/activate"
            echo "   python scripts/ingest_data.py"
            echo ""
            echo "📋 Or run in background:"
            echo "   nohup python scripts/ingest_data.py > ingestion.log 2>&1 &"
        else
            echo "⏭️  Skipping data ingestion"
            echo "💡 You can run it later with: python scripts/ingest_data.py"
        fi
    fi
fi

# Final health check
echo "🔍 Final system health check..."
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ API is responding"
else
    echo "❌ API is not responding"
fi

echo ""
echo "🎉 System is ready!"
echo ""
echo "🌐 Access Points:"
echo "   Streamlit UI:    http://localhost:8501"
echo "   FastAPI Docs:    http://localhost:8000/docs"
echo "   Grafana:         http://localhost:3000 (admin/admin)"
echo "   Health Check:    http://localhost:8000/health"
echo ""
echo "📊 Quick Test:"
echo "   curl -X POST http://localhost:8000/query \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"query\": \"technology companies in Karnataka\", \"retrieval_method\": \"hybrid\"}'"
echo ""
echo "🛠️  Management Commands:"
echo "   View logs:       docker-compose logs -f"
echo "   Stop system:     docker-compose down"
echo "   Restart system:  docker-compose restart"
echo ""
echo "📥 Data Management:"
echo "   Run full ingestion:    python scripts/ingest_data.py"
echo "   Migrate ES from Qdrant: python scripts/migrate_es.py"
echo "   Check data status:     curl http://localhost:8000/health"
echo "   Monitor ingestion:     tail -f ingestion.log"
echo "   Volume backup:         docker run --rm -v llm-zoomcamp-project-2025_qdrant_data:/data alpine tar czf - /data"
echo ""
echo "📚 For detailed documentation, see:"
echo "   - README.md      (Overview and architecture)"
echo "   - SETUP.md       (Detailed setup instructions)"
echo "   - EVALUATION.md  (Performance evaluation results)"
echo ""

# Optional: Open browser
if command -v xdg-open &> /dev/null; then
    read -p "🌐 Open Streamlit UI in browser? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        xdg-open http://localhost:8501
    fi
elif command -v open &> /dev/null; then
    read -p "🌐 Open Streamlit UI in browser? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open http://localhost:8501
    fi
fi

echo "✨ Setup complete! Happy querying!"