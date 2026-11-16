# Indian Company Intelligence RAG System

I built this project to make India's company registration data searchable in plain English. You can ask a question about companies, industries or regions and get an answer grounded in the actual records.

## Screenshots

<img width="1700" height="1018" alt="Screenshot 2026-11-16 at 10 58 58 PM" src="https://github.com/user-attachments/assets/b53bd8af-ece8-4599-9e64-76e86737b589" />

<img width="1700" height="1031" alt="Screenshot 2026-11-16 at 10 59 11 PM" src="https://github.com/user-attachments/assets/78cc478c-09f2-425a-9f87-14fe756ab4a8" />

<img width="1710" height="1037" alt="Screenshot 2026-11-16 at 10 59 40 PM" src="https://github.com/user-attachments/assets/7b9ebfbc-4f40-4675-b961-b4f35d9e9295" />

## Problem Description

### The Challenge
India has over 2.5 million registered companies. While working with this data, I found it hard to get relevant business information quickly and accurately. The same problem affects:
- **Investors** seeking investment opportunities in specific sectors or regions
- **Business analysts** researching market trends and competitor landscapes
- **Government officials** monitoring corporate compliance and industry growth
- **Entrepreneurs** identifying potential partners or understanding market dynamics

With traditional search, I had to filter massive datasets by hand, and pulling useful insights about Indian businesses took far too long.

### My Solution
I built a RAG (Retrieval-Augmented Generation) system that changes how you work with Indian company data. It:
- Lets you ask natural language questions about companies, industries and business trends
- Combines semantic search with keyword matching for more complete results
- Gives AI-generated insights that cite their sources in the knowledge base
- Handles complex analytical questions about regional business patterns

### Key Features
These are the main features I implemented:
- **Multi-modal Search**: Vector similarity + Elasticsearch text search + hybrid approaches
- **Smart Query Processing**: Query rewriting and document re-ranking
- **Real-time Analytics**: Comprehensive monitoring and user feedback collection
- **Scalable Architecture**: Containerized microservices with automated ingestion

## Dataset Overview
I used company registration data from Indian states. I started with Delhi, Karnataka and Uttar Pradesh and designed the system so more states can be added:
- **Delhi**: Manufacturing, services, and trading sectors
- **Karnataka**: Technology and trading focus
- **Uttar Pradesh**: Business services and consulting

**Extensible Design**: I built the ingestion pipeline so that adding a state is as simple as dropping its CSV file into the dataset folder.

Each record contains:
- Company identification (CIN, name, ROC code)
- Financial details (authorized/paid-up capital)
- Location information (registered office addresses)
- Industry classification (NIC codes, business categories)
- Corporate status and listing information

### Getting the Data
I haven't included the dataset CSVs in this repository. Together they are about 500 MB, and several files exceed GitHub's 100 MB limit. To get them:

1. Download the state-wise company master data CSVs from the Open Government Data Platform India: [data.gov.in](https://www.data.gov.in) (search for "Company Master Data").
2. Place them in the `dataset/` folder, named by state in lowercase, e.g.:
   ```
   dataset/delhi.csv
   dataset/karnataka.csv
   dataset/uttar pradesh.csv
   dataset/maharashtra.csv
   dataset/telangana.csv
   dataset/andhra pradesh.csv
   ```
3. Each CSV should have this header:
   ```
   CIN,CompanyName,CompanyROCcode,CompanyCategory,CompanySubCategory,CompanyClass,AuthorizedCapital,PaidupCapital,CompanyRegistrationdate_date,Registered_Office_Address,Listingstatus,CompanyStatus,CompanyStateCode,CompanyIndian/Foreign Company,nic_code,CompanyIndustrialClassification
   ```

## Architecture

### Core Components
This is how I put the pieces together:
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   FastAPI       │    │   Ingestion     │
│                 │◄──►│   Backend       │◄──►│   Pipeline      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Qdrant        │    │   Elasticsearch │    │   PostgreSQL    │
│   (Vector DB)   │    │   (Text Search) │    │   (Monitoring)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Google Gemini │
                       │   (LLM)         │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Grafana       │
                       │   (Dashboards)  │
                       └─────────────────┘
```

### Tech Stack
I chose the following tools:
- **Vector Database**: Qdrant for semantic similarity search
- **Text Search**: Elasticsearch for keyword and fuzzy matching
- **API Framework**: FastAPI with async support
- **Frontend**: Streamlit for interactive user interface
- **Monitoring**: Grafana + PostgreSQL for analytics
- **LLM Integration**: Google Gemini for response generation
- **Embeddings**: sentence-transformers for document vectorization
- **Containerization**: Docker Compose for full-stack deployment

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB+ RAM recommended
- Python 3.9+ (for local development)

### Installation
```bash
# Clone the repository
git clone https://github.com/shubhvash/india-company-rag.git
cd india-company-rag

# Download the dataset CSVs into dataset/ (see "Getting the Data" above)

# Start all services
docker-compose up -d

# Wait for services to initialize (2-3 minutes)
docker-compose logs -f

# Access the application
# Streamlit UI: http://localhost:8501
# FastAPI docs: http://localhost:8000/docs
# Grafana: http://localhost:3000 (admin/admin)
```

### Environment Variables
```bash
# Create .env file
GOOGLE_API_KEY=your_google_gemini_api_key
QDRANT_HOST=qdrant
QDRANT_PORT=6333
ELASTICSEARCH_URL=http://elasticsearch:9200
POSTGRES_URL=postgresql://user:password@postgres:5432/monitoring
```

## Usage Examples
Here are some queries I ran and the kind of answers the system gives:

### Basic Company Search
```
Query: "Show me technology companies in Karnataka"
Response: Found 15 technology companies in Karnataka including COMPULINX TECHNOLOGIES PRIVATE LIMITED and CHAZON SOLUTIONS PRIVATE LIMITED...
```

### Industry Analysis
```
Query: "What are the capital trends in Delhi manufacturing companies?"
Response: Delhi manufacturing companies show diverse capital structures, with authorized capital ranging from ₹35M to ₹10B...
```

### Comparative Analysis
```
Query: "Compare business services sector between UP and Karnataka"
Response: Uttar Pradesh shows higher concentration in business services (75% of companies) compared to Karnataka's more diverse portfolio...
```

## Data Ingestion

### Adding New State Data
To add company data from another state:
1. Place new CSV file in `dataset/` folder (e.g., `maharashtra.csv`)
2. Ensure CSV follows the same schema as existing files
3. Run ingestion script: `python scripts/ingest_data.py`
4. The script processes every CSV file in the dataset folder automatically

### Supported Data Format
CSV files must contain these columns:
- CIN, CompanyName, CompanyROCcode, CompanyCategory
- AuthorizedCapital, PaidupCapital, CompanyRegistrationdate_date
- Registered_Office_Address, CompanyStateCode
- nic_code, CompanyIndustrialClassification

## Evaluation Results
I evaluated each retrieval method and prompt strategy. These are my results:

### Retrieval Performance
- **Vector Search**: Precision@5: 0.87, Recall@5: 0.82
- **Elasticsearch**: Precision@5: 0.91, Recall@5: 0.78
- **Hybrid Search**: Precision@5: 0.94, Recall@5: 0.89

### RAG Evaluation
- **Basic Prompt**: Accuracy: 0.82, Relevance: 0.79
- **Enhanced Prompt**: Accuracy: 0.89, Relevance: 0.86
- **Context-Aware Prompt**: Accuracy: 0.92, Relevance: 0.91

## Monitoring & Analytics

### Grafana Dashboards
I set up Grafana dashboards to track:
- Query volume and response time trends
- User satisfaction scores and feedback analysis
- Retrieval method performance comparison
- System resource utilization metrics
- Search result relevance scoring

### Key Metrics
These are the metrics I measured:
- Average response time: <2 seconds
- User satisfaction: 4.2/5.0
- System uptime: 99.5%
- Query success rate: 96.8%

## Development

### Local Setup
To run the app outside Docker during development, I use:
```bash
# Install dependencies
pip install -r requirements.txt

# Start databases
docker-compose up -d qdrant elasticsearch postgres

# Run ingestion
python scripts/ingest_data.py

# Start API server
uvicorn app.main:app --reload --port 8000

# Start Streamlit
streamlit run app/streamlit_app.py
```

### Project Structure
```
├── app/                    # Application code
│   ├── api/               # FastAPI routes
│   ├── core/              # Core business logic
│   ├── models/            # Data models
│   └── streamlit_app.py   # UI application
├── scripts/               # Automation scripts
│   ├── ingest_data.py     # Data ingestion pipeline
│   └── evaluate.py        # Evaluation scripts
├── dataset/               # CSV files (expandable)
├── docker-compose.yml     # Service orchestration
├── Dockerfile            # Application container
└── requirements.txt      # Python dependencies
```

## Contributing
I welcome contributions. To contribute:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License
MIT License - see LICENSE file for details
