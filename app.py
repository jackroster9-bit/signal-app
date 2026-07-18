import streamlit as st
import pandas as pd
import numpy as np
import requests
import pytz
import time

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
                  margin: 4px; min-width: 130px; text-align:center; }
    .metric-label { font-size:12px; color:#94a3b8; }
    .metric-value { font-size:16px; font-weight:700; }
    .profit { color:#00e676; }
    .loss { color:#ff1744; }
    .stat-box { background: rgba(30,41,59,0.85); border-radius:12px; padding:16px; text-align:center; }
    .stat-num { font-size:26px; font-weight:800; }
    .stat-lbl { font-size:13px; color:#94a3b8; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Ilu Shukla\'s Sniper Pro 🎯</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">AlphaTrend Engine + EMA / VWAP / ADX / Volume / FVG / BOS / ML Filters</div>', unsafe_allow_html=True)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "ADAUSDT",
           "DOTUSDT", "XRPUSDT", "SUIUSDT", "NEARUSDT", "XAUTUSDT"]

IST = pytz.timezone("Asia/Kolkata")

# locked constants (match the Pine Script's hard-coded values)
ADX_THRESHOLD = 18
FVG_LOOKBACK = 10
BOS_LOOKBACK = 10
AT_ATR_PERIOD = 14
AT_COEFF = 1.0
ML_ATR_LEN = 14
ML_VOL_LEN = 20
ML_EVAL_WINDOW = 10
ML_EVAL_ATR_MULT = 1.0
ML_LOOKBACK = 100
ML_KNN_K = 5
ML_MIN_CONF = 40

# ====================== DATA FETCH ======================
def _fetch_klines(url, headers):
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
        df['Volume'] = df['V'].astype(float)
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
    """Returns (df, error_message, source). Tries Binance Futures first; falls back to
    Binance's public spot data mirror (data-api.binance.vision) if futures is geo-blocked."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SniperPro/1.0)"}
    futures_url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    df, err, status = _fetch_klines(futures_url, headers)
    if df is not None:
        return df, None, "futures"
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

# ====================== INDICATOR LIBRARY ======================
def true_range(df):
    high, low, close = df['High'], df['Low'], df['Close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def wilder_smooth(series, period):
    return series.ewm(alpha=1 / period, adjust=False).mean()

def calc_mfi(df, period=14):
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = typical * df['Volume']
    delta = typical.diff()
    pos_sum = money_flow.where(delta > 0, 0.0).rolling(period).sum()
    neg_sum = money_flow.where(delta < 0, 0.0).rolling(period).sum()
    ratio = pos_sum / neg_sum.replace(0, np.nan)
    return (100 - (100 / (1 + ratio))).fillna(50.0)

def calc_vwap_session(df):
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    tpv = typical * df['Volume']
    date = df['Time'].dt.date
    cum_tpv = tpv.groupby(date).cumsum()
    cum_vol = df['Volume'].groupby(date).cumsum()
    return cum_tpv / cum_vol.replace(0, np.nan)

def calc_adx(df, period=9):
    high, low = df['High'], df['Low']
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    atr = wilder_smooth(true_range(df), period)
    plus_di = 100 * wilder_smooth(pd.Series(plus_dm, index=df.index), period) / atr.replace(0, np.nan)
    minus_di = 100 * wilder_smooth(pd.Series(minus_dm, index=df.index), period) / atr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = wilder_smooth(dx, period)
    return plus_di.fillna(0), minus_di.fillna(0), adx.fillna(0)

def calc_alphatrend(df, coeff=AT_COEFF, ap=AT_ATR_PERIOD):
    """Recursive AlphaTrend (needs a sequential loop, matches Pine's var-based recursion).
    Note: the rare momentum-override edge case from the original script is skipped here
    for simplicity/robustness — the core trend logic is otherwise faithful."""
    tr = true_range(df)
    atr_sma = tr.shift(1).rolling(ap).mean()
    mfi = calc_mfi(df, ap).shift(1)
    up_t = df['Low'].shift(1) - atr_sma * coeff
    dn_t = df['High'].shift(1) + atr_sma * coeff

    n = len(df)
    at = np.zeros(n)
    u_vals, d_vals, m_vals = up_t.values, dn_t.values, mfi.values
    for i in range(n):
        prev = at[i - 1] if i > 0 else 0.0
        u, d, m = u_vals[i], d_vals[i], m_vals[i]
        if np.isnan(u) or np.isnan(d) or np.isnan(m):
            at[i] = prev
        elif m >= 50:
            at[i] = u if u >= prev else prev
        else:
            at[i] = d if d <= prev else prev

    direction = np.ones(n, dtype=int)
    for i in range(3, n):
        if at[i - 1] > at[i - 3]:
            direction[i] = 1
        elif at[i - 1] < at[i - 3]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]

    alpha_trend = pd.Series(at, index=df.index)
    direction_s = pd.Series(direction, index=df.index)
    is_bullish = (direction_s == 1) & (df['Close'] > alpha_trend)
    is_bearish = (direction_s == -1) & (df['Close'] < alpha_trend)
    return alpha_trend, is_bullish, is_bearish

def barssince(bool_series):
    vals = bool_series.values
    result = np.full(len(vals), np.inf)
    last_true = None
    for i in range(len(vals)):
        if vals[i]:
            last_true = i
        result[i] = (i - last_true) if last_true is not None else np.inf
    return pd.Series(result, index=bool_series.index)

def calc_fvg(df, lookback=FVG_LOOKBACK):
    bullish = (df['Low'] > df['High'].shift(2)) & (df['Close'].shift(1) > df['Open'].shift(1))
    bearish = (df['High'] < df['Low'].shift(2)) & (df['Close'].shift(1) < df['Open'].shift(1))
    return barssince(bullish) <= lookback, barssince(bearish) <= lookback

def calc_bos(df, lookback=BOS_LOOKBACK):
    swing_high = df['High'].rolling(lookback).max().shift(1)
    swing_low = df['Low'].rolling(lookback).min().shift(1)
    return df['Close'] > swing_high, df['Close'] < swing_low

def calc_ml_filter(df, alpha_trend, atr_len=ML_ATR_LEN, vol_len=ML_VOL_LEN,
                    eval_window=ML_EVAL_WINDOW, eval_atr_mult=ML_EVAL_ATR_MULT,
                    ml_lookback=ML_LOOKBACK, knn_k=ML_KNN_K, min_conf=ML_MIN_CONF):
    """Causal/online KNN classifier — mirrors the Pine Script's incremental training set,
    so it only ever learns from bars already seen (no lookahead)."""
    atr = wilder_smooth(true_range(df), atr_len)
    vol_avg = df['Volume'].rolling(vol_len).mean()
    vol_ratio = np.where(vol_avg > 0, df['Volume'] / vol_avg, 1.0)
    f1 = np.minimum(vol_ratio / 3.0, 1.0)

    atr_v = atr.values
    close = df['Close'].values
    open_ = df['Open'].values
    at_v = alpha_trend.values

    safe_atr = np.where(atr_v > 0, atr_v, 1)
    dist = np.where(atr_v > 0, np.abs(close - at_v) / safe_atr, np.nan)
    f2 = np.where(np.isnan(dist), 0.5, 1.0 - np.minimum(dist / 3.0, 1.0))
    disp = np.where(atr_v > 0, np.abs(close - open_) / safe_atr, 0.0)
    f3 = np.minimum(disp / 3.0, 1.0)

    n = len(df)
    train_f1, train_f2, train_f3, train_label = [], [], [], []
    ml_conf = np.full(n, 50.0)
    warmup = eval_window + atr_len + vol_len

    for i in range(n):
        j = i - eval_window
        if i > warmup and j >= 0 and not np.isnan(atr_v[j]) and atr_v[j] > 0:
            fut_move = abs(close[i] - close[j])
            label = 1.0 if fut_move > atr_v[j] * eval_atr_mult else 0.0
            train_f1.append(f1[j]); train_f2.append(f2[j]); train_f3.append(f3[j]); train_label.append(label)
            if len(train_f1) > ml_lookback:
                train_f1.pop(0); train_f2.pop(0); train_f3.pop(0); train_label.pop(0)

        n_train = len(train_label)
        if n_train > 0:
            d1 = f1[i] - np.array(train_f1)
            d2 = f2[i] - np.array(train_f2)
            d3 = f3[i] - np.array(train_f3)
            dists = np.sqrt(d1 ** 2 + d2 ** 2 + d3 ** 2)
            k_eff = min(knn_k, n_train)
            nearest = np.argsort(dists)[:k_eff]
            votes = sum(train_label[k] for k in nearest)
            ml_conf[i] = votes / k_eff * 100.0

    ml_conf_s = pd.Series(ml_conf, index=df.index)
    return ml_conf_s, ml_conf_s >= min_conf

def calc_ref_candle(df):
    """Daily High/Low Reference Candle: the very first candle of each day sets a
    high/low range; that range stays fixed for the rest of the day and is used as
    a breakout trigger (price must break above/below it, on top of the other filters)."""
    date = df['Time'].dt.date
    ref_high = df.groupby(date)['High'].transform('first')
    ref_low = df.groupby(date)['Low'].transform('first')
    return ref_high, ref_low

def add_all_indicators(df, ema_length=9):
    df = df.copy()
    df['EMA'] = df['Close'].ewm(span=ema_length, adjust=False).mean()
    df['VWAP'] = calc_vwap_session(df)
    _, _, df['ADX'] = calc_adx(df, period=9)
    df['VolAvg3'] = df['Volume'].rolling(3).mean()
    alpha_trend, at_bull, at_bear = calc_alphatrend(df)
    df['AlphaTrend'] = alpha_trend
    df['AT_Bullish'] = at_bull
    df['AT_Bearish'] = at_bear
    df['FVG_Long'], df['FVG_Short'] = calc_fvg(df)
    df['BOS_Long'], df['BOS_Short'] = calc_bos(df)
    df['RefHigh'], df['RefLow'] = calc_ref_candle(df)
    df['ML_Conf'], df['ML_Zone'] = calc_ml_filter(df, alpha_trend)
    return df

def generate_signals(df, use_ema=True, use_vwap=True, use_adx=False, use_vol=False,
                      use_fvg=False, use_bos=False, use_ml=True, use_ref_candle=False):
    true_s = pd.Series(True, index=df.index)
    ema_call = (df['Close'] > df['EMA']) if use_ema else true_s
    ema_put = (df['Close'] < df['EMA']) if use_ema else true_s
    vwap_call = (df['Close'] > df['VWAP']) if use_vwap else true_s
    vwap_put = (df['Close'] < df['VWAP']) if use_vwap else true_s
    adx_ok = (df['ADX'] >= ADX_THRESHOLD) if use_adx else true_s
    vol_ok = (df['Volume'] > df['VolAvg3']) if use_vol else true_s
    fvg_long = df['FVG_Long'] if use_fvg else true_s
    fvg_short = df['FVG_Short'] if use_fvg else true_s
    bos_long = df['BOS_Long'] if use_bos else true_s
    bos_short = df['BOS_Short'] if use_bos else true_s
    ml_zone = df['ML_Zone'] if use_ml else true_s

    unified_buy = ema_call & vwap_call & adx_ok & vol_ok & fvg_long & bos_long & df['AT_Bullish'] & ml_zone
    unified_sell = ema_put & vwap_put & adx_ok & vol_ok & fvg_short & bos_short & df['AT_Bearish'] & ml_zone

    if use_ref_candle:
        # only the exact moment price CROSSES the day's opening range — not every bar
        # after that the level stays broken (otherwise it barely filters anything post-breakout)
        crossed_above = (df['High'] >= df['RefHigh']) & (df['High'].shift(1) < df['RefHigh'])
        crossed_below = (df['Low'] <= df['RefLow']) & (df['Low'].shift(1) > df['RefLow'])
        buy_cond = crossed_above & unified_buy
        sell_cond = crossed_below & unified_sell
    else:
        buy_cond = unified_buy
        sell_cond = unified_sell

    raw_buy = buy_cond & (~buy_cond.shift(1).fillna(False))
    raw_sell = sell_cond & (~sell_cond.shift(1).fillna(False))
    return raw_buy, raw_sell

def calc_levels(entry_price, sig_type, target_pct, sl_pct):
    if sig_type == "BUY":
        return entry_price * (1 + target_pct / 100), entry_price * (1 - sl_pct / 100)
    return entry_price * (1 - target_pct / 100), entry_price * (1 + sl_pct / 100)

# ====================== SHARED FILTER-TOGGLE UI ======================
def filter_toggle_row(key_prefix):
    st.markdown("###### ⚙️ Algo Filters (jaisa Pine Script mein hai, ON/OFF)")
    f1, f2, f3, f4, f5, f6, f7, f8 = st.columns(8)
    with f1:
        use_ema = st.checkbox("EMA", value=True, key=f"{key_prefix}_ema")
    with f2:
        use_vwap = st.checkbox("VWAP", value=True, key=f"{key_prefix}_vwap")
    with f3:
        use_adx = st.checkbox("ADX", value=True, key=f"{key_prefix}_adx")
    with f4:
        use_vol = st.checkbox("Volume", value=True, key=f"{key_prefix}_vol")
    with f5:
        use_fvg = st.checkbox("FVG", value=False, key=f"{key_prefix}_fvg")
    with f6:
        use_bos = st.checkbox("BOS", value=True, key=f"{key_prefix}_bos")
    with f7:
        use_ml = st.checkbox("ML (KNN)", value=True, key=f"{key_prefix}_ml")
    with f8:
        use_ref_candle = st.checkbox("Ref Candle", value=True, key=f"{key_prefix}_ref",
                                       help="Daily High/Low Reference Candle: din ki pehli candle ka high/low ek range banata hai. Signal sirf tabhi aayega jab price is range se pehli baar cross kare (baar-baar nahi, jab tak wapas range ke andar aakar dobara cross na kare).")
    return use_ema, use_vwap, use_adx, use_vol, use_fvg, use_bos, use_ml, use_ref_candle

tab_live, tab_backtest = st.tabs(["🔴 Live Signals", "📊 Backtest"])

# =====================================================================
# TAB 1: LIVE SIGNALS
# =====================================================================
with tab_live:
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        target_pct = st.number_input("Target %", value=1.0, step=0.1, min_value=0.1)
    with c2:
        sl_pct = st.number_input("Stop-Loss %", value=0.5, step=0.1, min_value=0.1)
    with c3:
        capital = st.number_input("Position Size / Margin (₹)", value=10000, step=1000, min_value=100)
    with c4:
        leverage = st.number_input("Leverage (x)", value=10, step=1, min_value=1, max_value=125)
    with c5:
        ema_length = st.number_input("EMA Length", value=9, step=1, min_value=2)

    timeframes = st.multiselect("Timeframes Scan Karein", ["1m", "30m", "1h"], default=["1m", "30m", "1h"])
    use_ema, use_vwap, use_adx, use_vol, use_fvg, use_bos, use_ml, use_ref_candle = filter_toggle_row("live")

    d1, d2 = st.columns(2)
    with d1:
        wait_candle_close = st.checkbox("Wait For Candle Close (Slower but Safe)", value=True,
                                          help="ON (default): sirf poori ho chuki candle par signal — thoda slow, lekin stable/final. OFF: abhi ban rahi candle par bhi check hoga — turant milega, lekin candle close hone tak repaint (badal) sakta hai.")
    with d2:
        auto_refresh = st.checkbox("Auto-Refresh (har 30 sec)", value=False,
                                     help="ON karne par page har 30 second mein khud check karega, taaki koi signal miss na ho.")

    if leverage > 20:
        st.warning(f"⚠️ {leverage}x leverage par ek ~{round(100/leverage,1)}% adverse price move liquidation kar sakta hai. SL zaroor lagayein.")

    if st.button("🔄 अभी सिग्नल चेक करें", type="primary", use_container_width=True):
        with st.spinner("AlphaTrend + Filters Scan Chal Raha Hai..."):
            signals_found = False

            fetch_errors = []
            source_note_shown = False
            for tf in timeframes:
                needed = 1500 if tf == "1m" else 300  # 1m needs ~1 day of candles so the daily Ref Candle is the real day-open, not just window-start
                for symbol in SYMBOLS:
                    df, err, source = get_binance_data(symbol, limit=needed, interval=tf)
                    if df is None:
                        fetch_errors.append(f"**{symbol} ({tf})**: {err}")
                        continue
                    if len(df) < needed:
                        continue

                    if source == "spot" and not source_note_shown:
                        st.caption("ℹ️ Futures API is server se block hai — Binance ke public **spot** data se signals chal rahe hain.")
                        source_note_shown = True

                    is_forming_candle_used = not wait_candle_close
                    closed = df.reset_index(drop=True) if wait_candle_close is False else df.iloc[:-1].reset_index(drop=True)
                    closed = add_all_indicators(closed, ema_length=ema_length)
                    raw_buy, raw_sell = generate_signals(closed, use_ema, use_vwap, use_adx, use_vol, use_fvg, use_bos, use_ml, use_ref_candle)

                    sig_type = None
                    if bool(raw_buy.iloc[-1]):
                        sig_type = "BUY"
                    elif bool(raw_sell.iloc[-1]):
                        sig_type = "SELL"
                    if sig_type is None:
                        continue

                    signals_found = True
                    row = closed.iloc[-1]
                    entry_price = float(row['Close'])
                    entry_time = row['Time'].strftime("%d %b, %I:%M %p IST")
                    repaint_note = ("<p style='color:#facc15;font-size:12px;margin:4px 0 0;'>⚠️ Yeh abhi ban rahi candle par hai — candle close hone tak price/signal repaint (badal) sakta hai.</p>"
                                     if is_forming_candle_used else "")

                    target, sl = calc_levels(entry_price, sig_type, target_pct, sl_pct)
                    notional = capital * leverage
                    profit_amt = notional * (target_pct / 100)
                    loss_amt = notional * (sl_pct / 100)
                    rr_ratio = round(target_pct / sl_pct, 2)

                    card_class = "buy-card" if sig_type == "BUY" else "sell-card"
                    emoji = "🟢" if sig_type == "BUY" else "🔴"

                    st.markdown(f"""
                    <div class="signal-card {card_class}">
                        <h3>{emoji} {sig_type} • {symbol} <span style="font-size:14px;color:#94a3b8;">({tf})</span></h3>
                        {repaint_note}
                        <div class="signal-row">
                            <div class="metric-box"><div class="metric-label">Entry Price</div>
                                <div class="metric-value">${entry_price:.4f}</div></div>
                            <div class="metric-box"><div class="metric-label">Entry Time</div>
                                <div class="metric-value">{entry_time}</div></div>
                            <div class="metric-box"><div class="metric-label">Leverage</div>
                                <div class="metric-value">{leverage}x</div></div>
                        </div>
                        <div class="signal-row">
                            <div class="metric-box"><div class="metric-label">🎯 Target</div>
                                <div class="metric-value profit">${target:.4f}</div></div>
                            <div class="metric-box"><div class="metric-label">🛑 SL</div>
                                <div class="metric-value loss">${sl:.4f}</div></div>
                            <div class="metric-box"><div class="metric-label">Risk:Reward</div>
                                <div class="metric-value">1 : {rr_ratio}</div></div>
                        </div>
                        <div class="signal-row">
                            <div class="metric-box"><div class="metric-label">AlphaTrend</div>
                                <div class="metric-value">${row['AlphaTrend']:.4f}</div></div>
                            <div class="metric-box"><div class="metric-label">EMA{ema_length}</div>
                                <div class="metric-value">${row['EMA']:.4f}</div></div>
                            <div class="metric-box"><div class="metric-label">VWAP</div>
                                <div class="metric-value">${row['VWAP']:.4f}</div></div>
                            <div class="metric-box"><div class="metric-label">ADX</div>
                                <div class="metric-value">{row['ADX']:.1f}</div></div>
                            <div class="metric-box"><div class="metric-label">ML Confidence</div>
                                <div class="metric-value">{row['ML_Conf']:.0f}%</div></div>
                            {"<div class='metric-box'><div class='metric-label'>Ref High/Low</div><div class='metric-value'>$" + format(row['RefHigh'], '.4f') + " / $" + format(row['RefLow'], '.4f') + "</div></div>" if use_ref_candle else ""}
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
                st.info("**Abhi koi signal nahi mila.** Ya to trend/filters align nahi ho rahe, ya market quiet hai.")

        st.caption(f"🕒 Last checked: {pd.Timestamp.now(tz=IST).strftime('%I:%M:%S %p IST')}")
        if auto_refresh:
            time.sleep(30)
            st.rerun()
    else:
        st.write("**Button dabakar live signals dekhein** — AlphaTrend + selected filters align hone par entry, target, SL, EMA/VWAP/ADX/ML values aur leverage ke saath profit/nuksaan (₹) dikhega.")

    st.caption("Engine: AlphaTrend (core) + EMA/VWAP/ADX/Volume/FVG/BOS/Ref-Candle/ML-KNN filters (Pine Script se port kiya gaya). Default: FVG OFF, baaki sab ON — har filter alag se ON/OFF kar sakte ho. Target/SL adjustable hain, single-trade lock nahi hai. Fees/slippage/funding shaamil nahi.")

# =====================================================================
# TAB 2: BACKTEST
# =====================================================================
with tab_backtest:
    st.markdown("#### Historical data par AlphaTrend + Filters test karo")
    b1, b2, b3 = st.columns(3)
    with b1:
        bt_symbol = st.selectbox("Symbol", SYMBOLS, index=0)
        bt_interval = st.selectbox("Candle Interval", ["1m", "3m", "5m", "15m", "30m", "1h"], index=0)
    with b2:
        bt_candles = st.slider("Kitne Candles Test Karein", 200, 1000, 500, step=50)
        bt_ema_length = st.number_input("EMA Length", value=9, step=1, min_value=2, key="bt_ema_len")
    with b3:
        bt_target_pct = st.number_input("Target %", value=1.0, step=0.1, min_value=0.1, key="bt_tp")
        bt_sl_pct = st.number_input("Stop-Loss %", value=0.5, step=0.1, min_value=0.1, key="bt_sl")

    b4, b5 = st.columns(2)
    with b4:
        bt_capital = st.number_input("Har Trade Ka Position Size / Margin (₹)", value=10000, step=1000, min_value=100, key="bt_cap")
    with b5:
        bt_leverage = st.number_input("Leverage (x)", value=10, step=1, min_value=1, max_value=125, key="bt_lev")

    bt_use_ema, bt_use_vwap, bt_use_adx, bt_use_vol, bt_use_fvg, bt_use_bos, bt_use_ml, bt_use_ref_candle = filter_toggle_row("bt")

    max_hold = st.slider("Max Holding Candles (target/SL na mile to trade band ho jaayega)", 10, 200, 60)

    if bt_leverage > 20:
        st.warning(f"⚠️ {bt_leverage}x leverage par ek ~{round(100/bt_leverage,1)}% adverse price move liquidation kar sakta hai.")

    if st.button("▶️ Backtest Chalao", type="primary", use_container_width=True):
        with st.spinner(f"{bt_symbol} ka backtest chal raha hai..."):
            needed = min(bt_candles + 200, 1500)  # +buffer so all indicators (esp. ML) have warmup history
            df, err, source = get_binance_data(bt_symbol, limit=needed, interval=bt_interval)

            if df is None:
                st.error(f"Data fetch nahi ho paaya:\n\n{err}")
            elif len(df) < 100:
                st.error("Bahut kam candles mile — 'Kitne Candles Test Karein' ki value badhayein ya interval change karein.")
            else:
                if source == "spot":
                    st.caption("ℹ️ Futures API is server se block hai — Binance ke public **spot** data se backtest chal raha hai.")

                closed = df.iloc[:-1].reset_index(drop=True)
                closed = add_all_indicators(closed, ema_length=bt_ema_length)
                raw_buy, raw_sell = generate_signals(closed, bt_use_ema, bt_use_vwap, bt_use_adx,
                                                      bt_use_vol, bt_use_fvg, bt_use_bos, bt_use_ml, bt_use_ref_candle)

                signal_positions = []
                for i in range(len(closed)):
                    if bool(raw_buy.iloc[i]):
                        signal_positions.append((i, "BUY"))
                    elif bool(raw_sell.iloc[i]):
                        signal_positions.append((i, "SELL"))

                trades = []
                for entry_pos, sig_type in signal_positions:
                    if entry_pos >= len(closed) - 1:
                        continue
                    entry_price = float(closed['Close'].iloc[entry_pos])
                    entry_time = closed['Time'].iloc[entry_pos]
                    target, sl = calc_levels(entry_price, sig_type, bt_target_pct, bt_sl_pct)

                    outcome, exit_time, bars_held = "OPEN", None, 0
                    for j in range(entry_pos + 1, min(entry_pos + 1 + max_hold, len(closed))):
                        hi, lo = closed['High'].iloc[j], closed['Low'].iloc[j]
                        bars_held = j - entry_pos
                        if sig_type == "BUY":
                            hit_target, hit_sl = hi >= target, lo <= sl
                        else:
                            hit_target, hit_sl = lo <= target, hi >= sl
                        if hit_target and hit_sl:
                            outcome, exit_time = "LOSS", closed['Time'].iloc[j]  # conservative: SL first
                            break
                        elif hit_target:
                            outcome, exit_time = "WIN", closed['Time'].iloc[j]
                            break
                        elif hit_sl:
                            outcome, exit_time = "LOSS", closed['Time'].iloc[j]
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
                    st.info("Is period mein koi valid signal nahi mila — filters try relax karein ya candles badhayein.")
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

                    active_filters = []
                    for flag, name in [(bt_use_ema, "EMA"), (bt_use_vwap, "VWAP"), (bt_use_adx, "ADX"),
                                        (bt_use_vol, "Volume"), (bt_use_fvg, "FVG"), (bt_use_bos, "BOS"),
                                        (bt_use_ml, "ML-KNN"), (bt_use_ref_candle, "Ref Candle")]:
                        if flag:
                            active_filters.append(name)
                    filt_txt = ", ".join(active_filters) if active_filters else "koi filter nahi (sirf AlphaTrend)"
                    st.caption(f"Note: {max_hold} se zyada candles tak target/SL na milne par trade 'OPEN' maani jaati hai aur stats mein include nahi hoti. Active filters: {filt_txt}. P&L {bt_leverage}x leverage ke saath calculate kiya gaya. Fees/slippage/funding shaamil nahi hain.")
    else:
        st.write("Settings choose karke **Backtest Chalao** dabayein — AlphaTrend + selected filters ka win rate, total P&L aur equity curve dikhega.")
