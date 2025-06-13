"""
Simplified Streamlit UI for Indian Company Intelligence RAG System
This version works standalone without requiring the complex Docker setup
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="Indian Company Intelligence",
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    """Initialize session state variables"""
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    if 'current_response' not in st.session_state:
        st.session_state.current_response = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = f"user_{int(time.time())}"

def mock_api_response(query: str) -> dict:
    """Mock API response for demonstration"""
    return {
        "query": query,
        "response": f"Based on the available data, I found several companies matching your query: '{query}'. Here are some technology companies in Karnataka with significant capital investments:\n\n1. **Infosys Limited** - Bangalore, Karnataka\n   - Industry: Information Technology Services\n   - Capital: ₹500+ Crores\n   - Founded: 1981\n\n2. **Wipro Limited** - Bangalore, Karnataka\n   - Industry: IT Services and Consulting\n   - Capital: ₹300+ Crores\n   - Founded: 1945\n\n3. **Mindtree Ltd** - Bangalore, Karnataka\n   - Industry: Digital Technology Services\n   - Capital: ₹200+ Crores\n   - Founded: 1999\n\nThese companies represent the leading technology sector in Karnataka with substantial capital bases and strong market presence.",
        "retrieval_method": "hybrid",
        "prompt_type": "detailed",
        "retrieved_documents": [
            {
                "company_name": "Infosys Limited",
                "state": "Karnataka",
                "city": "Bangalore",
                "industry_classification": "Information Technology",
                "score": 0.95
            },
            {
                "company_name": "Wipro Limited", 
                "state": "Karnataka",
                "city": "Bangalore",
                "industry_classification": "IT Services",
                "score": 0.91
            },
            {
                "company_name": "Mindtree Ltd",
                "state": "Karnataka", 
                "city": "Bangalore",
                "industry_classification": "Digital Technology",
                "score": 0.87
            }
        ],
        "response_time_ms": 850,
        "num_results": 3
    }

def display_query_response(response_data: dict):
    """Display query response"""
    if not response_data:
        return
    
    st.markdown("### 🎯 Response")
    st.markdown(response_data.get("response", "No response available"))
    
    # Display retrieved companies
    documents = response_data.get("retrieved_documents", [])
    if documents:
        st.markdown("### 📊 Retrieved Companies")
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(documents)
        if not df.empty:
            df['score'] = df['score'].round(3)
            st.dataframe(df, use_container_width=True)
    
    # Display metadata
    with st.expander("🔍 Query Details"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Response Time", f"{response_data.get('response_time_ms', 0)}ms")
        with col2:
            st.metric("Results Found", response_data.get('num_results', 0))
        with col3:
            st.metric("Retrieval Method", response_data.get('retrieval_method', 'N/A'))

def query_interface():
    """Main query interface"""
    st.title("🏢 Indian Company Intelligence")
    st.markdown("Ask questions about Indian companies using natural language")
    
    # Information about this being a demo
    st.info("🔧 **Demo Mode**: This is a simplified version running without the full Docker stack. The responses are mock data for demonstration purposes.")
    
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
                help="Choose how to search for relevant companies"
            )
        
        with col2:
            prompt_type = st.selectbox(
                "Response Style:",
                ["detailed", "concise", "analytical"],
                help="Choose the style of response"
            )
        
        with col3:
            top_k = st.slider(
                "Max Results:",
                min_value=1,
                max_value=20,
                value=5,
                help="Maximum number of companies to retrieve"
            )
    
    # Process query
    if search_button and query.strip():
        with st.spinner("🔍 Searching company database..."):
            # Simulate API delay
            time.sleep(1)
            
            # Get mock response
            response_data = mock_api_response(query)
            st.session_state.current_response = response_data
            
            # Add to history
            st.session_state.query_history.append({
                "timestamp": datetime.now(),
                "query": query,
                "response": response_data
            })
        
        st.rerun()
    
    # Display current response
    if st.session_state.current_response:
        display_query_response(st.session_state.current_response)

def sidebar_content():
    """Sidebar content"""
    st.sidebar.title("🏢 Company Intelligence")
    
    # System status (mock)
    st.sidebar.markdown("### 📊 System Status")
    st.sidebar.success("🟢 Demo Mode Active")
    
    # Quick examples
    st.sidebar.markdown("### 💡 Example Queries")
    example_queries = [
        "Technology companies in Karnataka",
        "Manufacturing companies in Maharashtra", 
        "Companies with capital > 100 crores",
        "Startups in Bangalore",
        "Pharmaceutical companies in India"
    ]
    
    for i, example in enumerate(example_queries):
        if st.sidebar.button(f"📝 {example}", key=f"example_{i}"):
            st.session_state.main_query = example
            st.rerun()
    
    # Query history
    if st.session_state.query_history:
        st.sidebar.markdown("### 📜 Recent Queries")
        for i, item in enumerate(st.session_state.query_history[-5:]):  # Show last 5
            timestamp = item["timestamp"].strftime("%H:%M")
            query_preview = item["query"][:30] + "..." if len(item["query"]) > 30 else item["query"]
            if st.sidebar.button(f"{timestamp}: {query_preview}", key=f"history_{i}"):
                st.session_state.current_response = item["response"]
                st.rerun()

def main():
    """Main application"""
    init_session_state()
    
    # Sidebar
    sidebar_content()
    
    # Main content
    query_interface()
    
    # Footer
    st.markdown("---")
    st.markdown("🚀 **Note**: This is a demo version. For the full experience with real-time data processing, please set up the complete Docker environment as described in the project README.")

if __name__ == "__main__":
    main()