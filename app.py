import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time
from datetime import datetime

# Configuration
GITHUB_RAW_URL = "https://raw.githubusercontent.com/B4k469420/qpool/refs/heads/main/data/pool_stats.csv"
REFRESH_INTERVAL = 5  # seconds

# GitHub settings - REPLACE THESE WITH YOUR INFO
GITHUB_OWNER = "B4k469420"
GITHUB_REPO = "qpool"
GITHUB_BRANCH = "main"

# Setup page
st.set_page_config(
    page_title="Live Monero Pool Dashboard",
    page_icon="⛏️",
    layout="wide"
)

# Custom CSS for better visuals
st.markdown("""
<style>
    .metric-card {
        background: rgba(26, 26, 46, 0.7);
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255,255,255,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #4cc9f0;
        margin: 0.5rem 0;
    }
    .stAlert { border-radius: 10px; }
    [data-testid="stExpander"] .streamlit-expanderHeader {
        background-color: rgba(22, 33, 62, 0.5);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=REFRESH_INTERVAL, show_spinner="Loading latest data...")
def load_data():
    url = GITHUB_RAW_URL.format(
        owner=GITHUB_OWNER,
        repo=GITHUB_REPO,
        branch=GITHUB_BRANCH
    )
    try:
        # Add cache-busting parameter
        timestamp = int(time.time())
        df = pd.read_csv(f"{url}?t={timestamp}")
        
        # Data processing
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Convert hashrates
        df['pool_hashrate_mhs'] = df['pool_hashrate'] / 1e6
        df['network_hashrate_ghs'] = df['network_hashrate'] / 1e9
        
        # Calculate blocks
        df['cumulative_blocks'] = df['blocks_found'].cumsum()
        df['new_blocks'] = df['blocks_found'].diff().fillna(0)
        
        return df
    except Exception as e:
        st.error(f"⚠️ Data loading error: {str(e)}")
        return pd.DataFrame()

def format_hashrate(h):
    if h >= 1e9: return f"{h/1e9:.2f} GH/s"
    elif h >= 1e6: return f"{h/1e6:.2f} MH/s"
    elif h >= 1e3: return f"{h/1e3:.2f} KH/s"
    return f"{h:.2f} H/s"

# Main app
st.title("⛏️ Live Monero Pool Dashboard")
st.caption(f"Updated every {REFRESH_INTERVAL} seconds | Last refresh: {datetime.now().strftime('%H:%M:%S')}")

# Load data
df = load_data()

if not df.empty:
    latest = df.iloc[-1]
    
    # Current stats row
    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"""
        <div class="metric-card">
            <div>POOL HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['pool_hashrate'])}</div>
            <div>Δ {df['pool_hashrate_mhs'].diff().iloc[-1]:+.2f} MH/s</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        st.markdown(f"""
        <div class="metric-card">
            <div>NETWORK HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['network_hashrate'])}</div>
            <div>Δ {df['network_hashrate_ghs'].diff().iloc[-1]:+.2f} GH/s</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        st.markdown(f"""
        <div class="metric-card">
            <div>BLOCKS FOUND</div>
            <div class="metric-value">{int(latest['cumulative_blocks'])}</div>
            <div>+{int(latest['new_blocks'])} since last update</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts
    with st.expander("📈 Hashrate Trends", expanded=True):
        fig = px.line(df, x='timestamp', 
                    y=['pool_hashrate_mhs', 'network_hashrate_ghs'],
                    labels={'value': 'Hashrate', 'variable': ''},
                    color_discrete_map={
                        'pool_hashrate_mhs': '#4cc9f0',
                        'network_hashrate_ghs': '#f72585'
                    })
        fig.update_layout(
            hovermode="x unified",
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", y=1.1),
            margin=dict(t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True, key="hashrate_chart")
    
    with st.expander("🧱 Block Discovery", expanded=True):
        fig = px.bar(df[df['new_blocks'] > 0], x='timestamp', y='new_blocks',
                    labels={'new_blocks': 'Blocks Found'},
                    color_discrete_sequence=['#7209b7'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title=None,
            margin=dict(t=20, b=20)
        st.plotly_chart(fig, use_container_width=True, key="blocks_chart")
else:
    st.warning("No data available. Waiting for first data points...")

# Auto-refresh logic
if st.button("🔄 Manual Refresh"):
    st.cache_data.clear()
    st.rerun()

# JavaScript auto-refresh
st.components.v1.html(f"""
<script>
    setTimeout(function(){{
        window.location.reload();
    }}, {REFRESH_INTERVAL * 1000});
</script>
""", height=0)
