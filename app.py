import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime

# Configuration
GITHUB_RAW_URL = "https://raw.githubusercontent.com/{owner}/{repo}/{branch}/data/pool_stats.csv"
REFRESH_INTERVAL = 5  # seconds

# GitHub settings - REPLACE THESE WITH YOUR INFO
GITHUB_OWNER = "your_github_username"
GITHUB_REPO = "your_repo_name"
GITHUB_BRANCH = "main"

# Set up page
st.set_page_config(
    page_title="Monero Pool Dashboard",
    page_icon="⛏️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data_from_github():
    url = GITHUB_RAW_URL.format(
        owner=GITHUB_OWNER,
        repo=GITHUB_REPO,
        branch=GITHUB_BRANCH
    )
    try:
        df = pd.read_csv(url)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        df['pool_hashrate_mhs'] = df['pool_hashrate'] / 1e6
        df['network_hashrate_ghs'] = df['network_hashrate'] / 1e9
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

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = 0

# Main app layout
st.title("⛏️ Monero Pool Dashboard")
st.markdown("---")

# Create containers for dynamic content
current_stats = st.container()
chart_container1 = st.container()
chart_container2 = st.container()

# Load data
df = load_data_from_github()

# Display current stats
with current_stats:
    if not df.empty:
        latest = df.iloc[-1]
        cols = st.columns(3)
        with cols[0]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">POOL HASHRATE</div>
                <div class="metric-value">{format_hashrate(latest['pool_hashrate'])}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">NETWORK HASHRATE</div>
                <div class="metric-value">{format_hashrate(latest['network_hashrate'])}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[2]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">BLOCKS FOUND</div>
                <div class="metric-value">{int(latest['cumulative_blocks'])}</div>
            </div>
            """, unsafe_allow_html=True)

# Create visualizations
if not df.empty:
    with chart_container1:
        st.subheader("Hashrate Comparison")
        fig1 = px.line(df, x='timestamp', 
                      y=['pool_hashrate_mhs', 'network_hashrate_ghs'],
                      labels={
                          'value': 'Hashrate',
                          'variable': 'Metric',
                          'pool_hashrate_mhs': 'Pool (MH/s)',
                          'network_hashrate_ghs': 'Network (GH/s)'
                      },
                      color_discrete_sequence=['#4cc9f0', '#f72585'])
        fig1.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        st.plotly_chart(fig1, use_container_width=True, key="hashrate_chart")
    
    with chart_container2:
        st.subheader("Blocks Found Over Time")
        fig2 = px.area(df, x='timestamp', y='cumulative_blocks',
                      labels={'cumulative_blocks': 'Total Blocks Found'},
                      color_discrete_sequence=['#7209b7'])
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            hovermode="x"
        )
        st.plotly_chart(fig2, use_container_width=True, key="blocks_chart")
else:
    st.warning("No data available yet. Please check back later.")

# Auto-refresh logic
if time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
    st.session_state.last_refresh = time.time()
    st.rerun()
