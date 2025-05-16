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

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: rgba(26, 26, 46, 0.7);
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #4cc9f0;
        margin: 0.5rem 0;
    }
    .block-indicator {
        color: #f72585;
        font-weight: bold;
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
        df['block_found'] = df['blocks_found'].diff().fillna(0) > 0
        
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
        block_status = "🟢 Found!" if latest['block_found'] else "🔴 Searching"
        st.markdown(f"""
        <div class="metric-card">
            <div>BLOCKS FOUND</div>
            <div class="metric-value">{int(latest['cumulative_blocks'])}</div>
            <div class="block-indicator">{block_status}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Hashrate Trends with Block Indicators
    fig = px.line(df, x='timestamp', 
                 y=['pool_hashrate_mhs', 'network_hashrate_ghs'],
                 labels={'value': 'Hashrate', 'variable': ''},
                 color_discrete_map={
                     'pool_hashrate_mhs': '#4cc9f0',
                     'network_hashrate_ghs': '#f72585'
                 })
    
    # Add block indicators as stars
    block_times = df[df['block_found']]['timestamp']
    for block_time in block_times:
        fig.add_annotation(
            x=block_time,
            y=df[df['timestamp'] == block_time]['pool_hashrate_mhs'].values[0],
            text="⭐",
            showarrow=True,
            arrowhead=1,
            ax=0,
            ay=-40,
            font=dict(size=20, color="#FFD700")
        )
    
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=20, b=20)
    )
    st.plotly_chart(fig, use_container_width=True, key="hashrate_chart")

else:
    st.warning("No data available. Waiting for first data points...")

# Auto-refresh
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
