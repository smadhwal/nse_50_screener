import yfinance as yf
import pandas as pd
import pandas_ta as ta

stock = "TCS.NS"

df = yf.download(stock, period="18mo", interval="1d", progress=False)

# Flatten columns (important)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.index = pd.to_datetime(df.index)

# Weekly candles
dfw = df.resample('W').agg({
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last',
    'Volume': 'sum'
}).dropna()

# Indicators
dfw['RSI'] = ta.rsi(dfw['Close'], 14)
macd = ta.macd(dfw['Close'])
dfw = dfw.join(macd)

# Print last 5 weeks
print(dfw[['Close','RSI','MACD_12_26_9','MACDs_12_26_9','MACDh_12_26_9']].tail())
