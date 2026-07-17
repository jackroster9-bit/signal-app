import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components
import pytz
from datetime import datetime

st.set_page_config(page_title="Ilu Shukla • Sniper Pro", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")

# ====================== PROFESSIONAL CSS ======================
st.markdown("""
<style>
    .stApp { background-color: #0f1626; color: #e2e8f0; }
    .main-title {
        font-size: 42px; font-weight: 800; text-align: center; margin-bottom: 8px;
        background: linear-gradient(90deg, #00d4ff, #7b68ee);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .sub-title { text-align: center; color: #94a3b8; font-size: 17px; margin-bottom: 30px; }
    
    .signal-card {
        background: linear-gradient(145deg, #1a2338, #16203a);
        border-radius: 16px; padding: 22px; margin: 18px 0;
        border: 1px solid rgba(100, 150, 255, 0.15); box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    .signal-card:hover { transform: translateY(-4px); border-color: #00d4ff; }
    
    .buy-card { border-left: 5px solid #00ff9d; }
    .sell-card { border-left: 5px solid #ff3b5c; }
    
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .symbol { font-size: 22px; font-weight: 700; }
    .signal-type { font-size: 13px; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
    
    .price-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-top: 16px; }
    .price-box { background: rgba(255,255,255,0.05); padding: 12px; border-radius: 10px; text-align: center; }
    .label { font-size: 12px; color: #94a3b8; }
    .value { font-size: 17px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ====================== SIDEBAR ======================
with st.sidebar:
    st.markdown("### **Ilu Shukla's Sniper Pro**")
    st.markdown("---")
    CAPITAL = st.number_input("💰 Capital (₹)", value=15000, step=1000)
    LEVERAGE = st.number_input("⚡ Leverage", value=10, step=1)
    TARGET_PCT = st.number_input("🎯 Target %", value=1.5, step=0.1) / 100
    SL_PCT = st.number_input("🛑 Stop Loss %", value=0.5, step=0.1) / 100
    
    st.success(f"**Position Size:** ₹{CAPITAL * LEVERAGE:,.0f}")
    st.caption("1 Minute • Professional Scalping System")

# ====================== HEADER ======================
st.markdown('<div class="main-title">ILU SHUKLA SNIPER PRO</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Professional 1-Minute Scalping • Live Signals</div>', unsafe_allow_html=True)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "XRPUSDT", "SUIUSDT"]

# ====================== DATA FUNCTION ======================
@st.cache_data(ttl=25)
def get_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=80"
    try:
        df = pd.DataFrame(requests.get(url).json(), 
                         columns=['ot','o','h','l','c','v','ct','q','n','tb','tq','ig'])
        df = df[['ot','o','h','l','c']].astype(float)
        df['Time'] = pd.to_datetime(df['ot'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        df['Close'] = df['c']
        
        # Indicators
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA21'] = df['Close'].ewm(span=21).mean()
        delta = df['Close'].diff()
        df['RSI'] = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / -delta.clip(upper=0).rolling(14).mean())))
        
        return df
    except:
        return None

# ====================== SMALL CHART ======================
def small_chart(symbol, df):
    last_price = df['Close'].iloc[-1]
    tv = f"""
    <div style="height:180px; border-radius:12px; overflow:hidden; background:#111827;">
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
            "symbol": "BINANCE:{symbol}",
            "interval": "1",
            "width": "100%",
            "height": "180",
            "theme": "dark",
            "style": "1",
            "hide_top_toolbar": true,
            "hide_legend": true,
            "save_image": false,
            "backgroundColor": "#111827"
        }});
        </script>
    </div>
    """
    components.html(tv, height=200)

# ====================== MAIN SCANNER ======================
if st.button("🚀 SCAN MARKET NOW", type="primary", use_container_width=True):
    with st.spinner("Professional Analysis Running on 1m Timeframe..."):
        found = False
        for symbol in SYMBOLS:
            df = get_data(symbol)
            if df is None or len(df) < 30: 
                continue
                
            close = float(df['Close'].iloc[-1])
            time_str = df['Time'].iloc[-1].strftime("%I:%M %p")
            
            setup = ""
            is_buy = is_sell = False
            
            # SMC + Indicator Logic (Clean & Professional)
            if df['Close'].iloc[-2] > df['EMA9'].iloc[-2] and df['Close'].iloc[-1] > df['EMA21'].iloc[-1]:
                is_buy, setup = True, "EMA Bullish Alignment + Momentum"
            elif close < df['Lower_BB'].iloc[-1] and df['RSI'].iloc[-1] < 32:
                is_buy, setup = True, "BB Oversold Bounce"
            elif close > df['Upper_BB'].iloc[-1]:
                is_buy, setup = True, "Strong Breakout"
                
            if df['RSI'].iloc[-1] > 70:
                is_sell, setup = True, "Overbought Rejection"
            
            if is_buy or is_sell:
                found = True
                color = "buy" if is_buy else "sell"
                
                st.markdown(f"""
                <div class="signal-card {color}-card">
                    <div class="card-header">
                        <span class="symbol">{symbol}</span>
                        <span class="signal-type" style="background:{'#00ff9d20' if is_buy else '#ff3b5c20'}; color:{'#00ff9d' if is_buy else '#ff3b5c'}">
                            {'BUY' if is_buy else 'SELL'}
                        </span>
                    </div>
                    <small style="color:#94a3b8">1m • {time_str}</small>
                    <h4 style="margin:8px 0; color:{'#00ff9d' if is_buy else '#ff3b5c'}">{setup}</h4>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Entry", f"${close:.4f}")
                with col2:
                    st.metric("Target", f"${close * (1 + TARGET_PCT if is_buy else 1 - TARGET_PCT):.4f}", 
                             delta=f"+{TARGET_PCT*100:.1f}%")
                with col3:
                    st.metric("Stop Loss", f"${close * (1 - SL_PCT if is_buy else 1 + SL_PCT):.4f}", 
                             delta=f"-{SL_PCT*100:.1f}%")
                
                small_chart(symbol, df)
                st.markdown("</div>", unsafe_allow_html=True)
        
        if not found:
            st.info("**No high-probability setups right now.** Market is being monitored on 1-minute timeframe.")

else:
    st.markdown("### Click **SCAN MARKET NOW** to get professional signals with mini-charts")
