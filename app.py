import streamlit as st
import pandas as pd
import requests
import pytz
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="Ilu Shukla • Sniper Pro", page_icon="🎯", layout="wide")

# ====================== CSS (Professional) ======================
st.markdown("""
<style>
    .stApp { background-color: #0a111f; color: #e2e8f0; }
    .main-title { font-size: 44px; font-weight: 900; text-align: center; 
                  background: linear-gradient(90deg, #00f5ff, #5e72ff); 
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .signal-card, .backtest-card { background: #13213a; border-radius: 16px; padding: 20px; margin: 15px 0; }
    .buy { color: #00ff9d; } .sell { color: #ff3b5c; }
</style>
""", unsafe_allow_html=True)

# ====================== SIDEBAR ======================
with st.sidebar:
    st.title("Ilu Shukla Sniper Pro")
    st.markdown("---")
    CAPITAL = st.number_input("💰 Capital (₹)", value=15000, step=1000)
    RISK_PERCENT = st.slider("Risk % per Trade", 0.5, 2.0, 1.0, 0.1)
    LEVERAGE = st.number_input("Leverage", value=10, step=1)

# ====================== HEADER ======================
st.markdown('<div class="main-title">ILU SHUKLA SNIPER PRO</div>', unsafe_allow_html=True)

# ====================== TABS ======================
tab1, tab2 = st.tabs(["🚀 Live Scanner", "📊 Backtesting"])

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "SUIUSDT"]

# ====================== DATA FETCH ======================
@st.cache_data(ttl=30)
def get_historical_data(symbol, interval="1m", limit=500):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        data = requests.get(url).json()
        df = pd.DataFrame(data, columns=['ot','o','h','l','c','v','ct','q','n','tb','tq','ig'])
        df = df[['ot','o','h','l','c','v']].astype(float)
        df['Time'] = pd.to_datetime(df['ot'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        df['Close'] = df['c']
        df['Volume'] = df['v']
        return df
    except:
        return None

# ====================== BACKTESTING LOGIC ======================
def run_backtest(symbol, days=7):
    df = get_historical_data(symbol, "1m", limit=days*24*60)
    if df is None or len(df) < 100:
        return None
    
    df['EMA9'] = df['Close'].ewm(span=9).mean()
    df['EMA21'] = df['Close'].ewm(span=21).mean()
    delta = df['Close'].diff()
    df['RSI'] = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / -delta.clip(upper=0).rolling(14).mean())))
    df['AvgVol'] = df['Volume'].rolling(20).mean()
    
    trades = []
    position = None
    
    for i in range(30, len(df)-1):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        vol_spike = row['Volume'] > row['AvgVol'] * 1.8
        ema_bull = row['EMA9'] > row['EMA21']
        rsi_div = row['RSI'] < 45 and row['Close'] > df['Close'].iloc[i-10:i].max()  # Bullish div approx
        
        if position is None:
            if ema_bull and vol_spike and rsi_div:
                entry = row['Close']
                sl = entry * (1 - 0.005)
                target = entry * (1 + 0.015)
                position = {'type': 'BUY', 'entry': entry, 'sl': sl, 'target': target, 'time': row['Time']}
        
        elif position:
            if row['Close'] >= position['target']:
                trades.append({'symbol': symbol, 'type': 'BUY', 'pnl': (position['target'] - position['entry'])/position['entry'] * 100, 'time': position['time']})
                position = None
            elif row['Close'] <= position['sl']:
                trades.append({'symbol': symbol, 'type': 'BUY', 'pnl': (position['sl'] - position['entry'])/position['entry'] * 100, 'time': position['time']})
                position = None
    
    if trades:
        df_trades = pd.DataFrame(trades)
        win_rate = len(df_trades[df_trades['pnl'] > 0]) / len(df_trades) * 100 if len(df_trades) > 0 else 0
        total_pnl = df_trades['pnl'].sum()
        return {
            'trades': len(df_trades),
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'profit_trades': len(df_trades[df_trades['pnl'] > 0])
        }
    return {'trades': 0, 'win_rate': 0, 'total_pnl': 0}

# ====================== TAB 1: LIVE SCANNER ======================
with tab1:
    if st.button("🚀 Professional Live Scan", type="primary", use_container_width=True):
        # (Your previous scanner logic here - same as last version)
        st.info("Live Scanner logic same as previous enhanced version.")

# ====================== TAB 2: BACKTESTING ======================
with tab2:
    st.markdown("### 📊 Strategy Backtesting")
    col1, col2 = st.columns([1, 2])
    with col1:
        test_days = st.slider("Backtest Days", 3, 30, 7)
        if st.button("Run Backtest on All Symbols", type="primary"):
            results = []
            progress = st.progress(0)
            
            for idx, symbol in enumerate(SYMBOLS):
                result = run_backtest(symbol, test_days)
                if result and result['trades'] > 0:
                    results.append({'Symbol': symbol, **result})
                progress.progress((idx+1)/len(SYMBOLS))
            
            if results:
                df_result = pd.DataFrame(results)
                st.success("Backtest Complete!")
                st.dataframe(df_result.style.format({
                    'win_rate': '{:.1f}%',
                    'total_pnl': '{:.2f}%'
                }), use_container_width=True)
                
                total_trades = df_result['trades'].sum()
                avg_winrate = df_result['win_rate'].mean()
                st.metric("Overall Win Rate", f"{avg_winrate:.1f}%")
                st.metric("Total Signals Found", total_trades)
            else:
                st.warning("No trades found in this period.")

st.caption("Note: Backtesting uses simplified logic. Past performance ≠ Future results.")
