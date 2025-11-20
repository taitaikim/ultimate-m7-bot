import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# Set paths
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'stock_data.csv')

# Define tickers
tickers = ['AAPL', 'TSLA', 'NVDA']

# Calculate date range (1 year)
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

print(f"Fetching data for {tickers} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")

# Fetch data
# auto_adjust=False ensures we get Open, High, Low, Close (not just Adj Close)
# group_by='ticker' groups data by ticker
data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', auto_adjust=False)

# The data is currently a MultiIndex DataFrame. 
# To make it a clean CSV for Excel, we can stack it to have a 'Ticker' column
# or just save it as is. 
# Let's try to make it a long-format DataFrame which is often easier to analyze in Excel with Pivot Tables.

data_list = []
for ticker in tickers:
    df = data[ticker].copy()
    df['Ticker'] = ticker
    data_list.append(df)

# Concatenate all tickers
final_df = pd.concat(data_list)

# Reset index to make Date a column
final_df.reset_index(inplace=True)

# Reorder columns
cols = ['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']
# Filter only existing columns in case some are missing (unlikely with yfinance standard data)
existing_cols = [c for c in cols if c in final_df.columns]
final_df = final_df[existing_cols]

# Save to CSV
final_df.to_csv(csv_path, index=False)

print(f"Successfully saved stock data to {csv_path}")
print(final_df.head())
