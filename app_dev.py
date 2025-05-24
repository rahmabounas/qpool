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
GITHUB_RAW_URL = "http://66.179.92.83/data/p2.csv"
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
        background-color: #1a252f !important;
        color: white !important;
    }
    .metric-card {
        background: rgba(32, 46, 60, 0.9);
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem;
        border: 1px solid rgba(255,255,255,0.15);
        color: white;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .metric-label { font-size: 1rem; font-weight: 600; color: #b0b8c1; }
    .metric-value { font-size: 1.8rem; font-weight: bold; color: #4cc9f0; margin: 0.3rem 0; }
    .delta-value { font-size: 0.85rem; color: #8b95a1; margin-top: auto; }
    .block-indicator { color: #f72585; font-weight: bold; }
    .price-positive { color: #4ade80; }
    .price-negative { color: #f87171; }
    .chart-container {
        background: rgba(32, 46, 60, 0.8);
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .stButton > button {
        background-color: #4cc9f0;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton > button:hover {
        background-color: #3ba8d0;
        border-color: #3ba8d0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=REFRESH_INTERVAL, show_spinner="Loading data...")
def load_data():
    """Load and preprocess CSV data."""
    try:
        df = pd.read_csv(f"{GITHUB_RAW_URL}?t={int(time.time())}")
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        if df['timestamp'].isna().any():
            raise ValueError("Invalid timestamp values in CSV")
        df.sort_values('timestamp', inplace=True)
        df['pool_hashrate_mhs'] = df['pool_hashrate'] / 1e6
        df['network_hashrate_ghs'] = df['network_hashrate'] / 1e9
        df['block_found'] = df['pool_blocks_found'].diff().fillna(0) > 0
        df['qubic_usdt'] = df['qubic_usdt'].astype(float, errors='ignore')
        df['close'] = df['close'].astype(float, errors='ignore')
        return df
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        return pd.DataFrame()

def format_hashrate(h):
    """Format hashrate values for display."""
    if pd.isna(h):
        return "N/A"
    if h >= 1e9: return f"{h/1e9:.2f} GH/s"
    if h >= 1e6: return f"{h/1e6:.2f} MH/s"
    if h >= 1e3: return f"{h/1e3:.2f} KH/s"
    return f"{h:.2f} H/s"

def format_timespan(delta):
    """Format time delta for display."""
    if pd.isna(delta):
        return "N/A"
    if delta.days > 0: return f"{delta.days}d {delta.seconds//3600}h ago"
    return f"{delta.seconds//3600}h {(delta.seconds%3600)//60}m ago"

def downsample(df, interval='5T'):
    """Downsample DataFrame while preserving key points (ATH, blocks)."""
    if df.empty:
        return df
    ath = df['pool_hashrate'].idxmax()
    blocks = df[df['block_found']].index

    df_resampled = df.resample(interval, on='timestamp').agg({
        'pool_hashrate': 'mean',
        'pool_hashrate_mhs': 'mean',
        'network_hashrate': 'mean',
        'network_hashrate_ghs': 'mean',
        'pool_blocks_found': 'last',
        'block_found': 'any',
        'qubic_usdt': 'last',
        'close': 'last'
    }).reset_index()

    extra_points = pd.concat([df.loc[[ath]]] + [df.loc[[i]] for i in blocks if i not in df_resampled.index])
    df_combined = pd.concat([df_resampled, extra_points]).sort_values('timestamp').drop_duplicates('timestamp')
    df_combined['block_found'] = df_combined['pool_blocks_found'].diff().fillna(0) > 0
    return df_combined

# Load data
df = load_data()

# Dashboard Layout
st.markdown("## Qubic Monero Pool Dashboard")

# Metric Cards (Top Row)
if not df.empty:
    latest = df.iloc[-1]
    six_hr = df[df['timestamp'] >= (df['timestamp'].max() - timedelta(hours=6))]
    mean_hash_6h = six_hr['pool_hashrate'].mean() / 1e6 if not six_hr.empty else 0
    ath_val = df['pool_hashrate'][:-1].max() if len(df) > 1 else latest['pool_hashrate']
    ath_time = df[df['pool_hashrate'] == ath_val]['timestamp'].iloc[0].strftime('%Y-%m-%d') if not df.empty else "N/A"
    last_block = df[df['block_found']]['timestamp'].iloc[-1] if df['block_found'].any() else None
    time_since_block = format_timespan(latest['timestamp'] - last_block) if last_block else "No block"

    # Metric Cards in a single row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">POOL HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['pool_hashrate'])}</div>
            <div class="delta-value">Mean (6h): {mean_hash_6h:.2f} MH/s</div>
            <div class="delta-value">ATH: {format_hashrate(ath_val)} ({ath_time})</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">NETWORK HASHRATE</div>
            <div class="metric-value">{format_hashrate(latest['network_hashrate'])}</div>
            <div class="delta-value">Mean (6h): {format_hashrate(six_hr['network_hashrate'].mean())}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">BLOCKS FOUND</div>
            <div class="metric-value">{int(latest['pool_blocks_found'])}</div>
            <div class="delta-value">Last block: {time_since_block}</div>
        </div>
        """, unsafe_allow_html=True)

# Hashrate Chart
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown("### Hashrate Over Time")
if not df.empty:
    df_chart = downsample(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_chart['timestamp'],
        y=df_chart['pool_hashrate_mhs'],
        name='Pool Hashrate (MH/s)',
        line=dict(color='#4cc9f0'),
        hovertemplate='%{x|%Y-%m-%d %H:%M}<br>Pool: %{y:.2f} MH/s<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=df_chart['timestamp'],
        y=df_chart['network_hashrate_ghs'],
        name='Network Hashrate (GH/s)',
        line=dict(color='#87ceeb', dash='dot'),
        yaxis='y2',
        hovertemplate='%{x|%Y-%m-%d %H:%M}<br>Network: %{y:.2f} GH/s<extra></extra>'
    ))
    blocks = df_chart[df_chart['block_found']]
    fig.add_trace(go.Scatter(
        x=blocks['timestamp'],
        y=blocks['pool_hashrate_mhs'],
        mode='markers',
        name='Block Found',
        marker=dict(symbol='star', size=12, color='gold', line=dict(width=1, color='black')),
        hovertemplate='%{x|%Y-%m-%d %H:%M}<br>Block Found<extra></extra>'
    ))
    fig.update_layout(
        title='Pool and Network Hashrate',
        xaxis=dict(title='Time', gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='Pool Hashrate (MH/s)', gridcolor='rgba(255,255,255,0.1)'),
        yaxis2=dict(title='Network Hashrate (GH/s)', overlaying='y', side='right', gridcolor='rgba(255,255,255,0.1)'),
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        showlegend=True,
        legend=dict(x=0, y=1.1, orientation='h'),
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hashrate data available.")
st.markdown('</div>', unsafe_allow_html=True)

# Price Chart with Dual Y-Axes
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown("### XMR & QUBIC Price (USD)")
if not df.empty and 'qubic_usdt' in df.columns and 'close' in df.columns:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['close'],
        name='XMR/USDT',
        line=dict(color='#4ade80'),
        hovertemplate='%{x|%Y-%m-%d %H:%M}<br>XMR: $%{y:.2f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['qubic_usdt'],
        name='QUBIC/USDT',
        line=dict(color='#f72585'),
        hovertemplate='%{x|%Y-%m-%d %H:%M}<br>QUBIC: $%{y:.6f}<extra></extra>',
        yaxis='y2'
    ))
    fig.update_layout(
        title='XMR and QUBIC Prices',
        xaxis=dict(title='Time', gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='XMR Price (USD)', titlefont=dict(color='#4ade80'), tickfont=dict(color='#4ade80'), gridcolor='rgba(255,255,255,0.1)'),
        yaxis2=dict(title='QUBIC Price (USD)', titlefont=dict(color='#f72585'), tickfont=dict(color='#f72585'), overlaying='y', side='right'),
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        showlegend=True,
        legend=dict(x=0, y=1.1, orientation='h'),
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No price data available.")
st.markdown('</div>', unsafe_allow_html=True)

# Manual Refresh Button
if st.button("🔄 Refresh Data", key="refresh"):
    st.cache_data.clear()
    st.rerun()

# Footer
st.markdown("""
<div style="margin-top: 1.5em; font-size: 0.85em; color: #8b95a1;">
📊 <strong>Data Source:</strong> <a href="https://xmr-stats.qubic.org/" target="_blank">xmr-stats.qubic.org</a><br>
💰 <strong>Price Data:</strong> MEXC (via CCXT)<br>
💌 <strong>Inspired by:</strong> <a href="https://qubic-xmr.vercel.app/" target="_blank">qubic-xmr.vercel.app</a>
</div>
""", unsafe_allow_html=True)
