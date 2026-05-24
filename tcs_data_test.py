import yfinance as yf
import pandas as pd

stock = "TCS.NS"

df = yf.download(stock, period="18mo", interval="1d", progress=False)

# 🔑 FIX: flatten columns
df.columns = df.columns.get_level_values(0)

print("Daily rows:", len(df))
print(df.tail())

df.index = pd.to_datetime(df.index)

dfw = df.resample('W').agg({
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last',
    'Volume': 'sum'
}).dropna()

print("\nWeekly rows:", len(dfw))
print(dfw.tail())

