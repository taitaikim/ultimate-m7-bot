# 🚀 M7 Bot Dashboard

**Real-time Signal Monitoring System for Magnificent 7 Stocks**

A sophisticated trading signal analysis platform that combines 5-layer filtering with cloud-based data storage and real-time visualization.

![M7 Bot Dashboard](https://img.shields.io/badge/Status-Production-green) ![Python](https://img.shields.io/badge/Python-3.9+-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)

---

## 📋 Overview

M7 Bot Dashboard is a SaaS-ready platform for analyzing and monitoring trading signals for the Magnificent 7 stocks (NVDA, TSLA, META, AMZN, GOOGL, AAPL, MSFT). The system employs a sophisticated 5-layer filtering mechanism to identify high-probability trading opportunities.

### Key Features

- **5-Layer Filter System**: Macroeconomic, Chart Technical, News Sentiment, Options Data, Support/Resistance
- **Cloud Database**: Supabase integration for persistent signal storage
- **Real-time Dashboard**: Interactive Streamlit interface with live metrics
- **Automated Execution**: GitHub Actions for daily signal generation
- **Telegram Notifications**: Instant alerts for strong buy signals

---

## 🏗️ Architecture

```
M7 Bot/
├── dashboard.py              # Streamlit web interface
├── main.py                   # Core signal analysis engine
├── verify_data.py           # Database verification utility
│
├── m7_cloud/                # Cloud integration module
│   ├── __init__.py
│   └── db_manager.py        # Supabase database manager
│
├── m7_core/                 # Technical analysis module
│   ├── __init__.py
│   └── filters.py           # Support/Resistance filter
│
├── .github/workflows/       # CI/CD automation
│   └── daily_bot.yml        # Daily signal generation
│
├── requirements.txt         # Python dependencies
├── config.json             # Telegram configuration
└── .env                    # Environment variables (not in repo)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Supabase account (free tier available)
- Telegram Bot Token (optional, for notifications)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/m7-bot-dashboard.git
   cd m7-bot-dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_key
   ```

4. **Set up Telegram (Optional)**
   
   Create `config.json`:
   ```json
   {
       "telegram": {
           "bot_token": "your_bot_token",
           "chat_id": "your_chat_id"
       }
   }
   ```

### Running the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard will open automatically in your browser at `http://localhost:8501`

### Running Signal Analysis

```bash
python main.py
```

This will analyze M7 stocks and save signals to Supabase.

---

## 📊 Dashboard Features

### 1. Summary Metrics
- **Total Signals**: Cumulative count of all generated signals
- **Strong Buy Signals**: Number and percentage of high-confidence signals
- **Analyzed Stocks**: Count of M7 stocks currently tracked
- **Latest Signal**: Time since last signal generation

### 2. Filter Pass Rates
Visual representation of how many signals pass each of the 5 filters:
- 거시경제 (Macroeconomic)
- 차트 (Chart Technical)
- 뉴스 (News Sentiment)
- 옵션 (Options Data)
- 지지선 (Support/Resistance)

### 3. Recent Stocks
Interactive buttons showing recently analyzed stocks with signal counts

### 4. Signal History Table
- Sortable and filterable data table
- Export to CSV functionality
- Detailed filter results for each signal

---

## 🔍 5-Layer Filter System

### Layer 1: Macroeconomic Filter
- **QQQ Trend**: Checks if QQQ is above 120-day moving average
- **Interest Rates**: Monitors 10-Year Treasury yield for spikes
- **Purpose**: Prevents trading in unfavorable market conditions

### Layer 2: Chart Technical Filter
- **RSI Analysis**: Group-specific thresholds (25/30/35 for high/medium/low volatility)
- **Golden Cross**: Validates MA20 > MA60
- **Purpose**: Identifies oversold conditions with bullish momentum

### Layer 3: News Sentiment Filter
- **VADER Analysis**: Analyzes top 3 recent news headlines
- **Threshold**: Blocks signals with sentiment ≤ -0.5
- **Purpose**: Avoids stocks with negative news catalysts

### Layer 4: Options Data Filter ⭐
- **IV Rank**: Must be ≤ 30% (low implied volatility)
- **Unusual Activity**: Detects bullish options flow
- **P/C Ratio**: Analyzes put/call ratio for sentiment
- **Purpose**: Confirms institutional bullish positioning

### Layer 5: Support/Resistance Filter ⭐
- **Scipy Analysis**: Uses local extrema detection
- **Proximity Check**: Current price within +3% of nearest support
- **Purpose**: Ensures favorable risk/reward entry points

---

## 🔧 Configuration

### Environment Variables

Create `.env` file with:
```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Telegram Configuration
TELEGRAM_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### Streamlit Secrets (for Cloud Deployment)

Create `.streamlit/secrets.toml`:
```toml
[general]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
TELEGRAM_TOKEN = "your-bot-token"
TELEGRAM_CHAT_ID = "your-chat-id"
```

---

## 🤖 Automated Execution

### GitHub Actions

The bot runs automatically via GitHub Actions every weekday at 23:30 KST (after US market close).

**Workflow**: `.github/workflows/daily_bot.yml`

To enable:
1. Push code to GitHub
2. Add repository secrets:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `TELEGRAM_TOKEN` (optional)
   - `TELEGRAM_CHAT_ID` (optional)
3. Enable GitHub Actions in repository settings

---

## 📱 Deployment Options

### Streamlit Cloud (Recommended - Free)

1. Push code to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Add secrets in Streamlit dashboard
5. Deploy!

### Heroku

```bash
# Create Procfile
echo "web: streamlit run dashboard.py --server.port=$PORT" > Procfile

# Deploy
heroku create m7-bot-dashboard
git push heroku main
```

### Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "dashboard.py"]
```

---

## 🛠️ Development

### Project Structure

- **dashboard.py**: Streamlit web interface with caching and error handling
- **main.py**: Core signal generation logic with 5-layer filtering
- **m7_cloud/**: Supabase integration and database operations
- **m7_core/**: Technical analysis tools (support/resistance, volume profile)
- **verify_data.py**: Utility to verify database connectivity

### Adding New Features

1. Create feature branch
2. Implement changes
3. Test locally with `streamlit run dashboard.py`
4. Update documentation
5. Submit pull request

---

## 📈 Usage Examples

### Verify Database Connection

```bash
python verify_data.py
```

### Generate Signals Manually

```bash
python main.py
```

### Run Dashboard Locally

```bash
streamlit run dashboard.py
```

### Export Signal Data

Use the "📥 CSV 다운로드" button in the dashboard to export filtered signals.

---

## 🔒 Security

- **Never commit** `.env` or `config.json` files
- Use environment variables for all sensitive data
- Rotate API keys regularly
- Use Supabase Row Level Security (RLS) for production

---

## 🐛 Troubleshooting

### Dashboard won't start
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Clear Streamlit cache
streamlit cache clear
```

### Database connection fails
```bash
# Verify credentials
python verify_data.py

# Check .env file exists and has correct values
```

### No signals appearing
- Ensure GitHub Actions has run (check Actions tab)
- Verify Supabase table `m7_signals` exists
- Check filter criteria aren't too restrictive

---

## 📊 Performance

- **Data Caching**: 5-minute TTL for dashboard queries
- **Lazy Loading**: Signals loaded on-demand
- **Optimized Queries**: Supabase indexes on `created_at` and `ticker`
- **Response Time**: < 2 seconds for typical dashboard load

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- **yfinance**: Financial data API
- **Streamlit**: Web framework
- **Supabase**: Cloud database
- **VADER**: Sentiment analysis
- **Scipy**: Technical analysis

---

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review troubleshooting section

---

## 🗺️ Roadmap

- [ ] Multi-user authentication
- [ ] Custom alert thresholds
- [ ] Historical performance charts
- [ ] Mobile app integration
- [ ] Real-time WebSocket updates
- [ ] Advanced backtesting module

---

**Built with ❤️ for algorithmic traders**

*Last Updated: 2025-11-20*
