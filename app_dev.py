import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time
import ccxt
import numpy as np
from datetime import datetime, timedelta
from plotly.subplots import make_subplots

# Configuration
GITHUB_RAW_URL = "http://66.179.92.83/data/p1.csv"
REFRESH_INTERVAL = 5  # seconds

# Setup page
st.set_page_config(
    page_title="Qubic Monero Pool Dashboard",
    page_icon="⛏️",
    layout="wide"
)

# Initialize exchange
EXCHANGE = ccxt.mexc({
    'enableRateLimit': True,
    'rateLimit': 3000,
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
    .metric-value { font-size: 1.8rem; font-weight: bold; color: #4cc9f0; margin: 0.2rem 0; }
    .delta-value { text-align: right; font-size: 0.9rem; color: gray; margin-top: auto; }
    .block-indicator { color: #f72585; font-weight: bold; }
    .price-positive { color: #4ade80; }
    .price-negative { color: #f87171; }
    .chart-container {
        background: rgba(32, 46, 60, 0.7);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=5, show_spinner="Loading data...")
def load_data():
    try:
        df = pd.read_csv(f"{GITHUB_RAW_URL}?t={int(time.time())}")
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.sort_values('timestamp', inplace=True)
        df['pool_hashrate_mhs'] = df['pool_hashrate'] / 1e6
        df['network_hashrate_ghs'] = df['network_hashrate'] / 1e9
        df['block_found'] = df['pool_blocks_found'].diff().fillna(0) > 0
        return df
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_prices():
    try:
        xmr_ticker = EXCHANGE.fetch_ticker('XMR/USDT')
        qubic_ticker = EXCHANGE.fetch_ticker('QUBIC/USDT')

        since = EXCHANGE.milliseconds() - 86400 * 1000
        xmr_ohlcv = EXCHANGE.fetch_ohlcv('XMR/USDT', '1h', since=since)
        qubic_ohlcv = EXCHANGE.fetch_ohlcv('QUBIC/USDT', '1h', since=since)

        def build_df(ohlcv, symbol):
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            return df

        return (pd.concat([build_df(xmr_ohlcv, 'XMR'), build_df(qubic_ohlcv, 'QUBIC')]),
                {
                    'XMR': xmr_ticker['last'],
                    'QUBIC': qubic_ticker['last'],
                    'XMR_change': xmr_ticker['percentage'],
                    'QUBIC_change': qubic_ticker['percentage']
                })
    except Exception as e:
        st.error(f"Price fetch error: {str(e)}")
        return pd.DataFrame(), {}

def format_hashrate(h):
    if h >= 1e9: return f"{h/1e9:.2f} GH/s"
    if h >= 1e6: return f"{h/1e6:.2f} MH/s"
    if h >= 1e3: return f"{h/1e3:.2f} KH/s"
    return f"{h:.2f} H/s"

def format_timespan(delta):
    if delta.days > 0: return f"{delta.days}d {delta.seconds//3600}h ago"
    return f"{delta.seconds//3600}h {(delta.seconds%3600)//60}m ago"

def downsample(df, interval='5T'):
    if df.empty: return df
    ath = df['pool_hashrate'].idxmax()
    blocks = df[df['block_found']].index

    df_resampled = df.resample(interval, on='timestamp').agg({
        'pool_hashrate': 'mean',
        'pool_hashrate_mhs': 'mean',
        'network_hashrate': 'mean',
        'network_hashrate_ghs': 'mean',
        'pool_blocks_found': 'last',
        'block_found': 'any'
    }).reset_index()

    extra_points = pd.concat([df.loc[[ath]]] + [df.loc[[i]] for i in blocks if i not in df_resampled.index])
    df_combined = pd.concat([df_resampled, extra_points]).sort_values('timestamp').drop_duplicates('timestamp')
    df_combined['block_found'] = df_combined['pool_blocks_found'].diff().fillna(0) > 0
    return df_combined

# Load
df = load_data()
prices_df, current_prices = fetch_prices()

# Metrics
if not df.empty:
    latest = df.iloc[-1]
    six_hr = df[df['timestamp'] >= (df['timestamp'].max() - timedelta(hours=6))]
    mean_hash_6h = six_hr['pool_hashrate'].mean() / 1e6 if not six_hr.empty else 0
    ath_val = df['pool_hashrate'][:-1].max()
    ath_time = df[df['pool_hashrate'] == ath_val]['timestamp'].iloc[0].strftime('%Y-%m-%d')
    last_block = df[df['block_found']]['timestamp'].iloc[-1] if df['block_found'].any() else None
    time_since_block = format_timespan(latest['timestamp'] - last_block) if last_block else "No block"

col1, col2 = st.columns([3, 2])

with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("### Pool Statistics")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div>POOL HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['pool_hashrate'])}</div>
            <div style="margin-top: 10px;">MEAN (6H)</div>
            <div class="metric-value">{mean_hash_6h:.2f} MH/s</div>
            <div class="delta-value">ATH: {ath_val/1e6:.2f} MH/s ({ath_time})</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div>BLOCKS FOUND</div>
            <div class="metric-value">{int(latest['pool_blocks_found'])}</div>
            <div class="time-since-block">Last block: {time_since_block}</div>
            <div style="margin-top: 10px;">NETWORK HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['network_hashrate'])}</div>
        </div>
        """, unsafe_allow_html=True)

    if not df.empty:
        df_chart = downsample(df)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_chart['timestamp'], y=df_chart['pool_hashrate_mhs'], name='Pool Hashrate (MH/s)', line=dict(color='white')))
        fig.add_trace(go.Scatter(x=df_chart['timestamp'], y=df_chart['network_hashrate_ghs'], name='Network Hashrate (GH/s)', line=dict(color='deepskyblue', dash='dot')))
        blocks = df_chart[df_chart['block_found']]
        fig.add_trace(go.Scatter(x=blocks['timestamp'], y=blocks['pool_hashrate_mhs'], mode='markers', name='Block Found', marker=dict(symbol='star', size=12, color='gold', line=dict(width=1, color='black'))))
        fig.update_layout(title='Hashrate Over Time', xaxis_title='Time', yaxis_title='Hashrate', height=450)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("### Price Charts")
    p1, p2 = st.columns(2)
    for coin, label, col in zip(['XMR', 'QUBIC'], ['XMR PRICE', 'QUBIC PRICE'], [p1, p2]):
        change = current_prices.get(f'{coin}_change', 0)
        cls = 'price-positive' if change >= 0 else 'price-negative'
        val = current_prices.get(coin, 0)
        fmt = '.2f' if coin == 'XMR' else '.6f'
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div>{label}</div>
                <div class="metric-value">${val:{fmt}}</div>
                <div class="delta-value {cls}">{change:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

    if not prices_df.empty:
        fig = go.Figure()
        for coin, color, axis in [('XMR', 'limegreen', 'y1'), ('QUBIC', 'magenta', 'y2')]:
            df_coin = prices_df[prices_df['symbol'] == coin]
            fig.add_trace(go.Scatter(x=df_coin['timestamp'], y=df_coin['close'], name=f'{coin} Price', line=dict(color=color), yaxis=axis))

        fig.update_layout(
            title='XMR & QUBIC Prices (24h)',
            xaxis_title='Timestamp',
            yaxis=dict(title='XMR Price (USD)', side='left'),
            yaxis2=dict(title='QUBIC Price (USD)', overlaying='y', side='right'),
            height=450
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

if st.button("🔄 Manual Refresh"):
    st.cache_data.clear()
    st.rerun()

st.markdown("""
<div style="margin-top: 1em; font-size: 0.9em; color: gray;">
📊 <strong>Data Source:</strong> <a href="https://xmr-stats.qubic.org/" target="_blank">xmr-stats.qubic.org</a>.<br>
💰 <strong>Price Data:</strong> MEXC (via CCXT).<br>
💌 <strong>Inspired by:</strong> <a href="https://qubic-xmr.vercel.app/" target="_blank">qubic-xmr.vercel.app</a>.<br>
</div>
""", unsafe_allow_html=True)
