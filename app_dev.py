import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time
import ccxt
import numpy as np
from datetime import datetime
from datetime import timedelta
from plotly.subplots import make_subplots

# Configuration
GITHUB_RAW_URL = "http://66.179.92.83/data/pool_stats_V2.csv"
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

# Initialize exchange
GATEIO_EXCHANGE = ccxt.mexc({
    'enableRateLimit': True,
    'rateLimit': 3000,  # requests per minute
})

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
    
    .price-positive {
        color: #4ade80;
    }
    
    .price-negative {
        color: #f87171;
    }
    
    .chart-container {
        background: rgba(32, 46, 60, 0.7);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
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

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_price_data():
    try:
        # Fetch current prices
        xmr_ticker = GATEIO_EXCHANGE.fetch_ticker('XMR/USDT')
        qubic_ticker = GATEIO_EXCHANGE.fetch_ticker('QUBIC/USDT')
        
        # Fetch historical data (last 24 hours)
        since = GATEIO_EXCHANGE.milliseconds() - 86400 * 1000  # 24 hours ago
        xmr_ohlcv = GATEIO_EXCHANGE.fetch_ohlcv('XMR/USDT', '1h', since=since)
        qubic_ohlcv = GATEIO_EXCHANGE.fetch_ohlcv('QUBIC/USDT', '1h', since=since)
        
        # Create DataFrames
        xmr_df = pd.DataFrame(xmr_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        xmr_df['timestamp'] = pd.to_datetime(xmr_df['timestamp'], unit='ms')
        xmr_df['symbol'] = 'XMR'
        
        qubic_df = pd.DataFrame(qubic_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        qubic_df['timestamp'] = pd.to_datetime(qubic_df['timestamp'], unit='ms')
        qubic_df['symbol'] = 'QUBIC'
        
        # Combine and return
        price_df = pd.concat([xmr_df, qubic_df])
        current_prices = {
            'XMR': xmr_ticker['last'],
            'QUBIC': qubic_ticker['last'],
            'XMR_change': xmr_ticker['percentage'],
            'QUBIC_change': qubic_ticker['percentage']
        }
        return price_df, current_prices
    except Exception as e:
        st.error(f"Error fetching price data: {str(e)}")
        return pd.DataFrame(), {}

def format_hashrate(h):
    if h >= 1e9: return f"{h/1e9:.2f} GH/s"
    elif h >= 1e6: return f"{h/1e6:.2f} MH/s"
    elif h >= 1e3: return f"{h/1e3:.2f} KH/s"
    return f"{h:.2f} H/s"

def format_timespan(delta):
    if delta.days > 0:
        return f"{delta.days}d {delta.seconds//3600}h ago"
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    return f"{hours}h {minutes}m ago"

def downsample_data(df, interval='5T'):
    """Downsample data while preserving important points (ATH, blocks found)."""
    if df.empty:
        return df

    # Identify important points to keep
    ath_idx = df['pool_hashrate'].idxmax()
    block_indices = df[df['block_found']].index

    # Downsample main data
    df_downsampled = df.resample(interval, on='timestamp').agg({
        'pool_hashrate': 'mean',
        'pool_hashrate_mhs': 'mean',
        'network_hashrate': 'mean',
        'network_hashrate_ghs': 'mean',
        'pool_blocks_found': 'last',
        'block_found': 'any'
    }).reset_index()

    # Ensure timestamp is datetime
    df_downsampled['timestamp'] = pd.to_datetime(df_downsampled['timestamp'])

    # Add ATH point if it's not already in downsampled range
    ath_timestamp = df.loc[ath_idx, 'timestamp']
    
    if not ((df_downsampled['timestamp'] >= ath_timestamp - pd.Timedelta(interval)) & 
            (df_downsampled['timestamp'] <= ath_timestamp + pd.Timedelta(interval))).any():
            df_downsampled = pd.concat([df_downsampled, df.loc[[ath_idx]]], ignore_index=True)

    # Add all block points ("stars") if not already in the downsampled set
    for idx in block_indices:
        block_time = df.loc[idx, 'timestamp']
        if not ((df_downsampled['timestamp'] >= block_time - pd.Timedelta(interval)) & 
                (df_downsampled['timestamp'] <= block_time + pd.Timedelta(interval))).any():
            df_downsampled = pd.concat([df_downsampled, df.loc[[idx]]], ignore_index=True)

    # Final clean-up
    df_downsampled = df_downsampled.sort_values('timestamp').drop_duplicates('timestamp', keep='last')
    df_downsampled['block_found'] = df_downsampled['pool_blocks_found'].diff().fillna(0) > 0

    return df_downsampled

# Load Data
df = load_data()
price_df, current_prices = fetch_price_data()

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
    ath_date = df.loc[df['pool_hashrate'] == previous_ath, 'timestamp'].iloc[0].strftime('%Y-%m-%d')
    
    # Calculate time since last block
    if df['block_found'].any():
        last_block_time = df[df['block_found']]['timestamp'].iloc[-1]
        time_since_block = format_timespan(latest['timestamp'] - last_block_time)
    else:
        time_since_block = "No blocks found yet"

    cols = st.columns(6)
    with cols[0]:
        st.markdown(f"""
        <div class="metric-card">
            <div>POOL HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['pool_hashrate'])}</div>
            <div class="delta-value">ATH: {previous_ath_mhs:.2f} MH/s ({ath_date})</div>
        </div>
        """, unsafe_allow_html=True)

    with cols[1]:
        st.markdown(f"""
        <div class="metric-card">
            <div>MEAN HASHRATE (6H)</div>
            <div class="metric-value">{mean_hashrate_6h:.2f} MH/s</div>
        </div>
        """, unsafe_allow_html=True)

    with cols[2]:
        st.markdown(f"""
        <div class="metric-card">
            <div>BLOCKS FOUND</div>
            <div class="metric-value">{int(latest['pool_blocks_found'])}</div>
            <div class="time-since-block">Last block: {time_since_block}</div>
        </div>
        """, unsafe_allow_html=True)

    with cols[3]:
        st.markdown(f"""
        <div class="metric-card">
            <div>NETWORK HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['network_hashrate'])}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with cols[4]:
        price_change_class = "price-positive" if current_prices.get('XMR_change', 0) >= 0 else "price-negative"
        st.markdown(f"""
        <div class="metric-card">
            <div>XMR PRICE</div>
            <div class="metric-value">${current_prices.get('XMR', 0):.2f}</div>
            <div class="delta-value {price_change_class}">{current_prices.get('XMR_change', 0):.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    with cols[5]:
        price_change_class = "price-positive" if current_prices.get('QUBIC_change', 0) >= 0 else "price-negative"
        st.markdown(f"""
        <div class="metric-card">
            <div>QUBIC PRICE</div>
            <div class="metric-value">${current_prices.get('QUBIC', 0):.6f}</div>
            <div class="delta-value {price_change_class}">{current_prices.get('QUBIC_change', 0):.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

# Create two columns for charts
col1, col2 = st.columns([2, 1])

# Pool Stats Chart in first column
# Pool Stats Chart in first column
with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("### Pool Statistics")
    
    if not df.empty:
        # Downsample the data for better performance
        df_chart = downsample_data(df)
        
        # Calculate mean hashrate for the entire dataset
        df_chart['mean_hashrate_mhs'] = df_chart['pool_hashrate_mhs'].expanding().mean()
        
        # Calculate ATH hashrate
        df_chart['ath_hashrate_mhs'] = df_chart['pool_hashrate_mhs'].cummax()
        
        if st.session_state.get('show_candlestick', False):
            # Candlestick Easter Egg Mode
            st.warning("👀 I told you not to click that! Enjoy the secret candlestick view.")
            
            # Create candlestick chart
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Mean hashrate trace
            fig.add_trace(go.Scatter(
                x=df_chart['timestamp'],
                y=df_chart['mean_hashrate_mhs'],
                mode='lines',
                name='Mean Hashrate (MH/s)',
                line=dict(color='cyan', width=2),
                yaxis='y1'
            ), secondary_y=False)
            
            # ATH hashrate trace
            fig.add_trace(go.Scatter(
                x=df_chart['timestamp'],
                y=df_chart['ath_hashrate_mhs'],
                mode='lines',
                name='ATH Hashrate (MH/s)',
                line=dict(color='gold', width=2, dash='dot'),
                yaxis='y1'
            ), secondary_y=False)
            
            # Network hashrate
            fig.add_trace(go.Scatter(
                x=df_chart['timestamp'],
                y=df_chart['network_hashrate_ghs'],
                mode='lines',
                name='Network Hashrate (GH/s)',
                line=dict(color='deepskyblue', width=2, dash='dot'),
                hovertemplate='%{y:.2f} GH/s<extra></extra>',
                yaxis='y1'
            ), secondary_y=True)
            
            # Add stars for blocks found
            block_times = df_chart[df_chart['block_found']]['timestamp']
            block_hashes = df_chart[df_chart['block_found']]['mean_hashrate_mhs']
            fig.add_trace(go.Scatter(
                x=block_times,
                y=block_hashes,
                mode='markers',
                name='Block Found',
                marker=dict(
                    symbol='star',
                    size=12,
                    color='red',
                    line=dict(width=1, color='black')
                ),
                hovertemplate='Block found!<extra></extra>'
            ), secondary_y=False)
            
            # Layout
            fig.update_layout(
                title='SECRET VIEW: Hashrate Statistics (Downsampled)',
                xaxis=dict(title='Timestamp'),
                yaxis=dict(title='Pool Hashrate (MH/s)'),
                yaxis2=dict(title='Network Hashrate (GH/s)', overlaying='y', side='right'),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                margin=dict(l=40, r=40, t=40, b=40),
                height=450
            )
            fig.update_xaxes(rangeslider_visible=True)
            
        else:
            fig = go.Figure()
        
            # Mean Hashrate (MH/s) - using downsampled data
            fig.add_trace(go.Scatter(
                x=df_chart['timestamp'],
                y=df_chart['mean_hashrate_mhs'],
                mode='lines',
                name='Mean Hashrate (MH/s)',
                line=dict(color='cyan', width=2),
                yaxis='y1'
            ))
        
            # ATH Hashrate (MH/s)
            fig.add_trace(go.Scatter(
                x=df_chart['timestamp'],
                y=df_chart['ath_hashrate_mhs'],
                mode='lines',
                name='ATH Hashrate (MH/s)',
                line=dict(color='gold', width=2, dash='dot'),
                yaxis='y1'
            ))
        
            # Network Hashrate displayed in MH/s, labeled as GH/s
            fig.add_trace(go.Scatter(
                x=df_chart['timestamp'],
                y=df_chart['network_hashrate_ghs'],
                mode='lines',
                name='Network Hashrate (GH/s)',
                line=dict(color='deepskyblue', width=2, dash='dot'),
                hovertemplate='%{y:.2f} GH/s<extra></extra>',
                yaxis='y1'
            ))
        
            # Add stars for blocks found
            block_times = df_chart[df_chart['block_found']]['timestamp']
            block_hashes = df_chart[df_chart['block_found']]['mean_hashrate_mhs']
            fig.add_trace(go.Scatter(
                x=block_times,
                y=block_hashes,
                mode='markers',
                name='Block Found',
                marker=dict(
                    symbol='star',
                    size=12,
                    color='red',
                    line=dict(width=1, color='black')
                ),
                hovertemplate='Block found!<extra></extra>'
            ))

            # Layout
            fig.update_layout(
                title='Hashrate Statistics Over Time',
                xaxis=dict(title='Timestamp'),
                yaxis=dict(
                    title='Hashrate',
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
        st.warning("No pool data available to display.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Refresh button and footer
if st.button("🔄 Manual Refresh"):
    st.cache_data.clear()
    st.rerun()
    
# Add a data source note
st.markdown(
"""
<div style="margin-top: 1em; font-size: 0.9em; color: gray;">
    📊 <strong>Data Source:</strong> <a href="https://xmr-stats.qubic.org/" target="_blank">xmr-stats.qubic.org</a> (<a href="https://github.com/jtgrassie/monero-pool" target="_blank">https://github.com/jtgrassie/monero-pool</a>).<br>
    💰 <strong>Price Data:</strong> MEXC exchange (via CCXT).<br>
    💌 <strong>Inspired by:</strong> <a href="https://qubic-xmr.vercel.app/" target="_blank">qubic-xmr.vercel.app</a>.<br>
    ⏱️ <em>Note:</em> Data is slightly delayed due to the data collection approach.
</div>
""",
unsafe_allow_html=True
)
