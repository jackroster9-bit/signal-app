import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components
from datetime import datetime
import pytz

# 1. Page Config
st.set_page_config(page_title="Ilu Shukla's Sniper Pro", page_icon="🎯", layout="wide")

# --- CSS (Premium Mobile Look) ---
st.markdown("""
<style>
    .stApp { background-color: #1c222b; color: #ffffff; font-family: sans-serif; }
    .header-bar { background-color: #262d37; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .user-name { font-size: 22px; font-weight: bold; color: #00e676; }
    .app-title { font-size: 16px; color: #8ba1b5; }
    .signal-card { background-color: #2b3139; border-radius: 15px; padding: 20px; margin-bottom: 15px; border: 1px solid #384250; }
    .buy-card { border-left: 6px solid #00e676; }
    .sell-card { border-left: 6px solid #ff4a68; }
    .card-title { font-size: 20px; font-weight: bold; }
    .price-val { font-size: 18px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 2. Header
st.markdown(f"""
<div class="header-bar">
    <div class="user-name">Welcome, Ilu Shukla</div>
    <div class="app-title">Sniper Pro 1m Ultimate SMC Scanner</div>
</div>
""", unsafe_allow_html=True)

# 3. Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    CAPITAL = st.number_input("💵 Capital (₹)", value=10000)
    LEVERAGE = st.number_input("⚡ Leverage (x)", value=10)
    TARGET_PCT = st.number_input("🎯 Target (%)", value=1.5, step=0.1) / 100
    SL_PCT = st.number_input("🛑 Stop Loss (%)", value=0.5, step=0.1) / 100
    position_size = CAPITAL * LEVERAGE

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "ADAUSDT", "DOTUSDT", "XRPUSDT", "LINKUSDT", "NEARUSDT"]

def get_data(symbol):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m&limit=100"
    try:
        response = requests.get(url, timeout=5).json()
        df = pd.DataFrame(response, columns=['Ot', 'Open', 'High', 'Low', 'Close', 'V', 'Ct', 'Q', 'N', 'T1', 'T2', 'I'])
        df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].astype(float)
        
        # Indicators
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['RSI'] = 100 - (100 / (1 + df['Close'].diff().clip(lower=0).rolling(14).mean() / -df['Close'].diff().clip(upper=0).rolling(14).mean()))
        
        # SMC logic
        df['Bull_FVG'] = (df['Low'] > df['High'].shift(2))
        df['Bear_FVG'] = (df['High'] < df['Low'].shift(2))
        
        return df
    except: return None

# 4. Scanner logic
if st.button("⚡ EXECUTE ULTIMATE SCAN", use_container_width=True, type="primary"):
    est_profit = position_size * TARGET_PCT
    est_loss = position_size * SL_PCT
    found = False
    
    for symbol in SYMBOLS:
        df = get_data(symbol)
        if df is None: continue
        
        curr = df['Close'].iloc[-1]
        
        # Logic: EMA Cross or FVG
        if (df['EMA9'].iloc[-2] < df['EMA21'].iloc[-2] and df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1]) or df['Bull_FVG'].iloc[-1]:
            found = True
            st.markdown(f"""
            <div class="signal-card buy-card">
                <div class="card-title" style="color: #00e676;">🟢 BUY {symbol}</div>
                <div class="price-val">Entry: ${curr:.2f} | Profit: ₹{est_profit:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
            
        elif (df['EMA9'].iloc[-2] > df['EMA21'].iloc[-2] and df['EMA9'].iloc[-1] < df['EMA21'].iloc[-1]) or df['Bear_FVG'].iloc[-1]:
            found = True
            st.markdown(f"""
            <div class="signal-card sell-card">
                <div class="card-title" style="color: #ff4a68;">🔴 SELL {symbol}</div>
                <div class="price-val">Entry: ${curr:.2f} | Profit: ₹{est_profit:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
            
    if not found: st.info("Scanning... No signals right now.")
