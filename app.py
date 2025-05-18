import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time
from datetime import datetime
from datetime import timedelta

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

st.markdown("""
<div style="text-align: left; margin-bottom: 2rem;">
<svg width="95" height="26" viewBox="0 0 95 26" fill="none" xmlns="http://www.w3.org/2000/svg" class="cursor-pointer"><path d="M5.25 2H0.75C0.335786 2 0 2.33579 0 2.75V19.25C0 19.6642 0.335786 20 0.75 20H5.25C5.66421 20 6 19.6642 6 19.25V2.75C6 2.33579 5.66421 2 5.25 2Z" fill="white"></path><path d="M13.25 2H8.75C8.33579 2 8 2.33579 8 2.75V25.25C8 25.6642 8.33579 26 8.75 26H13.25C13.6642 26 14 25.6642 14 25.25V2.75C14 2.33579 13.6642 2 13.25 2Z" fill="white"></path><path d="M78.2335 20.5641C77.0029 20.5641 75.8848 20.3041 74.8795 19.7841C73.8915 19.2641 73.1028 18.5101 72.5135 17.5221C71.9415 16.5341 71.6555 15.3467 71.6555 13.9601V13.6221C71.6555 12.2354 71.9415 11.0567 72.5135 10.0861C73.1028 9.09807 73.8915 8.34407 74.8795 7.82407C75.8848 7.28673 77.0029 7.01807 78.2335 7.01807C79.4642 7.01807 80.5128 7.2434 81.3795 7.69407C82.2462 8.14473 82.9395 8.74273 83.4595 9.48807C83.9969 10.2334 84.3435 11.0567 84.4995 11.9581L81.8995 12.5041C81.8129 11.9321 81.6308 11.4121 81.3535 10.9441C81.0762 10.4761 80.6862 10.1034 80.1835 9.82607C79.6809 9.54873 79.0482 9.41007 78.2855 9.41007C77.5402 9.41007 76.8642 9.5834 76.2575 9.93007C75.6682 10.2594 75.2002 10.7447 74.8535 11.3861C74.5068 12.0101 74.3335 12.7727 74.3335 13.6741V13.9081C74.3335 14.8094 74.5068 15.5807 74.8535 16.2221C75.2002 16.8634 75.6682 17.3487 76.2575 17.6781C76.8642 18.0074 77.5402 18.1721 78.2855 18.1721C79.4122 18.1721 80.2702 17.8861 80.8595 17.3141C81.4488 16.7247 81.8215 15.9794 81.9775 15.0781L84.5775 15.6761C84.3695 16.5601 83.9969 17.3747 83.4595 18.1201C82.9395 18.8654 82.2462 19.4634 81.3795 19.9141C80.5128 20.3474 79.4642 20.5641 78.2335 20.5641Z" fill="white"></path><path d="M67.4473 20.2V7.382H70.1252V20.2H67.4473ZM68.7992 5.64C68.2792 5.64 67.8372 5.47533 67.4732 5.146C67.1266 4.79933 66.9532 4.35733 66.9532 3.82C66.9532 3.28267 67.1266 2.84933 67.4732 2.52C67.8372 2.17333 68.2792 2 68.7992 2C69.3366 2 69.7786 2.17333 70.1252 2.52C70.4719 2.84933 70.6452 3.28267 70.6452 3.82C70.6452 4.35733 70.4719 4.79933 70.1252 5.146C69.7786 5.47533 69.3366 5.64 68.7992 5.64Z" fill="white"></path><path d="M60.021 20.564C58.773 20.564 57.811 20.3387 57.135 19.888C56.4763 19.4373 55.9823 18.9347 55.653 18.38H55.237V20.2H52.611V2H55.289V9.124H55.705C55.913 8.77733 56.1903 8.448 56.537 8.136C56.8836 7.80667 57.343 7.538 57.915 7.33C58.487 7.122 59.189 7.018 60.021 7.018C61.0956 7.018 62.0836 7.278 62.985 7.798C63.8863 8.318 64.6056 9.072 65.143 10.06C65.6803 11.048 65.949 12.2267 65.949 13.596V13.986C65.949 15.3727 65.6716 16.56 65.117 17.548C64.5796 18.5187 63.8603 19.264 62.959 19.784C62.075 20.304 61.0956 20.564 60.021 20.564ZM59.241 18.224C60.4023 18.224 61.3556 17.8513 62.101 17.106C62.8636 16.3607 63.245 15.2947 63.245 13.908V13.674C63.245 12.3047 62.8723 11.2473 62.127 10.502C61.3816 9.75667 60.4196 9.384 59.241 9.384C58.097 9.384 57.1436 9.75667 56.381 10.502C55.6356 11.2473 55.263 12.3047 55.263 13.674V13.908C55.263 15.2947 55.6356 16.3607 56.381 17.106C57.1436 17.8513 58.097 18.224 59.241 18.224Z" fill="white"></path><path d="M43.3742 20.4341C42.4035 20.4341 41.5369 20.2174 40.7742 19.7841C40.0115 19.3507 39.4135 18.7354 38.9802 17.9381C38.5469 17.1407 38.3302 16.1874 38.3302 15.0781V7.38208H41.0082V14.8961C41.0082 16.0054 41.2855 16.8287 41.8402 17.3661C42.3949 17.8861 43.1662 18.1461 44.1542 18.1461C45.2462 18.1461 46.1215 17.7821 46.7802 17.0541C47.4562 16.3087 47.7942 15.2427 47.7942 13.8561V7.38208H50.4722V20.2001H47.8462V18.2761H47.4302C47.1875 18.7961 46.7542 19.2901 46.1302 19.7581C45.5062 20.2087 44.5875 20.4341 43.3742 20.4341Z" fill="white"></path><path d="M33.66 25.4001V18.4581H33.244C33.0533 18.8047 32.776 19.1427 32.412 19.4721C32.048 19.7841 31.58 20.0441 31.008 20.2521C30.4533 20.4601 29.76 20.5641 28.928 20.5641C27.8533 20.5641 26.8653 20.3041 25.964 19.7841C25.0627 19.2641 24.3433 18.5187 23.806 17.5481C23.2687 16.5601 23 15.3727 23 13.9861V13.5961C23 12.2094 23.2687 11.0307 23.806 10.0601C24.3607 9.07207 25.0887 8.31807 25.99 7.79807C26.8913 7.27807 27.8707 7.01807 28.928 7.01807C30.176 7.01807 31.1293 7.2434 31.788 7.69407C32.464 8.14473 32.9667 8.65607 33.296 9.22807H33.712V7.38207H36.338V25.4001H33.66ZM29.682 18.2241C30.8607 18.2241 31.8227 17.8514 32.568 17.1061C33.3133 16.3607 33.686 15.2947 33.686 13.9081V13.6741C33.686 12.3047 33.3047 11.2474 32.542 10.5021C31.7967 9.75673 30.8433 9.38407 29.682 9.38407C28.538 9.38407 27.5847 9.75673 26.822 10.5021C26.0767 11.2474 25.704 12.3047 25.704 13.6741V13.9081C25.704 15.2947 26.0767 16.3607 26.822 17.1061C27.5847 17.8514 28.538 18.2241 29.682 18.2241Z" fill="white"></path></svg>
</div>
""", unsafe_allow_html=True)

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

    if not df_last_6h.empty:
        mean_hashrate_6h = df_last_6h['pool_hashrate'].mean() / 1e6  # Convert to MH/s
    else:
        mean_hashrate_6h = 0

# Metrics Cards
if not df.empty:
    latest = df.iloc[-1]
    mean_hashrate = df['pool_hashrate'].mean()
    mean_hashrate_mhs = mean_hashrate / 1e6
    block_count = int(df['pool_blocks_found'].max())
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
