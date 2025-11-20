# 🚀 M7 Bot: The Ultimate Stock Trading Assistant
> **"Data-Driven Decisions, Automated for You."**

## 🌟 Service Overview
**M7 Bot (Cloud V2)** is a state-of-the-art automated stock analysis service designed for the "Magnificent 7" and major US indices. It combines **macroeconomic analysis**, **technical indicators**, **news sentiment**, **options flow**, and **support/resistance levels** into a single, powerful decision-making engine.

![M7 Bot Architecture](C:/Users/user/.gemini/antigravity/brain/d49acbc6-c0df-445c-95c2-62978f5e2242/service_architecture_1763647022240.png)

Unlike simple alert bots, M7 Bot filters out noise using a rigorous **5-Layer Filtering System**, ensuring that only the highest-probability signals reach you.

---

## 💎 Key Features

### 1. 🛡️ 5-Layer Filtering System (The Core Engine)
We don't just look at price. We analyze the entire market context:
1.  **Macro Filter**: Checks market health using QQQ trends and 10-Year Treasury Yields (^TNX). If the market is crashing, we stay cash.
2.  **Chart Filter**: Analyzes RSI and Golden Cross patterns to find optimal entry points.
3.  **News Filter**: Uses AI (VADER Sentiment Analysis) to screen out stocks with breaking bad news.
4.  **Options Filter**: Tracks Institutional Money Flow (Smart Money) via IV Rank and Put/Call Ratios.
5.  **Support Filter**: Ensures you buy at strong structural support levels, not in thin air.

### 2. ☁️ Cloud-Native Architecture
-   **Always On**: Runs 24/7 on the cloud (Streamlit/Heroku/Docker).
-   **Database Integrated**: All signals are logged to **Supabase** (PostgreSQL) for historical tracking and performance analysis.
-   **Secure**: Enterprise-grade security with environment variable management.

### 3. 📱 Real-Time Notifications
-   **Telegram Integration**: Get instant alerts the moment a "STRONG BUY" signal is generated.
-   **Rich Reports**: Notifications include price, RSI, IV Rank, and Support levels directly in the message.

---

## 🖥️ User Interface (Dashboard)

Our **Streamlit-based Web Dashboard** provides a command center for your trading operations.

### 📊 1. Live Market Metrics
-   **Market Status**: Instantly see if the market is "Safe", "Caution", or "Crash".
-   **Key Indices**: Real-time tracking of QQQ and TNX (Interest Rates).
-   **Filter Pass Rates**: Visual charts showing how many stocks passed each filter layer.

### 📋 2. Signal History Table
-   A sortable, searchable table of all past signals.
-   **Columns**: Time, Ticker, Signal Type, Entry Price, and detailed Filter Results.
-   **Export**: Download data as CSV for your own analysis.

### 🔍 3. Deep Dive Analysis
-   Click on any signal to see the **"Why?"** behind it.
-   View the exact values that triggered the decision (e.g., "RSI was 28.5", "News Sentiment was Positive").

---

## 🛠️ Technical Stack
-   **Core**: Python 3.9+
-   **Analysis**: Pandas, NumPy, SciPy, TA-Lib
-   **AI/NLP**: VADER Sentiment
-   **Data**: yfinance (Real-time), Supabase (Cloud DB)
-   **Frontend**: Streamlit
-   **DevOps**: Docker, GitHub Actions (CI/CD)

---

## 📈 Why M7 Bot?

| Feature | Ordinary Bots | 🚀 M7 Bot |
| :--- | :---: | :---: |
| **Market Awareness** | ❌ Ignores Crash Risks | ✅ Macro-First Approach |
| **Risk Management** | ❌ Simple Price Alerts | ✅ 5-Layer Safety Net |
| **Transparency** | ❌ "Black Box" Signals | ✅ Full Dashboard & Logs |
| **Reliability** | ❌ Prone to Crashes | ✅ Hotfix v2.1 Stability |

---

### 🚀 Ready to Trade Smarter?
*Deploy your own M7 Bot today and let data drive your success.*
