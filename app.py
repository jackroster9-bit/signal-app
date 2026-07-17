import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components
from datetime import datetime
import pytz

st.set_page_config(page_title="Ilu Shukla's Sniper Pro", page_icon="🎯", layout="wide")

# ====================== CUSTOM CSS ======================
st.markdown("""
<style>
    .stApp { background-color: #0a0e17; color: #e2e8f0; }
    .main-title { font-size: 48px; font-weight: 900; text-align: center;
                  background: linear-gradient(45deg, #00f2fe, #4facfe);
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .signal-card { background: rgba(30, 41, 59, 0.8); border-radius: 15px; 
                   padding: 20px; margin: 15px 0; border-left: 6px solid; }
    .buy-card { border-color: #00e676; }
    .sell-card { border-color: #ff1744; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Ilu Shukla\'s Sniper Pro 🎯</div>', unsafe_allow_html=True)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "ADAUSDT", 
           "DOTUSDT", "XRPUSDT", "SUIUSDT", "NEARUSDT"]

def get_binance_data(symbol):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m&limit=30"
    try:
        response = requests.get(url, timeout=6)
        if response.status_code == 200:
            df = pd.DataFrame(response.json(), columns=['Ot', 'Open', 'High', 'Low', 'Close', 'V', 'Ct', 'Q', 'N', 'T1', 'T2', 'I'])
            df[['High', 'Low', 'Close']] = df[['High', 'Low', 'Close']].astype(float)
            df['Time'] = pd.to_datetime(df['Ot'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
            return df
    except:
        return None
    return None

if st.button("🔄 अभी सिग्नल चेक करें", type="primary", use_container_width=True):
    with st.spinner("Swing High/Low Scan Chal Raha Hai..."):
        signals_found = False
        
        for symbol in SYMBOLS:
            df = get_binance_data(symbol)
            if df is None or len(df) < 15:
                continue
                
            latest_close = float(df['Close'].iloc[-1])
            time_str = df['Time'].iloc[-1].strftime("%I:%M %p IST")
            
            # Swing Detection Logic
            lookback = 5
            recent = df.iloc[- (lookback*2 + 2) : -1]
            
            if len(recent) < lookback*2:
                continue
                
            swing_high_idx = recent['High'].idxmax()
            swing_low_idx = recent['Low'].idxmin()
            
            is_swing_high = swing_high_idx == recent.index[lookback]
            is_swing_low = swing_low_idx == recent.index[lookback]
            
            if is_swing_high:
                signals_found = True
                target = latest_close * (1 - 0.01)
                sl = latest_close * (1 + 0.005)
                st.markdown(f"""
                <div class="signal-card sell-card">
                    <h3>🔴 SELL • {symbol}</h3>
                    <p>Entry: ${latest_close:.4f} | Time: {time_str}</p>
                    <p>Target: ${target:.4f} | SL: ${sl:.4f}</p>
                </div>
                """, unsafe_allow_html=True)
                
            elif is_swing_low:
                signals_found = True
                target = latest_close * (1 + 0.01)
                sl = latest_close * (1 - 0.005)
                st.markdown(f"""
                <div class="signal-card buy-card">
                    <h3>🟢 BUY • {symbol}</h3>
                    <p>Entry: ${latest_close:.4f} | Time: {time_str}</p>
                    <p>Target: ${target:.4f} | SL: ${sl:.4f}</p>
                </div>
                """, unsafe_allow_html=True)
        
        if not signals_found:
            st.info("**Abhi koi clear Swing Signal nahi mila.** Market quiet hai.")

else:
    st.write("**Button dabakar live signals dekhein**")

st.caption("Strategy: 1 Minute Swing High / Swing Low Break")
