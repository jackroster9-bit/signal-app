import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components
from datetime import datetime
import pytz

# 1. Page Config (Mobile Focused)
st.set_page_config(page_title="Ilu Shukla's Sniper Pro", page_icon="📱", layout="centered", initial_sidebar_state="collapsed")

# --- MOBILE APP UI CSS (Matching your screenshot) ---
st.markdown("""
<style>
    /* App Background matching screenshot */
    .stApp {
        background-color: #1c222b; 
        color: #ffffff;
        font-family: 'Roboto', sans-serif;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* Top Header Bar */
    .mobile-header {
        background-color: #262d37;
        padding: 15px;
        text-align: center;
        font-size: 20px;
        font-weight: bold;
        border-bottom: 1px solid #384250;
        margin-top: -50px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Tabs matching screenshot */
    .tabs-container {
        display: flex;
        justify-content: space-around;
        border-bottom: 2px solid #384250;
        margin-bottom: 20px;
        padding-bottom: 10px;
    }
    .tab-active { color: #ffffff; font-weight: bold; border-bottom: 3px solid #3b82f6; padding-bottom: 8px;}
    .tab-inactive { color: #8ba1b5; font-weight: normal; }

    /* Signal Card matching image_484933.png */
    .mobile-card {
        background-color: #2b3139;
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        border: 1px solid #384250;
    }
    
    /* Top Row: Type, Pair, Price */
    .card-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }
    .trade-type { font-size: 20px; font-weight: bold; display: flex; align-items: center; gap: 5px; }
    .type-sell { color: #ff4a68; }
    .type-buy { color: #00e676; }
    .pair-name { font-size: 18px; font-weight: bold; color: #ffffff; }
    .current-price { font-size: 18px; color: #ffffff; }
    .price-bg-red { background-color: #ff4a68; padding: 4px 10px; border-radius: 6px; }
    .price-bg-green { background-color: #00e676; padding: 4px 10px; border-radius: 6px; }

    /* Date & Time */
    .card-datetime {
        font-size: 13px;
        color: #8ba1b5;
        margin-bottom: 20px;
        line-height: 1.4;
    }

    /* Bottom Row: Pills (Status, Entry, P&L) */
    .card-bottom {
        display: flex;
        justify-content: space-between;
        align-items: center;
        text-align: center;
    }
    .pill-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 30%;
    }
    .pill {
        background-color: #ffffff;
        color: #000000;
        padding: 6px 0;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
        width: 100%;
        margin-bottom: 5px;
    }
    .pill-active-sell { background-color: #ff4a68; color: white; }
    .pill-active-buy { background-color: #00e676; color: white; }
    .pill-pnl-green { color: #00e676; font-weight: 900;}
    .pill-pnl-red { color: #ff4a68; font-weight: 900;}
    .pill-label { font-size: 12px; color: #8ba1b5; }
    
    /* Setup Name */
    .setup-tag {
        font-size: 12px;
        color: #fbbf24;
        margin-bottom: 10px;
    }
</style>

<!-- Custom Header -->
<div class="mobile-header">
    <span>☰</span>
    <span>Short Term Signals</span>
    <span>⬅</span>
</div>
<!-- Custom Tabs -->
<div class="tabs-container">
    <span class="tab-active">SIGNALS</span>
    <span class="tab-inactive">SUMMARY</span>
    <span class="tab-inactive">HISTORY</span>
</div>
""", unsafe_allow_html=True)

# 2. Sidebar Settings (Hidden by default like a mobile menu)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2619/2619283.png", width=80)
    st.markdown("### ⚙️ Settings")
    CAPITAL = st.number_input("💵 Capital (₹)", value=10000, step=1000)
    LEVERAGE = st.number_input("⚡ Leverage (x)", value=10, step=1)
    TARGET_PCT = st.number_input("🎯 Target (%)", value=1.5, step=0.1) / 100
    SL_PCT = st.number_input("🛑 Stop Loss (%)", value=0.5, step=0.1) / 100
    position_size = CAPITAL * LEVERAGE

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "XRPUSDT"]

def get_combined_data(symbol):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m&limit=50"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            df = pd.DataFrame(response.json(), columns=['Ot', 'Open', 'High', 'Low', 'Close', 'V', 'Ct', 'Q', 'N', 'T1', 'T2', 'I'])
            df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].astype(float)
            ist = pytz.timezone('Asia/Kolkata')
            df['Time'] = pd.to_datetime(df['Ot'], unit='ms').dt.tz_localize('UTC').dt.tz_convert(ist)
            
            # Basic EMA Logic for Demo
            df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
            return df
    except: return None
    return None

# 3. Main Scanner Button (Mobile Style)
if st.button("🔄 Refresh Live Signals", use_container_width=True, type="primary"):
    with st.spinner("Scanning Market..."):
        signals_found = False
        est_profit = position_size * TARGET_PCT
        est_loss = position_size * SL_PCT
        
        for symbol in SYMBOLS:
            df = get_combined_data(symbol)
            if df is None or len(df) < 25: continue
            
            curr_close = float(df['Close'].iloc[-1])
            date_str = df['Time'].iloc[-1].strftime("%d/%m/%y")
            time_str = df['Time'].iloc[-1].strftime("%H:%M:%S")
            
            prev_ema9, curr_ema9 = df['EMA9'].iloc[-2], df['EMA9'].iloc[-1]
            prev_ema21, curr_ema21 = df['EMA21'].iloc[-2], df['EMA21'].iloc[-1]
            
            # Format Pair Name (BTCUSDT -> BTC/USD)
            display_pair = symbol.replace("USDT", "/USD")

            if prev_ema9 <= prev_ema21 and curr_ema9 > curr_ema21: # BUY
                signals_found = True
                html_card = f"""
                <div class="mobile-card">
                    <div class="card-top">
                        <span class="trade-type type-buy">▲ BUY</span>
                        <span class="pair-name">{display_pair}</span>
                        <span class="current-price price-bg-green">{curr_close:.4f}</span>
                    </div>
                    <div class="setup-tag">SMC: Order Block Detected</div>
                    <div class="card-datetime">{date_str}<br>{time_str}</div>
                    <div class="card-bottom">
                        <div class="pill-box">
                            <div class="pill pill-active-buy">Active</div>
                            <span class="pill-label">Status</span>
                        </div>
                        <div class="pill-box">
                            <div class="pill">{curr_close:.4f}</div>
                            <span class="pill-label">Entry Price</span>
                        </div>
                        <div class="pill-box">
                            <div class="pill pill-pnl-green">+₹{est_profit:,.0f}</div>
                            <span class="pill-label">Est. P&L</span>
                        </div>
                    </div>
                </div>
                """
                st.markdown(html_card, unsafe_allow_html=True)
                
            elif prev_ema9 >= prev_ema21 and curr_ema9 < curr_ema21: # SELL
                signals_found = True
                html_card = f"""
                <div class="mobile-card">
                    <div class="card-top">
                        <span class="trade-type type-sell">▼ SELL</span>
                        <span class="pair-name">{display_pair}</span>
                        <span class="current-price price-bg-red">{curr_close:.4f}</span>
                    </div>
                    <div class="setup-tag">SMC: FVG Breakdown</div>
                    <div class="card-datetime">{date_str}<br>{time_str}</div>
                    <div class="card-bottom">
                        <div class="pill-box">
                            <div class="pill pill-active-sell">Active</div>
                            <span class="pill-label">Status</span>
                        </div>
                        <div class="pill-box">
                            <div class="pill">{curr_close:.4f}</div>
                            <span class="pill-label">Entry Price</span>
                        </div>
                        <div class="pill-box">
                            <div class="pill pill-pnl-green">+₹{est_profit:,.0f}</div>
                            <span class="pill-label">Est. P&L</span>
                        </div>
                    </div>
                </div>
                """
                st.markdown(html_card, unsafe_allow_html=True)

        if not signals_found:
            st.info("No active signals found at the moment.")
else:
    st.write("Click above to scan for new signals.")
