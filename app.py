import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# 1. Page Config (Wide Layout for Dashboard feel)
st.set_page_config(page_title="Ilu Shukla's Sniper Pro", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS FOR PREMIUM LOOK ---
st.markdown("""
<style>
    /* Dark Theme & Background */
    .stApp {
        background-color: #0a0e17;
        color: #e2e8f0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Hide Streamlit default UI elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Premium Header Styling */
    .main-title {
        font-size: 48px;
        font-weight: 900;
        text-align: center;
        background: -webkit-linear-gradient(45deg, #00f2fe, #4facfe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        padding-top: 20px;
    }
    .sub-title {
        text-align: center;
        color: #94a3b8;
        font-size: 18px;
        letter-spacing: 1px;
        margin-bottom: 40px;
    }

    /* Signal Cards Styling */
    .signal-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 20px;
        transition: transform 0.3s ease;
    }
    .signal-card:hover {
        transform: translateY(-5px);
    }
    
    .buy-card {
        border-left: 6px solid #00e676;
        box-shadow: 0 10px 20px rgba(0, 230, 118, 0.1);
    }
    .sell-card {
        border-left: 6px solid #ff1744;
        box-shadow: 0 10px 20px rgba(255, 23, 68, 0.1);
    }

    .card-title {
        font-size: 26px;
        font-weight: bold;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .buy-color { color: #00e676; }
    .sell-color { color: #ff1744; }
    
    .price-grid {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 15px;
        margin-top: 15px;
        padding-top: 15px;
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    .price-box {
        display: flex;
        flex-direction: column;
    }
    .price-label {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
    }
    .price-value {
        font-size: 20px;
        font-weight: bold;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# 2. Premium Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2619/2619283.png", width=100)
    st.markdown("## ⚙️ Control Panel")
    st.markdown("---")
    TIMEFRAME = st.selectbox("⏳ Timeframe", ["1m", "5m", "15m", "30m", "1h"], index=3)
    WINDOW = st.number_input("📏 Pivot Window", value=45, step=2)
    TARGET_PCT = st.number_input("🎯 Target (%)", value=2.0, step=0.1) / 100
    SL_PCT = st.number_input("🛑 Stop Loss (%)", value=1.0, step=0.1) / 100
    st.markdown("---")
    st.caption("Powered by Ilu Shukla | v2.0 Pro")

# 3. Main Dashboard Header
st.markdown('<div class="main-title">Ilu Shukla\'s Sniper Pro 🎯</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">Advanced Institutional Grade Scanner • {TIMEFRAME} Live API</div>', unsafe_allow_html=True)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "ADAUSDT", "DOTUSDT", "XRPUSDT", "LINKUSDT", "NEARUSDT", "RENDERUSDT", "SUIUSDT", "APTUSDT", "TONUSDT", "OPUSDT", "ARBUSDT", "LTCUSDT", "ATOMUSDT", "FTMUSDT", "INJUSDT"]

# --- Layout: Chart on Left, Scanner on Right ---
col1, col2 = st.columns([1.5, 1])

with col1:
    st.markdown("### 📊 Interactive Live Chart")
    selected_coin = st.selectbox("Select Asset:", SYMBOLS, label_visibility="collapsed")
    
    # TradingView Widget
    tv_widget = f"""
    <div class="tradingview-widget-container" style="border-radius: 15px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
      <div id="tradingview_widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
      "width": "100%",
      "height": 550,
      "symbol": "BINANCE:{selected_coin}",
      "interval": "30",
      "timezone": "Asia/Kolkata",
      "theme": "dark",
      "style": "1",
      "locale": "in",
      "enable_publishing": false,
      "backgroundColor": "#1e293b",
      "gridColor": "#334155",
      "hide_top_toolbar": false,
      "hide_legend": false,
      "save_image": false,
      "container_id": "tradingview_widget"
      }}
      );
      </script>
    </div>
    """
    components.html(tv_widget, height=570)

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

with col2:
    st.markdown("### 🤖 Algorithmic Scanner")
    
    if st.button("⚡ EXECUTE SCAN", use_container_width=True, type="primary"):
        with st.spinner("Analyzing Market Structure..."):
            signals_found = False
            
            for symbol in SYMBOLS:
                df = get_binance_data(symbol)
                if df is None or len(df) < WINDOW: 
                    continue
                
                curr_price = float(df['Close'].iloc[-1])
                
                df['P_High'] = df['High'].rolling(window=WINDOW, center=True).max()
                df['P_Low'] = df['Low'].rolling(window=WINDOW, center=True).min()
                idx = -(WINDOW // 2 + 1)

                is_swing_high = df['High'].iloc[idx] == df['P_High'].iloc[idx]
                is_swing_low = df['Low'].iloc[idx] == df['P_Low'].iloc[idx]

                if is_swing_high:
                    signals_found = True
                    sl, target = curr_price * (1 + SL_PCT), curr_price * (1 - TARGET_PCT)
                    
                    html_card = f"""
                    <div class="signal-card sell-card">
                        <div class="card-title sell-color">🔴 SELL • {symbol}</div>
                        <div class="price-grid">
                            <div class="price-box">
                                <span class="price-label">Entry</span>
                                <span class="price-value">${curr_price:.4f}</span>
                            </div>
                            <div class="price-box">
                                <span class="price-label">Target</span>
                                <span class="price-value sell-color">${target:.4f}</span>
                            </div>
                            <div class="price-box">
                                <span class="price-label">Stop Loss</span>
                                <span class="price-value">${sl:.4f}</span>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(html_card, unsafe_allow_html=True)
                    
                elif is_swing_low:
                    signals_found = True
                    sl, target = curr_price * (1 - SL_PCT), curr_price * (1 + TARGET_PCT)
                    
                    html_card = f"""
                    <div class="signal-card buy-card">
                        <div class="card-title buy-color">🟢 BUY • {symbol}</div>
                        <div class="price-grid">
                            <div class="price-box">
                                <span class="price-label">Entry</span>
                                <span class="price-value">${curr_price:.4f}</span>
                            </div>
                            <div class="price-box">
                                <span class="price-label">Target</span>
                                <span class="price-value buy-color">${target:.4f}</span>
                            </div>
                            <div class="price-box">
                                <span class="price-label">Stop Loss</span>
                                <span class="price-value">${sl:.4f}</span>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(html_card, unsafe_allow_html=True)

            if not signals_found:
                st.info(f"Market is consolidating. No active {TIMEFRAME} setups found.")
    else:
        st.write("Click **EXECUTE SCAN** to find live pivot setups.")
