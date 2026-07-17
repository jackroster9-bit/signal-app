import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh # यह लाइब्रेरी ऑटो-रिफ्रेश के लिए है

# 1. Page Config
st.set_page_config(page_title="Ilu Shukla's Sniper Pro", page_icon="🎯", layout="wide")

# ऑटो-रिफ्रेश सेट करें (30 सेकंड = 30000 मिलीसेकंड)
st_autorefresh(interval=30000, key="datarefresh")

# 2. Premium CSS (Institutional Look)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #050505; font-family: 'Inter', sans-serif; color: #e2e8f0; }
    .marquee { width: 100%; background: #131722; padding: 10px; color: #00e676; font-weight: bold; border-radius: 8px; border: 1px solid #363c4e; margin-bottom: 20px; text-align: center; }
    .signal-card { 
        background: rgba(13, 17, 23, 0.8); backdrop-filter: blur(10px);
        border: 1px solid #30363d; border-radius: 16px; padding: 20px; margin-bottom: 20px;
        border-left: 6px solid #58a6ff;
    }
    .buy-signal { border-left-color: #238636; }
    .sell-signal { border-left-color: #da3633; }
    .big-title { font-size: 3rem; font-weight: 900; background: linear-gradient(90deg, #00f2fe, #4facfe); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .price-val { font-size: 1.2rem; font-weight: bold; color: #ffffff; }
    .label { font-size: 0.8rem; color: #8b949e; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# 3. Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2619/2619283.png", width=80)
    st.title("🎯 Sniper Settings")
    CAPITAL = st.number_input("Capital (₹)", value=10000, step=1000)
    LEVERAGE = st.slider("Leverage (x)", 1, 100, 10)
    TARGET_PCT = st.number_input("Target (%)", value=1.5, step=0.1) / 100
    SL_PCT = st.number_input("Stop Loss (%)", value=0.5, step=0.1) / 100
    st.divider()
    st.metric("Position Size", f"₹{CAPITAL * LEVERAGE:,}")
    st.caption("✅ Auto-Refresh: ON (30s)")

# 4. Header & Marquee
st.markdown("<h1 class='big-title' style='text-align: center;'>Ilu Shukla's Sniper Pro</h1>", unsafe_allow_html=True)
st.markdown("<div class='marquee'>🚀 AUTO-LIVE SCALPING: SYSTEM IS SCANNING MARKET EVERY 30 SECONDS...</div>", unsafe_allow_html=True)

# 5. Functions
def get_data(symbol):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m&limit=50"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            df = pd.DataFrame(response.json(), columns=['Ot', 'Open', 'High', 'Low', 'Close', 'V', 'Ct', 'Q', 'N', 'T1', 'T2', 'I'])
            df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].astype(float)
            df['EMA9'] = df['Close'].ewm(span=9).mean()
            df['EMA21'] = df['Close'].ewm(span=21).mean()
            return df
    except: return None
    return None

# 6. Main Scanner
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "NEARUSDT", "SUIUSDT"]
cols = st.columns(3) # ग्रिड लेआउट के लिए

for i, symbol in enumerate(symbols):
    df = get_data(symbol)
    if df is not None:
        curr_close = df['Close'].iloc[-1]
        is_buy = df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1]
        
        card_class = "signal-card buy-signal" if is_buy else "signal-card sell-signal"
        color = "#238636" if is_buy else "#da3633"
        action = "BUY" if is_buy else "SELL"
        
        with cols[i % 3]:
            st.markdown(f"""
            <div class="{card_class}">
                <h3 style="color:{color}; margin-top:0;">{action} • {symbol}</h3>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                    <div><div class="label">Entry</div><div class="price-val">${curr_close:.2f}</div></div>
                    <div><div class="label">Target</div><div class="price-val">${curr_close*(1+TARGET_PCT if is_buy else 1-TARGET_PCT):.2f}</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
