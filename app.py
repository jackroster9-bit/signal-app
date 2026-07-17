import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components
from datetime import datetime
import pytz

# 1. Page Config
st.set_page_config(page_title="Ilu Shukla's Sniper Pro", page_icon="🎯", layout="wide")

# --- CUSTOM CSS FOR PREMIUM LOOK ---
st.markdown("""
<style>
    .stApp { background-color: #0a0e17; color: #e2e8f0; }
    .main-title { font-size: 42px; font-weight: 900; text-align: center; color: #ffffff; margin-bottom: 5px; }
    .sub-title { text-align: center; color: #94a3b8; font-size: 16px; margin-bottom: 30px; }
    .signal-card { background: #111827; border-radius: 12px; padding: 20px; margin-bottom: 15px; border: 1px solid #1f2937; }
    .buy-card { border-left: 5px solid #00e676; }
    .sell-card { border-left: 5px solid #ff1744; }
    .price-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 15px; }
    .price-label { font-size: 11px; color: #64748b; text-transform: uppercase; }
    .price-value { font-size: 16px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 2. Sidebar
with st.sidebar:
    st.title("⚙️ Sniper Settings")
    CAPITAL = st.number_input("कैपिटल (₹)", value=10000, step=1000)
    LEVERAGE = st.number_input("लिवरेज (x)", value=10, step=1)
    TARGET_PCT = st.number_input("टारगेट (%)", value=1.5, step=0.1) / 100
    SL_PCT = st.number_input("स्टॉप लॉस (%)", value=0.5, step=0.1) / 100
    st.info("🕒 टाइमफ्रेम: 1 Minute (Scalping)")

# 3. Header
st.markdown('<div class="main-title">Ilu Shukla\'s Sniper Pro 🎯</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">SMC + Multi-Indicator AI Scalper</div>', unsafe_allow_html=True)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "ADAUSDT", "XRPUSDT", "LINKUSDT", "NEARUSDT", "SUIUSDT"]

def get_data(symbol):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m&limit=50"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json(), columns=['Ot', 'Open', 'High', 'Low', 'Close', 'V', 'Ct', 'Q', 'N', 'T1', 'T2', 'I'])
            df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].astype(float)
            df['EMA9'] = df['Close'].ewm(span=9).mean()
            df['EMA21'] = df['Close'].ewm(span=21).mean()
            return df
    except: return None

# 4. Scanner Logic
if st.button("⚡ EXECUTE ULTIMATE SCAN", use_container_width=True):
    with st.spinner("स्कैनिंग जारी है..."):
        for symbol in SYMBOLS:
            df = get_data(symbol)
            if df is None: continue
            
            c = df['Close'].iloc[-1]
            # Simple Trigger Logic (For demonstration)
            is_buy = df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1] and df['EMA9'].iloc[-2] <= df['EMA21'].iloc[-2]
            is_sell = df['EMA9'].iloc[-1] < df['EMA21'].iloc[-1] and df['EMA9'].iloc[-2] >= df['EMA21'].iloc[-2]
            
            if is_buy or is_sell:
                type_class = "buy-card" if is_buy else "sell-card"
                title = "🟢 BUY" if is_buy else "🔴 SELL"
                target = c * (1 + TARGET_PCT) if is_buy else c * (1 - TARGET_PCT)
                sl = c * (1 - SL_PCT) if is_buy else c * (1 + SL_PCT)
                
                st.markdown(f"""
                <div class="signal-card {type_class}">
                    <div style="font-size:20px; font-weight:bold;">{title} • {symbol}</div>
                    <div class="price-grid">
                        <div><div class="price-label">Entry</div><div class="price-value">${c:.2f}</div></div>
                        <div><div class="price-label">Target</div><div class="price-value">${target:.2f}</div></div>
                        <div><div class="price-label">SL</div><div class="price-value">${sl:.2f}</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
else:
    st.write("---")
    st.info("मार्केट डेटा एनालाइज करने के लिए बटन दबाएं।")
