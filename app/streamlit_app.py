"""
Streamlit UI for Indian Company Intelligence RAG System
"""

import os
import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any, List
import time

# Page configuration
st.set_page_config(
    page_title="Indian Company Intelligence",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

def init_session_state():
    """Initialize session state variables"""
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    if 'current_response' not in st.session_state:
        st.session_state.current_response = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = f"user_{int(time.time())}"

def make_api_request(endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
    """Make API request with error handling"""
    try:
        url = f"{API_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return {}
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return {}

def display_system_health():
    """Display system health status in sidebar"""
    health_data = make_api_request("/health")
    
    if health_data:
        status = health_data.get("status", "unknown")
        
        if status == "healthy":
            st.sidebar.success("🟢 System Healthy")
        elif status == "degraded":
            st.sidebar.warning("🟡 System Degraded")
        else:
            st.sidebar.error("🔴 System Unhealthy")
        
        components = health_data.get("components", {})
        if components:
            with st.sidebar.expander("Component Status"):
                for component, status in components.items():
                    if isinstance(status, bool):
                        icon = "✅" if status else "❌"
                        st.write(f"{icon} {component.title()}")
                    else:
                        st.write(f"📊 {component}: {status}")

def query_interface():
    """Main query interface"""
    st.title("🏢 Indian Company Intelligence")
    st.markdown("Ask questions about Indian companies using natural language")
    
    # Query input section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "Enter your question:",
            placeholder="e.g., Show me technology companies in Karnataka with high capital",
            key="main_query"
        )
    
    with col2:
        search_button = st.button("🔍 Search", type="primary")
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            retrieval_method = st.selectbox(
                "Retrieval Method:",
                ["hybrid", "vector", "elasticsearch"],
                index=0,
                help="Hybrid combines vector and text search for best results"
            )
        
        with col2:
            prompt_type = st.selectbox(
                "Prompt Strategy:",
                ["context_aware", "enhanced", "basic"],
                index=0,
                help="Context-aware provides the most tailored responses"
            )
        
        with col3:
            top_k = st.slider("Results to retrieve:", 3, 10, 5)
        
        enhanced_query = st.checkbox(
            "Use Enhanced Query (Query Rewriting + Re-ranking)",
            help="Applies query rewriting and document re-ranking for better results"
        )
    
    # Process query
    if search_button and query:
        with st.spinner("Processing your query..."):
            # Prepare request data
            request_data = {
                "query": query,
                "retrieval_method": retrieval_method,
                "prompt_type": prompt_type,
                "top_k": top_k,
                "user_id": st.session_state.user_id
            }
            
            # Choose endpoint based on enhanced option
            endpoint = "/query/enhanced" if enhanced_query else "/query"
            
            # Make API request
            response = make_api_request(endpoint, "POST", request_data)
            
            if response:
                st.session_state.current_response = response
                st.session_state.query_history.append({
                    "query": query,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "method": retrieval_method,
                    "enhanced": enhanced_query
                })

def display_response():
    """Display query response"""
    if st.session_state.current_response:
        response = st.session_state.current_response
        
        # Main response
        st.subheader("📝 Response")
        st.markdown(response.get("response", "No response generated"))
        
        # Response metadata
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Response Time", f"{response.get('response_time_ms', 0)}ms")
        with col2:
            st.metric("Results Found", response.get('num_results', 0))
        with col3:
            st.metric("Method", response.get('retrieval_method', 'N/A'))
        with col4:
            st.metric("Prompt Type", response.get('prompt_type', 'N/A'))
        
        # Retrieved documents
        if response.get('retrieved_documents'):
            st.subheader("📊 Source Companies")
            
            docs = response['retrieved_documents']
            
            # Create DataFrame for display
            df_data = []
            for doc in docs:
                # Format financial data
                auth_capital = doc.get('authorized_capital')
                paid_capital = doc.get('paid_up_capital')
                capital_ratio = doc.get('capital_utilization_ratio')
                
                financial_info = ""
                if auth_capital is not None:
                    financial_info += f"Auth: ₹{auth_capital:,}"
                if paid_capital is not None:
                    if financial_info:
                        financial_info += " | "
                    financial_info += f"Paid: ₹{paid_capital:,}"
                if capital_ratio is not None:
                    if financial_info:
                        financial_info += " | "
                    financial_info += f"Util: {capital_ratio}%"
                
                df_data.append({
                    "Company": doc.get('company_name', ''),
                    "State": doc.get('state', ''),
                    "City": doc.get('city', ''),
                    "Industry": doc.get('industry_classification', ''),
                    "Financial Info": financial_info if financial_info else "N/A",
                    "Status": doc.get('company_status', ''),
                    "Relevance Score": f"{doc.get('score', 0):.3f}",
                    "Chunk Type": doc.get('chunk_type', '')
                })
            
            df = pd.DataFrame(df_data)
            
            # Display as interactive table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
            
            # Visualization
            if len(docs) > 1:
                col1, col2 = st.columns(2)
                
                with col1:
                    # State distribution
                    state_counts = df['State'].value_counts()
                    if len(state_counts) > 1:
                        fig_states = px.pie(
                            values=state_counts.values,
                            names=state_counts.index,
                            title="Companies by State"
                        )
                        st.plotly_chart(fig_states, use_container_width=True)
                
                with col2:
                    # Industry distribution
                    industry_counts = df['Industry'].str.split(',').explode().str.strip().value_counts().head(5)
                    if len(industry_counts) > 1:
                        fig_industry = px.bar(
                            x=industry_counts.index,
                            y=industry_counts.values,
                            title="Top Industries"
                        )
                        fig_industry.update_xaxes(tickangle=45)
                        st.plotly_chart(fig_industry, use_container_width=True)
        
        # Feedback section
        st.subheader("📈 Rate this Response")
        col1, col2 = st.columns([1, 3])
        
        with col1:
            rating = st.slider("Rating (1-5):", 1, 5, 3, key="rating_slider")
        
        with col2:
            feedback_text = st.text_area(
                "Additional feedback (optional):",
                placeholder="Tell us how we can improve...",
                key="feedback_text"
            )
        
        if st.button("Submit Feedback"):
            feedback_data = {
                "query_id": hash(response.get('query', '')),  # Simplified ID
                "rating": rating,
                "feedback_text": feedback_text,
                "user_id": st.session_state.user_id
            }
            
            feedback_response = make_api_request("/feedback", "POST", feedback_data)
            if feedback_response:
                st.success("Thank you for your feedback!")

def analytics_dashboard():
    """Display analytics dashboard"""
    st.title("📊 System Analytics")
    
    # System metrics
    st.subheader("System Overview")
    metrics_data = make_api_request("/metrics")
    
    if metrics_data:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Queries (24h)",
                metrics_data.get('query_volume_24h', 0)
            )
        
        with col2:
            st.metric(
                "Avg Response Time",
                f"{metrics_data.get('avg_response_time_ms', 0):.1f}ms"
            )
        
        with col3:
            st.metric(
                "User Satisfaction",
                f"{metrics_data.get('user_satisfaction_avg', 0):.1f}/5.0"
            )
        
        with col4:
            st.metric(
                "System Uptime",
                f"{metrics_data.get('system_uptime_percent', 0):.1f}%"
            )
    
    # Query metrics
    st.subheader("Query Analytics")
    query_metrics = make_api_request("/metrics/queries?hours=24")
    
    if query_metrics and query_metrics.get('hourly_data'):
        # Query volume over time
        hourly_data = query_metrics['hourly_data']
        df_hourly = pd.DataFrame(hourly_data)
        df_hourly['timestamp'] = pd.to_datetime(df_hourly['timestamp'])
        
        fig_volume = px.line(
            df_hourly,
            x='timestamp',
            y='query_count',
            title='Query Volume (Last 24 Hours)'
        )
        st.plotly_chart(fig_volume, use_container_width=True)
        
        # Method distribution
        col1, col2 = st.columns(2)
        
        with col1:
            method_dist = query_metrics.get('method_distribution', {})
            if method_dist:
                fig_methods = px.pie(
                    values=list(method_dist.values()),
                    names=list(method_dist.keys()),
                    title="Retrieval Method Usage"
                )
                st.plotly_chart(fig_methods, use_container_width=True)
        
        with col2:
            response_times = query_metrics.get('response_times_by_method', {})
            if response_times:
                fig_times = px.bar(
                    x=list(response_times.keys()),
                    y=list(response_times.values()),
                    title="Avg Response Time by Method"
                )
                st.plotly_chart(fig_times, use_container_width=True)
    
    # Evaluation results
    st.subheader("Model Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Retrieval Method Evaluation**")
        retrieval_eval = make_api_request("/evaluation/retrieval")
        if retrieval_eval:
            eval_df = pd.DataFrame(retrieval_eval).T
            eval_df = eval_df.round(3)
            st.dataframe(eval_df, use_container_width=True)
    
    with col2:
        st.markdown("**RAG Approach Evaluation**")
        rag_eval = make_api_request("/evaluation/rag")
        if rag_eval:
            rag_df = pd.DataFrame(rag_eval).T
            rag_df = rag_df.round(3)
            st.dataframe(rag_df, use_container_width=True)

def query_history_sidebar():
    """Display query history in sidebar"""
    if st.session_state.query_history:
        st.sidebar.subheader("📝 Recent Queries")
        
        for i, query_item in enumerate(reversed(st.session_state.query_history[-5:])):
            with st.sidebar.expander(f"Query {len(st.session_state.query_history) - i}"):
                st.write(f"**Query:** {query_item['query'][:50]}...")
                st.write(f"**Time:** {query_item['timestamp']}")
                st.write(f"**Method:** {query_item['method']}")
                if query_item['enhanced']:
                    st.write("🔧 Enhanced")

def main():
    """Main application"""
    init_session_state()
    
    # Sidebar
    st.sidebar.title("🏢 Company Intelligence")
    display_system_health()
    
    # Navigation
    page = st.sidebar.selectbox(
        "Navigate to:",
        ["🔍 Search", "📊 Analytics", "ℹ️ About"]
    )
    
    query_history_sidebar()
    
    # Main content
    if page == "🔍 Search":
        query_interface()
        display_response()
    
    elif page == "📊 Analytics":
        analytics_dashboard()
    
    elif page == "ℹ️ About":
        st.title("About Indian Company Intelligence")
        st.markdown("""
        This RAG (Retrieval-Augmented Generation) system provides intelligent access to Indian company data.
        
        **Features:**
        - 🔍 **Multi-modal Search**: Vector similarity + Elasticsearch text search + hybrid approaches
        - 🤖 **Smart Generation**: Google Gemini with multiple prompt strategies
        - 🔧 **Enhanced Query Processing**: Query rewriting and document re-ranking
        - 📊 **Comprehensive Monitoring**: Real-time analytics and user feedback
        
        **Data Coverage:**
        - Company registration details
        - Financial information (authorized/paid-up capital)
        - Location and address data
        - Industry classifications
        - Corporate status and compliance
        
        **Technology Stack:**
        - **Vector Database**: Qdrant for semantic search
        - **Text Search**: Elasticsearch for keyword matching
        - **LLM**: Google Gemini for response generation
        - **API**: FastAPI for backend services
        - **Monitoring**: Grafana + PostgreSQL
        - **Deployment**: Docker Compose
        """)
        
        # System status
        st.subheader("System Information")
        system_info = make_api_request("/")
        if system_info:
            st.json(system_info)

if __name__ == "__main__":
    main()