-- Initialize PostgreSQL database for monitoring

-- Create monitoring tables
CREATE TABLE IF NOT EXISTS user_queries (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    user_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    retrieval_method VARCHAR(50),
    num_results INTEGER,
    user_feedback INTEGER CHECK (user_feedback BETWEEN 1 AND 5),
    feedback_text TEXT
);

CREATE TABLE IF NOT EXISTS retrieval_metrics (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES user_queries(id),
    method VARCHAR(50) NOT NULL,
    precision_score FLOAT,
    recall_score FLOAT,
    response_time_ms INTEGER,
    num_documents_retrieved INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rag_evaluations (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    prompt_type VARCHAR(50) NOT NULL,
    response_text TEXT,
    relevance_score FLOAT,
    accuracy_score FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_user_queries_timestamp ON user_queries(timestamp);
CREATE INDEX IF NOT EXISTS idx_retrieval_metrics_timestamp ON retrieval_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_rag_evaluations_timestamp ON rag_evaluations(timestamp);

-- Insert some initial system metrics
INSERT INTO system_metrics (metric_name, metric_value) VALUES 
('system_startup', 1.0),
('database_initialized', 1.0);