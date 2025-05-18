import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time
from datetime import datetime, timedelta

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
        df['block_found'] = df['pool_blocks_found'].diff().fillna(0) > 0
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

# Calculate mean hashrate for the last 6 hours
if not df.empty:
    six_hours_ago = df['timestamp'].max() - timedelta(hours=6)
    df_last_6h = df[df['timestamp'] >= six_hours_ago]
    mean_hashrate_6h = df_last_6h['pool_hashrate'].mean() / 1e6 if not df_last_6h.empty else 0

# Metrics Cards
if not df.empty:
    latest = df.iloc[-1]
    mean_hashrate = df['pool_hashrate'].mean()
    mean_hashrate_mhs = mean_hashrate / 1e6
    block_count = int(df['pool_blocks_found'].max())
    delta_pool = df['pool_hashrate_mhs'].diff().iloc[-1]
    delta_net = df['network_hashrate_ghs'].diff().iloc[-1]

    # Calculate previous ATH (excluding current value)
    previous_ath = df['pool_hashrate'][:-1].max()
    previous_ath_mhs = previous_ath / 1e6

    cols = st.columns(4)
    with cols[0]:
        st.markdown(f"""
        <div class="metric-card">
            <div>POOL HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['pool_hashrate'])}</div>
            <div class="delta-value">ATH: {previous_ath_mhs:.2f} MH/s<br>Δ {delta_pool:+.2f} MH/s</div>
        </div>
        """, unsafe_allow_html=True)

    with cols[1]:
        st.markdown(f"""
        <div class="metric-card">
            <div>MEAN HASHRATE (6H)</div>
            <div class="metric-value">{mean_hashrate_6h:.2f} MH/s</div>
            <div class="delta-value">Last 6 hours</div>
        </div>
        """, unsafe_allow_html=True)

    with cols[2]:
        block_status = "🟢 Found!" if latest['block_found'] else "🔴 Working"
        st.markdown(f"""
        <div class="metric-card">
            <div>BLOCKS FOUND</div>
            <div class="metric-value">{int(latest['pool_blocks_found'])}</div>
            <div class="block-indicator">{block_status}</div>
        </div>
        """, unsafe_allow_html=True)

    with cols[3]:
        st.markdown(f"""
        <div class="metric-card">
            <div>NETWORK HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['network_hashrate'])}</div>
            <div class="delta-value">Δ {delta_net:+.2f} GH/s</div>
        </div>
        """, unsafe_allow_html=True)



    # Chart: Pool & Network Hashrate
    # Chart Section
if not df.empty:
    fig = go.Figure()

    # Add Pool Hashrate (MH/s)
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['pool_hashrate_mhs'],
        mode='lines+markers',
        name='Pool Hashrate (MH/s)',
        line=dict(color='limegreen', width=2),
        marker=dict(size=3),
        yaxis='y1'
    ))

    # Add Network Hashrate (GH/s), scaled down to match MH/s range
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['network_hashrate_ghs'] * 1000,  # convert to MH/s for visual scaling
        mode='lines',
        name='Network Hashrate (GH/s)',
        line=dict(color='deepskyblue', width=1, dash='dot'),
        hovertemplate='%{y:.2f} MH/s<br>(GH/s: %{customdata:.2f})<extra></extra>',
        customdata=df['network_hashrate_ghs'].values.reshape(-1, 1),
        yaxis='y1'
    ))

    # Chart Layout
    fig.update_layout(
        title='Pool & Network Hashrate Over Time',
        xaxis=dict(title='Timestamp'),
        yaxis=dict(
            title='Hashrate (MH/s)',
            tickformat=',.0f',
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(l=40, r=20, t=40, b=40),
        height=450
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No data available to display.")
