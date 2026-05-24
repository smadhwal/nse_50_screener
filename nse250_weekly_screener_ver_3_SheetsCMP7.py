# =========================================================
# WARNINGS (suppress non-critical only)
# =========================================================
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# =========================================================
# IMPORTS
# =========================================================
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import sys

# =========================================================
# NSE TOP ~250 STOCK UNIVERSE (LIQUID)
# =========================================================
STOCKS = [
    "ADANIENT.NS","ADANIPORTS.NS","APOLLOHOSP.NS","ASIANPAINT.NS","AXISBANK.NS",
    "BAJAJ-AUTO.NS","BAJFINANCE.NS","BAJAJFINSV.NS","BPCL.NS","BHARTIARTL.NS",
    "BRITANNIA.NS","CIPLA.NS","COALINDIA.NS","DIVISLAB.NS","DRREDDY.NS",
    "EICHERMOT.NS","GRASIM.NS","HCLTECH.NS","HDFCBANK.NS","HDFCLIFE.NS",
    "HEROMOTOCO.NS","HINDALCO.NS","HINDUNILVR.NS","ICICIBANK.NS","ITC.NS",
    "INDUSINDBK.NS","INFY.NS","JSWSTEEL.NS","KOTAKBANK.NS","LT.NS","M&M.NS",
    "MARUTI.NS","NESTLEIND.NS","NTPC.NS","ONGC.NS","POWERGRID.NS",
    "RELIANCE.NS","SBILIFE.NS","SBIN.NS","SUNPHARMA.NS","TCS.NS",
    "TMCV.NS","TMPV.NS","TATASTEEL.NS","TECHM.NS","TITAN.NS","ULTRACEMCO.NS",
    "UPL.NS","WIPRO.NS",
    "ABB.NS","ADANIENSOL.NS","ADANIPOWER.NS","AUROPHARMA.NS","BANKBARODA.NS",
    "BOSCHLTD.NS","CANBK.NS","CHOLAFIN.NS","GODREJCP.NS","HAVELLS.NS",
    "ICICIGI.NS","ICICIPRULI.NS","IOC.NS","IRCTC.NS","LTTS.NS",
    "LUPIN.NS","MARICO.NS","MUTHOOTFIN.NS","NAUKRI.NS","NMDC.NS",
    "PIDILITIND.NS","PFC.NS","PNB.NS","RECLTD.NS","SHREECEM.NS",
    "SRF.NS","TORNTPHARM.NS","TVSMOTOR.NS","UBL.NS","VEDL.NS","VOLTAS.NS",
    "ZEEL.NS","ZYDUSLIFE.NS", 
    "INDIGo.NS", "KAYNES.NS"

]

# =========================================================
# MOMENTUM SCORE FUNCTION
# =========================================================
def momentum_score(rsi, macd_hist, price_vs_sma, rvol, signal):
    score = 0

    if 60 <= rsi <= 70:
        score += 25
    elif rsi >= 55:
        score += 18
    elif rsi >= 45:
        score += 10

    if macd_hist > 20:
        score += 25
    elif macd_hist > 5:
        score += 18
    elif macd_hist > 0:
        score += 10

    if -2 <= price_vs_sma <= 2:
        score += 20
    elif 2 < price_vs_sma <= 6:
        score += 15
    elif price_vs_sma > 6:
        score += 5

    if rvol >= 1.5:
        score += 20
    elif rvol >= 1.3:
        score += 15
    elif rvol >= 1.0:
        score += 10

    if signal == "Confirmed Momentum":
        score += 10
    elif signal == "Early Momentum":
        score += 5

    return score

# =========================================================
# MAIN SCAN
# =========================================================
results = []
today = pd.Timestamp.today().normalize()

for stock in STOCKS:
    try:
        df = yf.download(stock, period="24mo", interval="1d", progress=False)
        if df.empty or len(df) < 60:
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # ---------- DAILY DVR ----------
        df["AvgVol_10D"] = df["Volume"].rolling(10).mean()
        today_row = df.iloc[-1]
        if pd.isna(today_row["AvgVol_10D"]):
            continue

        daily_volume = int(today_row["Volume"])
        dvr = round(today_row["Volume"] / today_row["AvgVol_10D"], 2)

        inst_activity = (
            "Strong Institutional Activity" if dvr >= 1.5 else
            "Moderate Institutional Activity" if dvr >= 1.2 else
            "No Institutional Activity"
        )

        cmp_price = round(today_row["Close"], 2)

        # ---------- WEEKLY ----------
        dfw = df.resample("W-FRI").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()

        if len(dfw) < 30:
            continue

        dfw["RSI"] = ta.rsi(dfw["Close"], 14)
        macd = ta.macd(dfw["Close"])
        dfw = dfw.join(macd)
        dfw["SMA_10W"] = dfw["Close"].rolling(10, min_periods=10).mean()
        dfw["AvgVol_20W"] = dfw["Volume"].rolling(20, min_periods=20).mean()

        if dfw.index[-1] >= today:
            last = dfw.iloc[-2]
            prev = dfw.iloc[-3]
        else:
            last = dfw.iloc[-1]
            prev = dfw.iloc[-2]

        if pd.isna(last["SMA_10W"]) or pd.isna(last["AvgVol_20W"]):
            continue

        weekly_close_date = pd.to_datetime(last.name).date()

        price_vs_sma = round(
            (last["Close"] - last["SMA_10W"]) / last["SMA_10W"] * 100, 2
        )

        rvol = round(last["Volume"] / last["AvgVol_20W"], 2)
        drift = round((cmp_price - last["Close"]) / last["Close"] * 100, 2)

        # ---------- TRADE LEVELS ----------
        ideal_buy_low = round(max(last["SMA_10W"] * 0.99, last["Close"] * 0.985), 2)
        ideal_buy_high = round(last["Close"] * 1.01, 2)
        stop_loss = round(min(last["SMA_10W"] * 0.97, last["Close"] * 0.96), 2)
        target_1 = round(last["Close"] * 1.05, 2)
        target_2 = round(last["Close"] * 1.10, 2)

        # ---------- SIGNAL ----------
        signal = "No Signal"
        if last["RSI"] > 55 and last["MACD_12_26_9"] > 0 and last["MACDh_12_26_9"] > 0:
            signal = "Confirmed Momentum"
        elif last["RSI"] > 45 and last["MACDh_12_26_9"] > prev["MACDh_12_26_9"]:
            signal = "Early Momentum"

        score = momentum_score(
            last["RSI"], last["MACDh_12_26_9"], price_vs_sma, rvol, signal
        )

        results.append({
            "Stock": stock.replace(".NS",""),
            "Weekly Close Date": weekly_close_date,
            "Weekly Close": round(last["Close"], 2),
            "CMP": cmp_price,
            "Drift %": drift,
            "RSI": round(last["RSI"], 2),
            "MACD Histogram": round(last["MACDh_12_26_9"], 2),
            "SMA 10W": round(last["SMA_10W"], 2),
            "Price vs SMA 10W %": price_vs_sma,
            "Weekly RVOL": rvol,
            "Daily DVR (10D)": dvr,
            "Institutional Activity": inst_activity,
            "Ideal Buy Low": ideal_buy_low,
            "Ideal Buy High": ideal_buy_high,
            "Stop Loss": stop_loss,
            "Target 1": target_1,
            "Target 2": target_2,
            "Momentum Score": score,
            "Signal": signal
        })

    except Exception as e:
        print(stock, "FAILED:", e)

# =========================================================
# OUTPUT — BUY / WAIT / AVOID
# =========================================================
df = pd.DataFrame(results)
if df.empty:
    print("No stocks qualified.")
    sys.exit()

df_buy = df[
    (df["Signal"] == "Confirmed Momentum") &
    (df["Momentum Score"] >= 70) &
    (df["Price vs SMA 10W %"].abs() <= 3)
]

df_wait = df[
    (df["Signal"].isin(["Confirmed Momentum", "Early Momentum"])) &
    (~df.index.isin(df_buy.index))
]

df_avoid = df[
    ~df.index.isin(df_buy.index) &
    ~df.index.isin(df_wait.index)
]

with pd.ExcelWriter("NSE250_Weekly_Momentum_Screener.xlsx", engine="openpyxl") as writer:
    df_buy.to_excel(writer, sheet_name="BUY", index=False)
    df_wait.to_excel(writer, sheet_name="WAIT", index=False)
    df_avoid.to_excel(writer, sheet_name="AVOID", index=False)

print("Scan complete — BUY / WAIT / AVOID sheets generated.")
