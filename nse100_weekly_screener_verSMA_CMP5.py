import yfinance as yf
import pandas as pd
import pandas_ta as ta
import sys

# =========================================================
# STOCK UNIVERSE (NIFTY 50 + NEXT 50 + NSE 101–150)
# =========================================================
STOCKS = [
    # ---- NIFTY 50 ----
    "ADANIENT.NS","ADANIPORTS.NS","APOLLOHOSP.NS","ASIANPAINT.NS",
    "AXISBANK.NS","BAJAJ-AUTO.NS","BAJFINANCE.NS","BAJAJFINSV.NS",
    "BPCL.NS","BHARTIARTL.NS","BRITANNIA.NS","CIPLA.NS",
    "COALINDIA.NS","DIVISLAB.NS","DRREDDY.NS","EICHERMOT.NS",
    "GRASIM.NS","HCLTECH.NS","HDFCBANK.NS","HDFCLIFE.NS",
    "HEROMOTOCO.NS","HINDALCO.NS","HINDUNILVR.NS","ICICIBANK.NS",
    "ITC.NS","INDUSINDBK.NS","INFY.NS","JSWSTEEL.NS",
    "KOTAKBANK.NS","LT.NS","M&M.NS","MARUTI.NS",
    "NESTLEIND.NS","NTPC.NS","ONGC.NS","POWERGRID.NS",
    "RELIANCE.NS","SBILIFE.NS","SBIN.NS","SUNPHARMA.NS",
    "TCS.NS","TATAMOTORS.NS","TATASTEEL.NS","TECHM.NS",
    "TITAN.NS","ULTRACEMCO.NS","UPL.NS","WIPRO.NS",

    # ---- NIFTY NEXT 50 ----
    "ABB.NS","ADANIENSOL.NS","ADANIGREEN.NS","ADANIPOWER.NS",
    "ATGL.NS","AUROPHARMA.NS","BAJAJHLDNG.NS","BANKBARODA.NS"
    "BERGEPAINT.NS","BOSCHLTD.NS","CANBK.NS","CHOLAFIN.NS",
    "COLPAL.NS","CONCOR.NS","DABUR.NS","DLF.NS",
    "GODREJCP.NS","HAVELLS.NS","ICICIGI.NS","ICICIPRULI.NS",
    "IOC.NS","IRCTC.NS","JINDALSTEL.NS","LTTS.NS",
    "LUPIN.NS","MARICO.NS","MUTHOOTFIN.NS","NAUKRI.NS",
    "NMDC.NS","OFSS.NS","PIDILITIND.NS","PFC.NS",
    "PGHH.NS","PNB.NS","RECLTD.NS","SHREECEM.NS",
    "SIEMENS.NS","SRF.NS","TORNTPHARM.NS","TVSMOTOR.NS",
    "UBL.NS","VEDL.NS","VOLTAS.NS","ZEEL.NS","ZYDUSLIFE.NS"
]

# =========================================================
# TRADE LEVELS
# =========================================================
def trade_levels(weekly_close, signal):
    if signal == "Confirmed Momentum":
        return {
            "Ideal Buy Low": round(weekly_close * 0.99, 2),
            "Ideal Buy High": round(weekly_close * 1.02, 2),
            "Stop Loss": round(weekly_close * 0.96, 2),
            "Target 1": round(weekly_close * 1.07, 2),
            "Target 2": round(weekly_close * 1.14, 2),
        }
    elif signal == "Early Momentum":
        return {
            "Ideal Buy Low": round(weekly_close * 0.98, 2),
            "Ideal Buy High": round(weekly_close * 1.01, 2),
            "Stop Loss": round(weekly_close * 0.95, 2),
            "Target 1": round(weekly_close * 1.05, 2),
            "Target 2": round(weekly_close * 1.10, 2),
        }
    else:
        return {
            "Ideal Buy Low": None,
            "Ideal Buy High": None,
            "Stop Loss": None,
            "Target 1": None,
            "Target 2": None,
        }

# =========================================================
# MAIN SCAN
# =========================================================
results = []

for stock in STOCKS:
    try:
        df = yf.download(
            stock,
            period="24mo",
            interval="1d",
            progress=False
        )

        if df.empty:
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)

        # CMP = last completed daily close
        cmp_price = round(df["Close"].dropna().iloc[-1], 2)

        # Weekly aggregation (Friday close)
        dfw = df.resample("W-FRI").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()

        # Need enough weekly data
        if len(dfw) < 30:
            continue

        # ================= INDICATORS =================
        dfw["RSI"] = ta.rsi(dfw["Close"], 14)

        macd = ta.macd(dfw["Close"])
        dfw = dfw.join(macd)

        # 10-week SMA (GUARDED)
        dfw["SMA_10W"] = dfw["Close"].rolling(10, min_periods=10).mean()

        # 20-week avg volume
        dfw["AvgVol_20W"] = dfw["Volume"].rolling(20, min_periods=20).mean()

        last = dfw.iloc[-1]
        prev = dfw.iloc[-2]

        # Skip if SMA not available
        if pd.isna(last["SMA_10W"]) or pd.isna(last["AvgVol_20W"]):
            continue

        # ================= CALCULATIONS =================
        weekly_close_date = last.name.strftime("%d-%m-%Y")

        drift = round((cmp_price - last["Close"]) / last["Close"] * 100, 2)

        price_vs_sma = round(
            (last["Close"] - last["SMA_10W"]) / last["SMA_10W"] * 100, 2
        )

        rvol = round(last["Volume"] / last["AvgVol_20W"], 2)

        if rvol >= 1.5:
            volume_signal = "Strong Volume"
        elif rvol >= 1.0:
            volume_signal = "Normal Volume"
        else:
            volume_signal = "Weak Volume"

        # ================= SIGNAL LOGIC =================
        signal = "No Signal"

        if (
            last["RSI"] > 55 and
            last["MACD_12_26_9"] > 0 and
            last["MACDh_12_26_9"] > 0
        ):
            signal = "Confirmed Momentum"

        elif (
            last["RSI"] > 45 and
            last["MACDh_12_26_9"] > prev["MACDh_12_26_9"]
        ):
            signal = "Early Momentum"

        levels = trade_levels(last["Close"], signal)

        results.append({
            "Stock": stock.replace(".NS",""),
            "Weekly Close Date": weekly_close_date,
            "Weekly Close": round(last["Close"], 2),
            "CMP": cmp_price,
            "Drift %": drift,
            "RSI": round(last["RSI"], 2),
            "MACD": round(last["MACD_12_26_9"], 2),
            "MACD Histogram": round(last["MACDh_12_26_9"], 2),
            "SMA 10W": round(last["SMA_10W"], 2),
            "Price vs SMA 10W %": price_vs_sma,
            "Weekly Volume": int(last["Volume"]),
            "Avg Weekly Volume (20W)": int(last["AvgVol_20W"]),
            "RVOL": rvol,
            "Volume Signal": volume_signal,
            "Signal": signal,
            **levels
        })

    except Exception as e:
        print(stock, "FAILED:", e)

# =========================================================
# OUTPUT
# =========================================================
df_results = pd.DataFrame(results)

if df_results.empty:
    print("No stocks qualified this week.")
    sys.exit()

df_confirmed = df_results[df_results["Signal"] == "Confirmed Momentum"]
df_early = df_results[df_results["Signal"] == "Early Momentum"]
df_none = df_results[df_results["Signal"] == "No Signal"]

with pd.ExcelWriter("NSE_Weekly_Momentum_Screener.xlsx", engine="openpyxl") as writer:
    df_confirmed.to_excel(writer, sheet_name="Confirmed Momentum", index=False)
    df_early.to_excel(writer, sheet_name="Early Momentum", index=False)
    df_none.to_excel(writer, sheet_name="No Signal", index=False)

print("Scan complete. NSE_Weekly_Momentum_Screener.xlsx generated.")
