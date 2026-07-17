import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Ilu Shukla's Sniper Pro", page_icon="🎯", layout="wide")

# ====================== CUSTOM CSS ======================
st.markdown("""
<style>
    .stApp { background-color: #0a0e17; color: #e2e8f0; }
    .main-title { font-size: 44px; font-weight: 900; text-align: center;
                  background: linear-gradient(45deg, #00f2fe, #4facfe);
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sub-title { text-align:center; color:#94a3b8; margin-bottom: 25px; }
    .signal-card { background: rgba(30, 41, 59, 0.85); border-radius: 15px;
                   padding: 18px 22px; margin: 14px 0; border-left: 6px solid; }
    .buy-card { border-color: #00e676; }
    .sell-card { border-color: #ff1744; }
    .signal-row { display:flex; justify-content:space-between; flex-wrap:wrap; margin-top:8px; }
    .metric-box { background: rgba(15, 23, 42, 0.7); border-radius: 10px; padding: 8px 14px;
                  margin: 4px; min-width: 140px; text-align:center; }
    .metric-label { font-size:12px; color:#94a3b8; }
    .metric-value { font-size:17px; font-weight:700; }
    .profit { color:#00e676; }
    .loss { color:#ff1744; }
    .stat-box { background: rgba(30,41,59,0.85); border-radius:12px; padding:16px; text-align:center; }
    .stat-num { font-size:26px; font-weight:800; }
    .stat-lbl { font-size:13px; color:#94a3b8; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Ilu Shukla\'s Sniper Pro 🎯</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Swing High / Swing Low Break Strategy — Live Signals + Backtest</div>', unsafe_allow_html=True)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "ADAUSDT",
           "DOTUSDT", "XRPUSDT", "SUIUSDT", "NEARUSDT"]

IST = pytz.timezone("Asia/Kolkata")

# ====================== DATA FETCH ======================
def _fetch_klines(url, headers):
    """Low-level fetch. Returns (df, error, status_code)."""
    try:
        r = requests.get(url, timeout=10, headers=headers)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code} — {r.text[:150]}", r.status_code
        raw = r.json()
        if not isinstance(raw, list) or len(raw) == 0:
            return None, f"Khaali/ajeeb response: {str(raw)[:150]}", r.status_code
        df = pd.DataFrame(raw, columns=['Ot', 'Open', 'High', 'Low', 'Close', 'V',
                                         'Ct', 'Q', 'N', 'T1', 'T2', 'I'])
        df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].astype(float)
        df['Time'] = pd.to_datetime(df['Ot'], unit='ms').dt.tz_localize('UTC').dt.tz_convert(IST)
        return df.reset_index(drop=True), None, r.status_code
    except requests.exceptions.Timeout:
        return None, "Request timeout ho gaya — internet slow hai ya server response nahi de raha.", None
    except requests.exceptions.ConnectionError as e:
        return None, f"Connection error: {str(e)[:150]}", None
    except Exception as e:
        return None, f"Unexpected error: {str(e)[:150]}", None


@st.cache_data(ttl=25, show_spinner=False)
def get_binance_data(symbol, limit=100, interval="1m"):
    """Returns (df, error_message, source). Tries Binance Futures first; many cloud
    hosts (Streamlit Cloud, Replit, Heroku etc.) get geo-blocked (HTTP 451) on that
    endpoint, so it automatically falls back to Binance's public spot data mirror
    (data-api.binance.vision), which is not geo-restricted."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SniperPro/1.0)"}

    futures_url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    df, err, status = _fetch_klines(futures_url, headers)
    if df is not None:
        return df, None, "futures"

    # Fallback: Binance's public spot data mirror -- designed to work from any host
    spot_url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    df2, err2, status2 = _fetch_klines(spot_url, headers)
    if df2 is not None:
        return df2, None, "spot"

    if status == 451:
        combined = ("Futures API block ho gaya (HTTP 451 - geo-block, common on cloud hosting), "
                    f"aur spot fallback bhi fail ho gaya: {err2}")
    else:
        combined = f"Futures error: {err} | Spot fallback error: {err2}"
    return None, combined, None

# ====================== SWING PIVOT DETECTION ======================
def find_pivot_at(df, pos, lookback):
    """Check whether candle at integer position `pos` is a swing high/low,
    using `lookback` candles on both sides. Returns 'SELL', 'BUY', or None."""
    if pos - lookback < 0 or pos + lookback >= len(df):
        return None
    window = df.iloc[pos - lookback: pos + lookback + 1]
    if window['High'].idxmax() == df.index[pos]:
        return "SELL"
    if window['Low'].idxmin() == df.index[pos]:
        return "BUY"
    return None

def find_all_pivots(df, lookback):
    """Scan the whole dataframe and return every confirmed swing pivot."""
    pivots = []
    for pos in range(lookback, len(df) - lookback):
        sig = find_pivot_at(df, pos, lookback)
        if sig:
            pivots.append({"pos": pos, "type": sig})
    return pivots

def calc_levels(entry_price, sig_type, target_pct, sl_pct):
    if sig_type == "BUY":
        target = entry_price * (1 + target_pct / 100)
        sl = entry_price * (1 - sl_pct / 100)
    else:
        target = entry_price * (1 - target_pct / 100)
        sl = entry_price * (1 + sl_pct / 100)
    return target, sl

def add_ema(df, span=21):
    df = df.copy()
    df['EMA21'] = df['Close'].ewm(span=span, adjust=False).mean()
    return df

def ema_trend_ok(sig_type, close_price, ema_value):
    """EMA21 trend filter: BUY signals only in an uptrend (price above EMA21),
    SELL signals only in a downtrend (price below EMA21)."""
    if sig_type == "BUY":
        return close_price > ema_value
    return close_price < ema_value

tab_live, tab_backtest = st.tabs(["🔴 Live Signals", "📊 Backtest"])

# =====================================================================
# TAB 1: LIVE SIGNALS
# =====================================================================
with tab_live:
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        lookback = st.slider("Swing Lookback (candles)", 3, 10, 5)
    with c2:
        target_pct = st.number_input("Target %", value=1.0, step=0.1, min_value=0.1)
    with c3:
        sl_pct = st.number_input("Stop-Loss %", value=0.5, step=0.1, min_value=0.1)
    with c4:
        capital = st.number_input("Position Size / Margin (₹)", value=10000, step=1000, min_value=100)
    with c5:
        leverage = st.number_input("Leverage (x)", value=10, step=1, min_value=1, max_value=125)

    tf1, tf2 = st.columns([2, 1])
    with tf1:
        timeframes = st.multiselect("Timeframes Scan Karein", ["1m", "30m", "1h"],
                                     default=["1m", "30m", "1h"])
    with tf2:
        use_ema_filter = st.checkbox("EMA21 Trend Filter Lagayein", value=True)

    if leverage > 20:
        st.warning(f"⚠️ {leverage}x leverage par ek ~{round(100/leverage,1)}% adverse price move liquidation kar sakta hai. SL zaroor lagayein.")

    if st.button("🔄 अभी सिग्नल चेक करें", type="primary", use_container_width=True):
        with st.spinner("Swing High/Low Scan Chal Raha Hai..."):
            signals_found = False
            needed = lookback * 2 + 40  # extra candles so EMA21 has enough history to warm up

            fetch_errors = []
            source_note_shown = False
            for tf in timeframes:
                for symbol in SYMBOLS:
                    df, err, source = get_binance_data(symbol, limit=needed, interval=tf)
                    if df is None:
                        fetch_errors.append(f"**{symbol} ({tf})**: {err}")
                        continue
                    if len(df) < needed:
                        continue

                    if source == "spot" and not source_note_shown:
                        st.caption("ℹ️ Futures API is server se block hai — Binance ke public **spot** data se signals chal rahe hain (prices futures ke bahut kareeb hote hain).")
                        source_note_shown = True

                    # last row is the still-forming candle -> drop it, only use closed candles
                    closed = df.iloc[:-1].reset_index(drop=True)
                    closed = add_ema(closed, span=21)

                    # the most recently confirmed pivot sits `lookback` candles before the last closed candle
                    pivot_pos = len(closed) - 1 - lookback
                    sig_type = find_pivot_at(closed, pivot_pos, lookback)

                    if sig_type is None:
                        continue

                    entry_price = float(closed['Close'].iloc[-1])
                    ema_val = float(closed['EMA21'].iloc[-1])

                    if use_ema_filter and not ema_trend_ok(sig_type, entry_price, ema_val):
                        continue  # signal goes against the EMA21 trend -> skip

                    signals_found = True
                    entry_time = closed['Time'].iloc[-1].strftime("%d %b, %I:%M %p IST")
                    pivot_time = closed['Time'].iloc[pivot_pos].strftime("%I:%M %p")

                    target, sl = calc_levels(entry_price, sig_type, target_pct, sl_pct)
                    notional = capital * leverage
                    profit_amt = notional * (target_pct / 100)
                    loss_amt = notional * (sl_pct / 100)
                    rr_ratio = round(target_pct / sl_pct, 2)

                    card_class = "buy-card" if sig_type == "BUY" else "sell-card"
                    emoji = "🟢" if sig_type == "BUY" else "🔴"
                    trend_label = "Uptrend (Close > EMA21)" if entry_price > ema_val else "Downtrend (Close < EMA21)"

                    st.markdown(f"""
                    <div class="signal-card {card_class}">
                        <h3>{emoji} {sig_type} • {symbol} <span style="font-size:14px;color:#94a3b8;">({tf})</span></h3>
                        <div class="signal-row">
                            <div class="metric-box"><div class="metric-label">Entry Price</div>
                                <div class="metric-value">${entry_price:.4f}</div></div>
                            <div class="metric-box"><div class="metric-label">Entry Time</div>
                                <div class="metric-value">{entry_time}</div></div>
                            <div class="metric-box"><div class="metric-label">Swing Pivot Time</div>
                                <div class="metric-value">{pivot_time}</div></div>
                        </div>
                        <div class="signal-row">
                            <div class="metric-box"><div class="metric-label">🎯 Target Price</div>
                                <div class="metric-value profit">${target:.4f}</div></div>
                            <div class="metric-box"><div class="metric-label">🛑 SL Price</div>
                                <div class="metric-value loss">${sl:.4f}</div></div>
                            <div class="metric-box"><div class="metric-label">Risk:Reward</div>
                                <div class="metric-value">1 : {rr_ratio}</div></div>
                        </div>
                        <div class="signal-row">
                            <div class="metric-box"><div class="metric-label">EMA21</div>
                                <div class="metric-value">${ema_val:.4f}</div></div>
                            <div class="metric-box"><div class="metric-label">Trend</div>
                                <div class="metric-value">{trend_label}</div></div>
                            <div class="metric-box"><div class="metric-label">Leverage</div>
                                <div class="metric-value">{leverage}x</div></div>
                        </div>
                        <div class="signal-row">
                            <div class="metric-box"><div class="metric-label">Target पर Profit ({leverage}x)</div>
                                <div class="metric-value profit">+₹{profit_amt:,.0f}</div></div>
                            <div class="metric-box"><div class="metric-label">SL पर Nuksaan ({leverage}x)</div>
                                <div class="metric-value loss">-₹{loss_amt:,.0f}</div></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            if fetch_errors and not signals_found:
                st.error("Data fetch nahi ho paaya:\n\n" + "\n\n".join(fetch_errors[:3]))
            elif not signals_found:
                st.info("**Abhi koi clear Swing Signal nahi mila (ya EMA21 trend filter ne sab hata diya).** Market quiet hai.")
    else:
        st.write("**Button dabakar live signals dekhein** — har signal ke saath entry time, price, target, SL, EMA21 trend aur leverage ke saath possible profit/nuksaan (₹) dikhega.")

    st.caption("Strategy: Swing High/Low Break + EMA21 Trend Filter, 1m/30m/1h timeframes. Profit/Nuksaan = Position Size × Leverage × Target%/SL% (fees/slippage/funding shaamil nahi). Zyada leverage = zyada risk of liquidation, apna risk khud manage karein.")

# =====================================================================
# TAB 2: BACKTEST
# =====================================================================
with tab_backtest:
    st.markdown("#### Historical data par strategy test karo")
    b1, b2, b3 = st.columns(3)
    with b1:
        bt_symbol = st.selectbox("Symbol", SYMBOLS, index=0)
        bt_interval = st.selectbox("Candle Interval", ["1m", "3m", "5m", "15m", "30m", "1h"], index=0)
    with b2:
        bt_lookback = st.slider("Swing Lookback", 3, 10, 5, key="bt_lb")
        bt_candles = st.slider("Kitne Candles Test Karein", 200, 1000, 500, step=50)
    with b3:
        bt_target_pct = st.number_input("Target %", value=1.0, step=0.1, min_value=0.1, key="bt_tp")
        bt_sl_pct = st.number_input("Stop-Loss %", value=0.5, step=0.1, min_value=0.1, key="bt_sl")

    b4, b5, b6 = st.columns(3)
    with b4:
        bt_capital = st.number_input("Har Trade Ka Position Size / Margin (₹)", value=10000, step=1000, min_value=100, key="bt_cap")
    with b5:
        bt_leverage = st.number_input("Leverage (x)", value=10, step=1, min_value=1, max_value=125, key="bt_lev")
    with b6:
        bt_use_ema_filter = st.checkbox("EMA21 Trend Filter Lagayein", value=True, key="bt_ema")

    max_hold = st.slider("Max Holding Candles (target/SL na mile to trade band ho jaayega)", 10, 200, 60)

    if bt_leverage > 20:
        st.warning(f"⚠️ {bt_leverage}x leverage par ek ~{round(100/bt_leverage,1)}% adverse price move liquidation kar sakta hai.")

    if st.button("▶️ Backtest Chalao", type="primary", use_container_width=True):
        with st.spinner(f"{bt_symbol} ka backtest chal raha hai..."):
            df, err, source = get_binance_data(bt_symbol, limit=min(bt_candles + bt_lookback * 2 + 5, 1500), interval=bt_interval)

            if df is None:
                st.error(f"Data fetch nahi ho paaya:\n\n{err}")
            elif len(df) < bt_lookback * 3:
                st.error("Bahut kam candles mile — 'Kitne Candles Test Karein' ki value badhayein ya interval change karein.")
            else:
                if source == "spot":
                    st.caption("ℹ️ Futures API is server se block hai — Binance ke public **spot** data se backtest chal raha hai.")
                closed = df.iloc[:-1].reset_index(drop=True)  # drop forming candle
                closed = add_ema(closed, span=21)
                pivots = find_all_pivots(closed, bt_lookback)

                trades = []
                for p in pivots:
                    entry_pos = p["pos"] + bt_lookback  # candle where pivot gets confirmed = entry candle
                    if entry_pos >= len(closed) - 1:
                        continue
                    entry_price = float(closed['Close'].iloc[entry_pos])
                    entry_time = closed['Time'].iloc[entry_pos]
                    sig_type = p["type"]

                    if bt_use_ema_filter:
                        ema_val = float(closed['EMA21'].iloc[entry_pos])
                        if not ema_trend_ok(sig_type, entry_price, ema_val):
                            continue  # signal against EMA21 trend -> skip

                    target, sl = calc_levels(entry_price, sig_type, bt_target_pct, bt_sl_pct)

                    outcome, exit_time, exit_price, bars_held = "OPEN", None, None, 0
                    for j in range(entry_pos + 1, min(entry_pos + 1 + max_hold, len(closed))):
                        hi = closed['High'].iloc[j]
                        lo = closed['Low'].iloc[j]
                        bars_held = j - entry_pos
                        if sig_type == "BUY":
                            hit_target = hi >= target
                            hit_sl = lo <= sl
                        else:
                            hit_target = lo <= target
                            hit_sl = hi >= sl
                        if hit_target and hit_sl:
                            # both touched in same candle -> assume SL hits first (conservative)
                            outcome, exit_price, exit_time = "LOSS", sl, closed['Time'].iloc[j]
                            break
                        elif hit_target:
                            outcome, exit_price, exit_time = "WIN", target, closed['Time'].iloc[j]
                            break
                        elif hit_sl:
                            outcome, exit_price, exit_time = "LOSS", sl, closed['Time'].iloc[j]
                            break

                    pnl_pct = bt_target_pct if outcome == "WIN" else (-bt_sl_pct if outcome == "LOSS" else 0)
                    notional = bt_capital * bt_leverage
                    pnl_amt = notional * (pnl_pct / 100)

                    trades.append({
                        "Time": entry_time.strftime("%d %b %I:%M %p"),
                        "Type": sig_type,
                        "Entry": round(entry_price, 4),
                        "Target": round(target, 4),
                        "SL": round(sl, 4),
                        "Outcome": outcome,
                        "Bars Held": bars_held,
                        "P&L %": round(pnl_pct, 2),
                        "P&L ₹": round(pnl_amt, 0),
                    })

                if not trades:
                    st.info("Is period mein koi valid swing signal nahi mila.")
                else:
                    trades_df = pd.DataFrame(trades)
                    resolved = trades_df[trades_df["Outcome"] != "OPEN"]

                    wins = (resolved["Outcome"] == "WIN").sum()
                    losses = (resolved["Outcome"] == "LOSS").sum()
                    total_resolved = wins + losses
                    win_rate = (wins / total_resolved * 100) if total_resolved else 0
                    total_pnl = resolved["P&L ₹"].sum()
                    avg_win = resolved.loc[resolved["Outcome"] == "WIN", "P&L ₹"].mean() if wins else 0
                    avg_loss = resolved.loc[resolved["Outcome"] == "LOSS", "P&L ₹"].mean() if losses else 0

                    s1, s2, s3, s4, s5 = st.columns(5)
                    for col, num, lbl, cls in [
                        (s1, len(trades_df), "Total Signals", ""),
                        (s2, f"{win_rate:.1f}%", "Win Rate", "profit" if win_rate >= 50 else "loss"),
                        (s3, f"{wins}W / {losses}L", "Win / Loss", ""),
                        (s4, f"₹{total_pnl:,.0f}", f"Total P&L ({bt_leverage}x)", "profit" if total_pnl >= 0 else "loss"),
                        (s5, f"₹{avg_win:,.0f} / ₹{avg_loss:,.0f}", "Avg Win / Avg Loss", ""),
                    ]:
                        col.markdown(f"""
                        <div class="stat-box"><div class="stat-num {cls}">{num}</div>
                        <div class="stat-lbl">{lbl}</div></div>
                        """, unsafe_allow_html=True)

                    st.markdown("##### Equity Curve (₹)")
                    equity = resolved["P&L ₹"].cumsum()
                    st.line_chart(equity.reset_index(drop=True))

                    st.markdown("##### Trade Log")
                    def highlight_outcome(row):
                        color = "#00e676" if row["Outcome"] == "WIN" else ("#ff1744" if row["Outcome"] == "LOSS" else "#94a3b8")
                        return [f"color: {color}"] * len(row)
                    st.dataframe(trades_df.style.apply(highlight_outcome, axis=1), use_container_width=True, height=400)

                    ema_note = "EMA21 trend filter ON tha (sirf trend ke direction wale signals liye gaye)." if bt_use_ema_filter else "EMA21 trend filter OFF tha (saare swing signals liye gaye, trend ke against bhi)."
                    st.caption(f"Note: {max_hold} se zyada candles tak target/SL na milne par trade 'OPEN' maani jaati hai aur stats mein include nahi hoti. P&L {bt_leverage}x leverage ke saath calculate kiya gaya hai. {ema_note} Fees/slippage/funding shaamil nahi hain — sirf strategy ka raw performance dikhaya gaya hai.")
    else:
        st.write("Settings choose karke **Backtest Chalao** dabayein — past data par strategy ka win rate, total P&L aur equity curve dikhega.")
