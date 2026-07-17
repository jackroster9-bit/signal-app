import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# 1. Page Config
st.set_page_config(page_title="Ilu Shukla's Sniper Pro", page_icon="🎯", layout="centered")

# 2. Sidebar Settings
with st.sidebar:
    st.header("⚙️ ऐप सेटिंग्स")
    TIMEFRAME = st.selectbox("Timeframe (कैंडल का समय)", ["1m", "5m", "15m", "30m", "1h"], index=3) # डिफ़ॉल्ट 30m
    WINDOW = st.number_input("Pivot Window (कैंडल्स)", value=45, step=2)
    TARGET_PCT = st.number_input("Target (%)", value=2.0, step=0.1) / 100
    SL_PCT = st.number_input("Stop Loss (%)", value=1.0, step=0.1) / 100
    st.markdown("---")
    st.info("💡 **टिप:** असली Sniper Pro स्ट्रेटेजी 30m टाइमफ्रेम और 45 विंडो पर सबसे अच्छी काम करती है, लेकिन आप टेस्टिंग के लिए 1m कर सकते हैं।")

# 3. Main Header
st.title("🎯 Ilu Shukla's Sniper Pro")
st.markdown(f"लाइव **Binance API** डेटा के साथ **{TIMEFRAME} Pivot High/Low** स्कैनर।")
st.markdown("---")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "ADAUSDT", "DOTUSDT", "XRPUSDT", "LINKUSDT", "NEARUSDT", "RENDERUSDT", "SUIUSDT", "APTUSDT", "TONUSDT", "OPUSDT", "ARBUSDT", "LTCUSDT", "ATOMUSDT", "FTMUSDT", "INJUSDT"]

# --- ट्रेडिंगव्यू लाइव चार्ट ---
st.subheader("📊 लाइव मार्केट चार्ट (TradingView)")
selected_coin = st.selectbox("चार्ट देखने के लिए कॉइन चुनें:", SYMBOLS)

tv_widget = f"""
<div class="tradingview-widget-container">
  <div id="tradingview_widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget(
  {{
  "width": "100%",
  "height": 450,
  "symbol": "BINANCE:{selected_coin}",
  "interval": "30",
  "timezone": "Asia/Kolkata",
  "theme": "dark",
  "style": "1",
  "locale": "in",
  "enable_publishing": false,
  "backgroundColor": "#131722",
  "hide_top_toolbar": false,
  "hide_legend": false,
  "save_image": false,
  "container_id": "tradingview_widget"
  }}
  );
  </script>
</div>
"""
components.html(tv_widget, height=450)
st.markdown("---")
# ----------------------------------------

def get_binance_data(symbol):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={TIMEFRAME}&limit=100"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            df = pd.DataFrame(response.json(), columns=['Ot', 'Open', 'High', 'Low', 'Close', 'V', 'Ct', 'Q', 'N', 'T1', 'T2', 'I'])
            df[['High', 'Low', 'Close']] = df[['High', 'Low', 'Close']].astype(float)
            return df
    except:
        return None
    return None

# 4. Auto Scanner (Pivot Logic)
st.subheader("🤖 ऑटोमैटिक सिग्नल स्कैनर")
if st.button("🚀 मार्केट स्कैन करें", use_container_width=True, type="primary"):
    with st.spinner(f"लाइव मार्केट डेटा स्कैन किया जा रहा है ({TIMEFRAME} टाइमफ्रेम)... ⏳"):
        signals_found = False
        cols = st.columns(2)
        col_idx = 0

        for symbol in SYMBOLS:
            df = get_binance_data(symbol)
            if df is None or len(df) < WINDOW: 
                continue
            
            curr_price = float(df['Close'].iloc[-1])
            
            # Pivot Strategy Logic
            df['P_High'] = df['High'].rolling(window=WINDOW, center=True).max()
            df['P_Low'] = df['Low'].rolling(window=WINDOW, center=True).min()
            
            idx = -(WINDOW // 2 + 1)

            is_swing_high = df['High'].iloc[idx] == df['P_High'].iloc[idx]
            is_swing_low = df['Low'].iloc[idx] == df['P_Low'].iloc[idx]

            if is_swing_high:
                signals_found = True
                sl, target = curr_price * (1 + SL_PCT), curr_price * (1 - TARGET_PCT)
                with cols[col_idx % 2]:
                    st.error(f"🔴 **SELL: {symbol}**\n\n**Entry:** ${curr_price:.4f}\n\n**Target:** ${target:.4f}\n\n**SL:** ${sl:.4f}")
                col_idx += 1
                
            elif is_swing_low:
                signals_found = True
                sl, target = curr_price * (1 - SL_PCT), curr_price * (1 + TARGET_PCT)
                with cols[col_idx % 2]:
                    st.success(f"🟢 **BUY: {symbol}**\n\n**Entry:** ${curr_price:.4f}\n\n**Target:** ${target:.4f}\n\n**SL:** ${sl:.4f}")
                col_idx += 1

        if not signals_found:
            st.info(f"📊 मार्केट में अभी {TIMEFRAME} टाइमफ्रेम पर कोई नया Pivot सिग्नल नहीं मिला है।")
