import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
from datetime import datetime
import time

# Configuration
GITHUB_RAW_URL = "https://raw.githubusercontent.com/B4k469420/qpool/refs/heads/main/data/pool_stats.csv"
REFRESH_INTERVAL = 5  # seconds

# GitHub settings - REPLACE THESE WITH YOUR INFO
GITHUB_OWNER = "B4k469420"
GITHUB_REPO = "qpool"
GITHUB_BRANCH = "main"

# Set up page
st.set_page_config(
    page_title="Monero Pool Dashboard",
    page_icon="⛏️",
    layout="wide"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .header-style {
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .metric-card {
        background-color: #1a1a2e;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #4cc9f0;
    }
    .metric-label {
        font-size: 14px;
        color: #a8dadc;
    }
    .plot-container {
        background-color: #16213e;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache data for 5 minutes
def load_data_from_github():
    url = GITHUB_RAW_URL.format(
        owner=GITHUB_OWNER,
        repo=GITHUB_REPO,
        branch=GITHUB_BRANCH
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_csv(url)
        
        # Convert and clean data
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        df['pool_hashrate_mhs'] = df['pool_hashrate'] / 1e6  # Convert to MH/s
        df['network_hashrate_ghs'] = df['network_hashrate'] / 1e9  # Convert to GH/s
        
        # Calculate cumulative blocks
        df['cumulative_blocks'] = df['blocks_found'].cumsum()
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def format_hashrate(h):
    if h >= 1e9:
        return f"{h/1e9:.2f} GH/s"
    elif h >= 1e6:
        return f"{h/1e6:.2f} MH/s"
    elif h >= 1e3:
        return f"{h/1e3:.2f} KH/s"
    else:
        return f"{h:.2f} H/s"

# App layout
st.title("⛏️ Monero Pool Dashboard")
st.markdown("---")

# Create placeholder elements
current_stats_placeholder = st.empty()
chart_placeholder1 = st.empty()
chart_placeholder2 = st.empty()

# Main loop
while True:
    # Load data
    df = load_data_from_github()
    
    # Display current stats if available
    if not df.empty:
        latest = df.iloc[-1]
        
        with current_stats_placeholder.container():
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">POOL HASHRATE</div>
                    <div class="metric-value">{format_hashrate(latest['pool_hashrate'])}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">NETWORK HASHRATE</div>
                    <div class="metric-value">{format_hashrate(latest['network_hashrate'])}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">BLOCKS FOUND</div>
                    <div class="metric-value">{int(latest['cumulative_blocks'])}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Create visualizations
    if not df.empty:
        with chart_placeholder1.container():
            st.markdown('<div class="header-style">Hashrate Comparison</div>', unsafe_allow_html=True)
            
            # Create figure with secondary y-axis
            fig = px.line(df, x='timestamp', 
                          y=['pool_hashrate_mhs', 'network_hashrate_ghs'],
                          labels={
                              'value': 'Hashrate',
                              'variable': 'Metric',
                              'pool_hashrate_mhs': 'Pool (MH/s)',
                              'network_hashrate_ghs': 'Network (GH/s)'
                          },
                          color_discrete_sequence=['#4cc9f0', '#f72585'])
            
            # Update layout
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                hovermode="x unified",
                margin=dict(l=20, r=20, t=30, b=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with chart_placeholder2.container():
            st.markdown('<div class="header-style">Blocks Found Over Time</div>', unsafe_allow_html=True)
            
            fig = px.area(df, x='timestamp', y='cumulative_blocks',
                          labels={'cumulative_blocks': 'Total Blocks Found'},
                          color_discrete_sequence=['#7209b7'])
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                hovermode="x",
                margin=dict(l=20, r=20, t=30, b=20)
            )
            
            fig.update_traces(hovertemplate="%{y} blocks")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available yet. Please check back later.")
    
    # Wait before refreshing
    time.sleep(REFRESH_INTERVAL)
