import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set paths
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'stock_data.csv')
output_file = os.path.join(script_dir, 'stock_graph.png')

# Read the data
df = pd.read_csv(csv_path)

# Convert Date to datetime
df['Date'] = pd.to_datetime(df['Date'])

# Set the style
sns.set_theme(style="darkgrid")

# Create the plot
plt.figure(figsize=(12, 6))

# Plot the data
sns.lineplot(data=df, x='Date', y='Close', hue='Ticker', palette='bright')

# Set title and labels
plt.title('Stock Price Trend', fontsize=16)
plt.xlabel('Date', fontsize=12)
plt.ylabel('Close Price', fontsize=12)

# Add legend
plt.legend(title='Ticker')

# Adjust layout
plt.tight_layout()

# Save the plot
plt.savefig(output_file)
plt.close()

print(f"Successfully saved stock graph to {output_file}")
