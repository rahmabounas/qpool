import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time
from datetime import datetime

# Configuration
GITHUB_RAW_URL = "https://raw.githubusercontent.com/B4k469420/qpool/refs/heads/main/data/pool_stats_V2.csv"
REFRESH_INTERVAL = 5  # seconds

# GitHub settings
GITHUB_OWNER = "B4k469420"
GITHUB_REPO = "qpool"
GITHUB_BRANCH = "main"

# Setup page
st.set_page_config(
    page_title="Qubic Monero Pool Dashboard",
    page_icon="⛏️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    body, .main, .block-container {
        background-color: #202e3c !important;
        color: white !important;
    }

    .metric-card {
        background: rgba(32, 46, 60, 0.9);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(255,255,255,0.1);
        color: white;
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #4cc9f0;
        margin: 0.2rem 0;
    }

    .delta-value {
        text-align: right;
        font-size: 0.9rem;
        color: gray;
        margin-top: auto;
    }

    .block-indicator {
        color: #f72585;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=5, show_spinner="Loading latest data...")
def load_data():
    url = GITHUB_RAW_URL.format(owner=GITHUB_OWNER, repo=GITHUB_REPO, branch=GITHUB_BRANCH)
    try:
        timestamp = int(time.time())
        df = pd.read_csv(f"{url}?t={timestamp}")

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        df['pool_hashrate_mhs'] = df['pool_hashrate'] / 1e6
        df['network_hashrate_ghs'] = df['network_hashrate'] / 1e9
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

# Load Data
df = load_data()

# Metrics Cards
if not df.empty:
    latest = df.iloc[-1]
    mean_hashrate = df['pool_hashrate'].mean()
    mean_hashrate_mhs = mean_hashrate / 1e6
    block_count = int(df['blocks_found'].max())
    delta_pool = df['pool_hashrate_mhs'].diff().iloc[-1]
    delta_net = df['network_hashrate_ghs'].diff().iloc[-1]

    # Summary cards
    cols = st.columns(4)
    with cols[0]:
        st.markdown(f"""
        <div class="metric-card">
            <div>POOL HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['pool_hashrate'])}</div>
            <div class="delta-value">Δ {delta_pool:+.2f} MH/s</div>
        </div>
        """, unsafe_allow_html=True)

    with cols[1]:
        st.markdown(f"""
        <div class="metric-card">
            <div>NETWORK HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['network_hashrate'])}</div>
            <div class="delta-value">Δ {delta_net:+.2f} GH/s</div>
        </div>
        """, unsafe_allow_html=True)

    with cols[2]:
        block_status = "🟢 Found!" if latest['block_found'] else "🔴 Working"
        st.markdown(f"""
        <div class="metric-card">
            <div>BLOCKS FOUND</div>
            <div class="metric-value">{int(latest['blocks_found'])}</div>
            <div class="block-indicator">{block_status}</div>
        </div>
        """, unsafe_allow_html=True)

    with cols[3]:
        st.markdown(f"""
        <div class="metric-card">
            <div>MEAN POOL HASHRATE</div>
            <div class="metric-value">{mean_hashrate_mhs:.2f} MH/s</div>
            <div class="delta-value">({len(df)} samples)</div>
        </div>
        """, unsafe_allow_html=True)

    # Chart: Pool & Network Hashrate
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['pool_hashrate_mhs'],
        mode='lines',
        name='Pool Hashrate (MH/s)',
        line=dict(color='#4cc9f0', shape='spline', smoothing=1.3)
    ))

    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['network_hashrate_ghs'],
        mode='lines',
        name='Network Hashrate (GH/s)',
        line=dict(color='#f72585', shape='spline', smoothing=1.3)
    ))

    # Add block found markers
    block_times = df[df['block_found']]['timestamp']
    for block_time in block_times:
        y_val = df[df['timestamp'] == block_time]['pool_hashrate_mhs'].values[0]
        fig.add_annotation(
            x=block_time,
            y=y_val,
            text="⭐",
            showarrow=True,
            arrowhead=1,
            ax=0,
            ay=-40,
            font=dict(size=20, color="#FFD700")
        )

    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor='#202e3c',
        paper_bgcolor='#202e3c',
        font=dict(color="white"),
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=20, b=20),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)', zeroline=False),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)', zeroline=False)
    )

    st.plotly_chart(fig, use_container_width=True, key="hashrate_chart")

    if st.button("🔄 Manual Refresh"):
        st.cache_data.clear()
        st.rerun()

else:
    st.warning("No data available. Waiting for first data points...")
