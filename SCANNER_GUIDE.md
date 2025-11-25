# M7 Background Scanner

## 🎯 Purpose
A lightweight background service that monitors M7 stocks and ETFs in real-time, automatically sending Telegram alerts when significant RSI conditions are detected.

## 🚀 How It Works

### Architecture
- **dashboard.py** (👀 Eyes): Visual interface for manual analysis and chart review
- **scanner.py** (👂 Ears): Background monitoring engine that runs 24/7
- **main.py** (📅 Scheduler): Scheduled daily/weekly reports

### Scanner Features
1. **Real-time Monitoring**: Checks all tickers every 5 minutes
2. **Smart Alerts**: 
   - RSI < 30 → Oversold (Potential Buy) 🟢
   - RSI > 75 → Overbought (Potential Sell) 🔴
3. **Cooldown System**: Prevents spam (1 hour between same ticker alerts)
4. **Lightweight**: Uses <20MB RAM, minimal CPU

## 📋 Usage

### Starting the Scanner

**Option 1: Run in Terminal** (Recommended)
```bash
python scanner.py
```
Keep the terminal minimized - it will run in the background.

**Option 2: Run as Windows Service** (Advanced)
Use NSSM (Non-Sucking Service Manager) to run as a Windows service that auto-starts with your PC.

### Stopping the Scanner
Press `Ctrl+C` in the terminal window.

## ⚙️ Configuration

Edit `scanner.py` to customize:

```python
CHECK_INTERVAL = 300  # Check every 5 minutes
COOLDOWN_PERIOD = 3600  # 1 hour between duplicate alerts

# Alert conditions (modify as needed)
if rsi < 30:  # Oversold threshold
    condition_met = True
elif rsi > 75:  # Overbought threshold
    condition_met = True
```

## 📱 Alert Format

```
🚨 M7 Auto Scanner Alert

🎯 Ticker: NVDA
💵 Price: $180.50
📊 RSI: 28.3

🔥 Signal: 🟢 Oversold (RSI < 30) - Potential Buy Signal

⏰ Detected at 2025-11-22 18:10:00
```

## 🔧 Troubleshooting

### Scanner won't start
- Check `.env` file has `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`
- Verify Python packages installed: `pip install yfinance pandas requests python-dotenv`

### Not receiving alerts
- Test Telegram connection: `python test_telegram.py`
- Check scanner logs in terminal
- Verify alert conditions are being met

### Too many/few alerts
- Adjust `COOLDOWN_PERIOD` (increase to get fewer alerts)
- Modify RSI thresholds (< 30 and > 75)

## 💡 Pro Tips

1. **Run on Startup**: Add `scanner.py` to Windows Startup folder or use Task Scheduler
2. **Multiple Monitors**: Keep scanner terminal on second monitor
3. **Combo Strategy**: Use scanner for alerts + dashboard for detailed analysis
4. **Custom Conditions**: Modify alert logic to include MACD, volume, etc.

## 📊 Resource Usage
- CPU: ~1% average
- RAM: ~20MB
- Network: Minimal (API calls every 5 min)
- Disk: No writes (logs to console only)

## 🎯 Recommended Workflow

1. **Morning**: Check dashboard for market overview
2. **During Day**: Scanner runs in background, sends alerts
3. **Alert Received**: Open dashboard to analyze the specific stock
4. **Evening**: Review scanner logs for pattern analysis
