import yfinance as yf
import pandas as pd
import pandas_ta as ta

# -----------------------------
# NSE 50 STOCK LIST
# -----------------------------
NSE50 = [
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
    "TITAN.NS","ULTRACEMCO.NS","UPL.NS","WIPRO.NS"
]

results = []

# -----------------------------
# MAIN LOOP
# -----------------------------
for stock in NSE50:
    try:
        # Download daily data
        df = yf.download(stock, period="18mo", interval="1d", progress=False)

        if df.empty:
            continue

        # Handle Yahoo multi-index columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)

        # -----------------------------
        # CMP (latest daily close)
        # -----------------------------
        cmp_price = round(df["Close"].iloc[-1], 2)

        # -----------------------------
        # Weekly candles
        # -----------------------------
        dfw = df.resample("W").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()

        if len(dfw) < 30:
            continue

        # -----------------------------
        # Indicators (weekly)
        # -----------------------------
        dfw["RSI"] = ta.rsi(dfw["Close"], 14)
        macd = ta.macd(dfw["Close"])
        dfw = dfw.join(macd)

        last = dfw.iloc[-1]
        prev = dfw.iloc[-2]

        # -----------------------------
        # Signal Logic
        # -----------------------------
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

        # -----------------------------
        # Store Results
        # -----------------------------
        #print(stock, "CMP:", cmp_price)

        results.append({
            "Stock": stock.replace(".NS",""),
            "Weekly Close": round(last["Close"], 2),
            "CMP": cmp_price,
            "Drift %": round((cmp_price - last["Close"]) / last["Close"] * 100, 2),
            "RSI": round(last["RSI"], 2),
            "MACD": round(last["MACD_12_26_9"], 2),
            "MACD Histogram": round(last["MACDh_12_26_9"], 2),
            "Signal": signal
        })

    except Exception as e:
        print(stock, "FAILED:", e)

# -----------------------------
# CREATE DATAFRAME
# -----------------------------
df_results = pd.DataFrame(results)

# Split into sheets
df_confirmed = df_results[df_results["Signal"] == "Confirmed Momentum"]
df_early = df_results[df_results["Signal"] == "Early Momentum"]
df_none = df_results[df_results["Signal"] == "No Signal"]

# -----------------------------
# EXPORT TO EXCEL
# -----------------------------
with pd.ExcelWriter(
    "NSE50_Weekly_Momentum_Screener.xlsx",
    engine="openpyxl"
) as writer:
    df_confirmed.to_excel(writer, sheet_name="Confirmed Momentum", index=False)
    df_early.to_excel(writer, sheet_name="Early Momentum", index=False)
    df_none.to_excel(writer, sheet_name="No Signal", index=False)

print("Scan complete. Excel file created with 3 sheets.")
