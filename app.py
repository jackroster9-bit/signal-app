import streamlit as st
import pandas as pd
import requests
import pytz
from datetime import datetime

st.set_page_config(page_title="Ilu Shukla • Sniper Pro", page_icon="🎯", layout="wide")

# ====================== CSS ======================
st.markdown("""
<style>
    .stApp { background-color: #0a111f; color: #e2e8f0; }
    .main-title { font-size: 44px; font-weight: 900; text-align: center; 
                  background: linear-gradient(90deg, #00f5ff, #5e72ff); 
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .signal-card { background: #13213a; border-radius: 16px; padding: 20px; margin: 15px 0; border-left: 5px solid; }
    .buy-card { border-color: #00ff9d; }
</style>
""", unsafe_allow_html=True)

# ====================== SIDEBAR ======================
with st.sidebar:
    st.title("Ilu Shukla Sniper Pro")
    CAPITAL = st.number_input("💰 Capital (₹)", value=15000, step=1000)
    RISK_PERCENT = st.slider("Risk % per Trade", 0.5, 2.0, 1.0, 0.1)

st.markdown('<div class="main-title">ILU SHUKLA SNIPER PRO</div>', unsafe_allow_html=True)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "SUIUSDT", "XRPUSDT"]

# ====================== DATA FETCH (Safe) ======================
@st.cache_data(ttl=25)
def get_data(symbol, interval="1m", limit=500):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if len(data) < 30:
            return None
        df = pd.DataFrame(data, columns=['ot','o','h','l','c','v','ct','q','n','tb','tq','ig'])
        df = df[['ot','o','h','l','c','v']].astype(float)
        df['Time'] = pd.to_datetime(df['ot'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        df['Close'] = df['c']
        df['Volume'] = df['v']
        return df
    except:
        return None

tab1, tab2 = st.tabs(["🚀 Live Scanner", "📊 Backtesting"])

# ====================== LIVE SCANNER ======================
with tab1:
    if st.button("🚀 RUN LIVE SCAN", type="primary", use_container_width=True):
        with st.spinner("Market Scan Chal Raha Hai..."):
            found = False
            for symbol in SYMBOLS:
                df = get_data(symbol)
                if df is None or len(df) < 30:
                    continue
                    
                close = float(df['Close'].iloc[-1])
                vol = float(df['Volume'].iloc[-1])
                avg_vol = float(df['Volume'].rolling(20).mean().iloc[-1])
                
                df['EMA9'] = df['Close'].ewm(span=9).mean()
                df['EMA21'] = df['Close'].ewm(span=21).mean()
                delta = df['Close'].diff()
                df['RSI'] = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / 
                                               -delta.clip(upper=0).rolling(14).mean())))
                
                if (df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1]) and (vol > avg_vol * 1.5) and (df['RSI'].iloc[-1] < 40):
                    found = True
                    st.markdown(f"""
                    <div class="signal-card buy-card">
                        <h3>🟢 BUY • {symbol}</h3>
                        <p>Price: ${close:.4f} | Time: {df['Time'].iloc[-1].strftime('%I:%M %p')}</p>
                        <p>Volume Spike + EMA Bullish</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            if not found:
                st.info("Abhi koi strong signal nahi mila. Thodi der baad try karein.")

# ====================== BACKTESTING ======================
with tab2:
    st.subheader("📊 Backtesting")
    days = st.slider("Backtest Days", 5, 30, 10)
    
    if st.button("🔥 Run Backtest", type="primary", use_container_width=True):
        progress = st.progress(0)
        results = []
        
        for idx, symbol in enumerate(SYMBOLS):
            df = get_data(symbol, limit=days*1440)
            if df is None or len(df) < 100:
                progress.progress((idx+1)/len(SYMBOLS))
                continue
                
            df['EMA9'] = df['Close'].ewm(span=9).mean()
            df['EMA21'] = df['Close'].ewm(span=21).mean()
            delta = df['Close'].diff()
            df['RSI'] = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / 
                                           -delta.clip(upper=0).rolling(14).mean())))
            df['AvgVol'] = df['Volume'].rolling(20).mean()
            
            trades = 0
            wins = 0
            total_pnl = 0.0
            
            for j in range(50, len(df)-15):
                row = df.iloc[j]
                if (row['EMA9'] > row['EMA21']) and (row['Volume'] > row['AvgVol'] * 1.45) and (row['RSI'] < 38):
                    trades += 1
                    future_price = df['Close'].iloc[j+12]   # 12 candles ahead (~12 min)
                    pnl = (future_price - row['Close']) / row['Close'] * 100
                    total_pnl += pnl
                    if pnl > 0:
                        wins += 1
            
            if trades > 0:
                winrate = (wins / trades) * 100
                results.append({
                    'Symbol': symbol,
                    'Trades': trades,
                    'Win Rate %': round(winrate, 1),
                    'Total PnL %': round(total_pnl, 2)
                })
            
            progress.progress((idx+1)/len(SYMBOLS))
        
        if results:
            df_res = pd.DataFrame(results)
            st.success("✅ Backtest Complete!")
            st.dataframe(df_res, use_container_width=True)
            st.metric("Average Win Rate", f"{df_res['Win Rate %'].mean():.1f}%")
            st.metric("Total Trades", df_res['Trades'].sum())
        else:
            st.warning("Is period mein trades nahi mile. Days badha ke ya Volume multiplier kam karke try karein.")

st.caption("Made with ❤️ for Ilu Shukla")
