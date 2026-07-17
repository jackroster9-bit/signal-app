import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components
from datetime import datetime
import pytz

# ====================== PAGE CONFIG ======================
st.set_page_config(
    page_title="Ilu Shukla's Sniper Pro",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== CUSTOM CSS ======================
st.markdown("""
<style>
    .stApp { background-color: #0a0e17; color: #e2e8f0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    .main-title {
        font-size: 48px; font-weight: 900; text-align: center;
        background: -webkit-linear-gradient(45deg, #00f2fe, #4facfe);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0px; padding-top: 20px;
    }
    .sub-title { text-align: center; color: #94a3b8; font-size: 18px; letter-spacing: 1px; margin-bottom: 40px; }
    
    .signal-card {
        background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px);
        border-radius: 15px; padding: 25px; margin: 20px 0;
        transition: transform 0.3s ease; border: 1px solid rgba(255,255,255,0.1);
    }
    .signal-card:hover { transform: translateY(-5px); }
    
    .buy-card { border-left: 6px solid #00e676; box-shadow: 0 10px 20px rgba(0, 230, 118, 0.1); }
    .sell-card { border-left: 6px solid #ff1744; box-shadow: 0 10px 20px rgba(255, 23, 68, 0.1); }
    
    .card-title { font-size: 26px; font-weight: bold; margin-bottom: 5px; }
    .setup-name { font-size: 15px; color: #fbbf24; margin-bottom: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .signal-time { font-size: 13px; color: #94a3b8; margin-bottom: 15px; font-weight: 500; }
    .buy-color { color: #00e676; } .sell-color { color: #ff1744; }
    
    .price-grid {
        display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px;
        margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1);
    }
    .price-box { display: flex; flex-direction: column; }
    .price-label { font-size: 13px; color: #94a3b8; text-transform: uppercase; margin-bottom: 5px; }
    .price-value { font-size: 18px; font-weight: bold; color: #ffffff; }
    .pnl-value { font-size: 16px; font-weight: bold; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# ====================== SIDEBAR ======================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2619/2619283.png", width=100)
    st.markdown("## ⚙️ Trading Setup")
    st.markdown("---")
    
    CAPITAL = st.number_input("💵 आपकी कैपिटल (₹)", value=10000, step=1000, min_value=1000)
    LEVERAGE = st.number_input("⚡ लिवरेज (x)", value=10, step=1, min_value=1)
    
    st.markdown("---")
    st.info("🕒 **Timeframe:** 1 Minute (Scalping)")
    TARGET_PCT = st.number_input("🎯 Target (%)", value=1.5, step=0.1) / 100
    SL_PCT = st.number_input("🛑 Stop Loss (%)", value=0.5, step=0.1) / 100
    
    st.markdown("---")
    position_size = CAPITAL * LEVERAGE
    st.success(f"💼 **टोटल पोज़िशन साइज़:** ₹{position_size:,.0f}")
    st.caption("🔥 6-in-1 Strategy: SMC + EMA + RSI + BB")

# ====================== HEADER ======================
st.markdown('<div class="main-title">Ilu Shukla\'s Sniper Pro 🎯</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">Ultimate 1m Scalper • Capital: ₹{CAPITAL:,} | Leverage: {LEVERAGE}x</div>', unsafe_allow_html=True)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "ADAUSDT", "DOTUSDT", 
           "XRPUSDT", "LINKUSDT", "NEARUSDT", "RENDERUSDT", "SUIUSDT", "APTUSDT", 
           "TONUSDT", "OPUSDT", "ARBUSDT", "LTCUSDT", "ATOMUSDT", "FTMUSDT", "INJUSDT"]

@st.cache_data(ttl=30)  # Cache for 30 seconds
def get_combined_data(symbol):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m&limit=100"
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        data = response.json()
        
        df = pd.DataFrame(data, columns=['Ot', 'Open', 'High', 'Low', 'Close', 'V', 'Ct', 'Q', 'N', 'T1', 'T2', 'I'])
        df = df[['Ot', 'Open', 'High', 'Low', 'Close']].copy()
        df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].astype(float)
        
        ist = pytz.timezone('Asia/Kolkata')
        df['Time'] = pd.to_datetime(df['Ot'], unit='ms').dt.tz_localize('UTC').dt.tz_convert(ist)
        
        # Technical Indicators
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = -delta.clip(upper=0).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['STD20'] = df['Close'].rolling(window=20).std()
        df['Upper_BB'] = df['SMA20'] + (2 * df['STD20'])
        df['Lower_BB'] = df['SMA20'] - (2 * df['STD20'])
        
        # SMC
        df['Bull_FVG'] = (df['Low'] > df['High'].shift(2)) & (df['Close'] > df['Open'])
        df['Bear_FVG'] = (df['High'] < df['Low'].shift(2)) & (df['Close'] < df['Open'])
        
        df['Bull_OB'] = (df['Close'].shift(1) < df['Open'].shift(1)) & (df['Close'] > df['Open']) & (df['Close'] > df['High'].shift(1))
        df['Bear_OB'] = (df['Close'].shift(1) > df['Open'].shift(1)) & (df['Close'] < df['Open']) & (df['Close'] < df['Low'].shift(1))
        
        df['Swing_High'] = df['High'].rolling(window=5, center=True).max()
        df['Swing_Low'] = df['Low'].rolling(window=5, center=True).min()
        
        return df
    except Exception as e:
        st.error(f"Error fetching {symbol}: {e}")
        return None

def render_chart(symbol):
    tv_widget = f"""
    <div style="border-radius:15px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,0.5); margin:20px 0;">
        <div id="tradingview_{symbol}"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
            "width": "100%",
            "height": 480,
            "symbol": "BINANCE:{symbol}",
            "interval": "1",
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
            "container_id": "tradingview_{symbol}"
        }});
        </script>
    </div>
    """
    components.html(tv_widget, height=520)

# ====================== SCANNER ======================
st.markdown("### 🤖 Ultimate Auto-Scanner (1m Scalper)")

if st.button("⚡ EXECUTE ULTIMATE SCAN", use_container_width=True, type="primary"):
    with st.spinner("SMC + Indicators स्कैन हो रहा है..."):
        signals_found = False
        est_profit = position_size * TARGET_PCT
        est_loss = position_size * SL_PCT
        
        for symbol in SYMBOLS:
            df = get_combined_data(symbol)
            if df is None or len(df) < 30:
                continue
                
            curr_close = float(df['Close'].iloc[-1])
            signal_time = df['Time'].iloc[-1].strftime("%I:%M %p IST")
            
            is_buy = False
            is_sell = False
            setup_name = ""
            
            # === SMC Priority ===
            if df['Bull_FVG'].iloc[-2]:
                is_buy, setup_name = True, "💎 SMC: BULLISH FVG"
            elif df['Bull_OB'].iloc[-2]:
                is_buy, setup_name = True, "💎 SMC: BULLISH ORDER BLOCK"
            elif df['Low'].iloc[-2] == df['Swing_Low'].iloc[-3]:
                is_buy, setup_name = True, "💎 SMC: SUPPORT BOUNCE"
                
            elif df['Bear_FVG'].iloc[-2]:
                is_sell, setup_name = True, "🩸 SMC: BEARISH FVG"
            elif df['Bear_OB'].iloc[-2]:
                is_sell, setup_name = True, "🩸 SMC: BEARISH ORDER BLOCK"
            elif df['High'].iloc[-2] == df['Swing_High'].iloc[-3]:
                is_sell, setup_name = True, "🩸 SMC: RESISTANCE REJECTION"
            
            # === Indicators (if no SMC) ===
            if not is_buy and not is_sell:
                prev_ema9, curr_ema9 = df['EMA9'].iloc[-2], df['EMA9'].iloc[-1]
                prev_ema21, curr_ema21 = df['EMA21'].iloc[-2], df['EMA21'].iloc[-1]
                curr_rsi = df['RSI'].iloc[-1]
                curr_close = df['Close'].iloc[-1]
                
                if curr_rsi < 30:
                    is_buy, setup_name = True, "🟢 RSI OVERSOLD (<30)"
                elif prev_ema9 <= prev_ema21 and curr_ema9 > curr_ema21:
                    is_buy, setup_name = True, "🚀 EMA 9/21 BULLISH CROSS"
                elif curr_close > df['Upper_BB'].iloc[-1]:
                    is_buy, setup_name = True, "🔥 BB UPPER BREAKOUT"
                    
                elif curr_rsi > 70:
                    is_sell, setup_name = True, "🔴 RSI OVERBOUGHT (>70)"
                elif prev_ema9 >= prev_ema21 and curr_ema9 < curr_ema21:
                    is_sell, setup_name = True, "🔻 EMA 9/21 BEARISH CROSS"
                elif curr_close < df['Lower_BB'].iloc[-1]:
                    is_sell, setup_name = True, "🩸 BB LOWER BREAKDOWN"
            
            # === Render Signals ===
            if is_buy:
                signals_found = True
                sl = curr_close * (1 - SL_PCT)
                target = curr_close * (1 + TARGET_PCT)
                
                html_card = f"""
                <div class="signal-card buy-card">
                    <div class="card-title buy-color">🟢 BUY • {symbol}</div>
                    <div class="setup-name">⚡ {setup_name}</div>
                    <div class="signal-time">🕒 {signal_time} | 1m</div>
                    <div class="price-grid">
                        <div class="price-box"><span class="price-label">Entry</span><span class="price-value">${curr_close:.4f}</span></div>
                        <div class="price-box"><span class="price-label">Target ({TARGET_PCT*100:.1f}%)</span><span class="price-value">${target:.4f}</span><span class="buy-color pnl-value">+ ₹{est_profit:,.0f}</span></div>
                        <div class="price-box"><span class="price-label">Stop Loss ({SL_PCT*100:.1f}%)</span><span class="price-value">${sl:.4f}</span><span class="sell-color pnl-value">- ₹{est_loss:,.0f}</span></div>
                    </div>
                </div>
                """
                st.markdown(html_card, unsafe_allow_html=True)
                render_chart(symbol)
                
            elif is_sell:
                signals_found = True
                sl = curr_close * (1 + SL_PCT)
                target = curr_close * (1 - TARGET_PCT)
                
                html_card = f"""
                <div class="signal-card sell-card">
                    <div class="card-title sell-color">🔴 SELL • {symbol}</div>
                    <div class="setup-name">⚡ {setup_name}</div>
                    <div class="signal-time">🕒 {signal_time} | 1m</div>
                    <div class="price-grid">
                        <div class="price-box"><span class="price-label">Entry</span><span class="price-value">${curr_close:.4f}</span></div>
                        <div class="price-box"><span class="price-label">Target ({TARGET_PCT*100:.1f}%)</span><span class="price-value">${target:.4f}</span><span class="buy-color pnl-value">+ ₹{est_profit:,.0f}</span></div>
                        <div class="price-box"><span class="price-label">Stop Loss ({SL_PCT*100:.1f}%)</span><span class="price-value">${sl:.4f}</span><span class="sell-color pnl-value">- ₹{est_loss:,.0f}</span></div>
                    </div>
                </div>
                """
                st.markdown(html_card, unsafe_allow_html=True)
                render_chart(symbol)
        
        if not signals_found:
            st.info("🚫 मार्केट अभी शांत है। कोई मजबूत सेटअप नहीं मिला। थोड़ी देर बाद दोबारा ट्राई करें।")

else:
    st.info("**EXECUTE ULTIMATE SCAN** बटन दबाकर लाइव सिग्नल्स देखें")
