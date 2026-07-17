import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Crypto Signals", page_icon="📈", layout="centered")
st.title("🚀 लाइव क्रिप्टो ट्रेडिंग सिग्नल्स")
st.markdown("यह टूल **Binance API** से लाइव डेटा लेकर **1-Minute Swing High/Low** स्ट्रेटेजी पर सिग्नल्स ढूंढता है।")

LOOKBACK = 4
INTERVAL = "1m"
TARGET_PCT = 0.01
SL_PCT = 0.005
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "ADAUSDT", "DOTUSDT", "XRPUSDT"]

def get_binance_data(symbol):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={INTERVAL}&limit=20"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            df = pd.DataFrame(response.json(), columns=['Ot', 'Open', 'High', 'Low', 'Close', 'V', 'Ct', 'Q', 'N', 'T1', 'T2', 'I'])
            df[['High', 'Low', 'Close']] = df[['High', 'Low', 'Close']].astype(float)
            return df
    except:
        return None
    return None

if st.button("🔄 अभी नए सिग्नल्स चेक करें", use_container_width=True):
    st.write("लाइव मार्केट डेटा स्कैन किया जा रहा है... कृपया प्रतीक्षा करें ⏳")
    signals_found = False
    
    for symbol in SYMBOLS:
        data = get_binance_data(symbol)
        if data is None: continue
        
        latest_close = float(data['Close'].iloc[-1])
        window = data.iloc[-(LOOKBACK*2+1):-1]
        if len(window) < (LOOKBACK*2): continue
        
        is_swing_high = window['High'].idxmax() == window.index[LOOKBACK]
        is_swing_low = window['Low'].idxmin() == window.index[LOOKBACK]

        if is_swing_high:
            signals_found = True
            st.error(f"🔴 **SELL SIGNAL:** {symbol} | Entry: ${latest_close:.4f} | Target: ${(latest_close*(1-TARGET_PCT)):.4f} | SL: ${(latest_close*(1+SL_PCT)):.4f}")
        elif is_swing_low:
            signals_found = True
            st.success(f"🟢 **BUY SIGNAL:** {symbol} | Entry: ${latest_close:.4f} | Target: ${(latest_close*(1+TARGET_PCT)):.4f} | SL: ${(latest_close*(1-SL_PCT)):.4f}")

    if not signals_found:
        st.info("मार्केट में अभी कोई नया स्विंग सिग्नल नहीं मिला है। थोड़ी देर बाद फिर से ट्राई करें।")