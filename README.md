# Personal Stock Analyst Agent (Building MVP)

A personalized, AI-powered stock analysis agent that delivers **daily market briefings**, **watchlist insights**, **technical analysis**, and **news sentiment summaries** — all tailored to the individual user.
The agent collects real market data, synthesizes it using an LLM, and optionally generates an **audio briefing** for hands-free consumption.

This project is designed to evolve from a deterministic data pipeline into a true **tool-using AI agent** (e.g., with Google ADK), where LLMs make decisions about what data to fetch, how deeply to analyze movements, and how to explain them.


## To do
- technical analysis agent (done)
- fundamental analysis agent (done)
- news and sentimental analysis agent (done)
- watchlist manager agent (done)
- overall market summary agent (done)
- daily brief agent
- TTS (tested)
- question and answer agent
- root agent for orchestration

---

## 🌟 Key Features (MVP)

### 1. **Daily Market Brief**

* Automatically generates a personalized morning briefing.
* Includes index movements (S&P 500, Nasdaq, Dow), sector trends, and notable macro events.
* Delivered as clean, structured markdown that reads like a human analyst's summary.

### 2. **Personalized Watchlist Insights**

* Each user maintains custom watchlists (e.g., *Core*, *Growth*, *Speculative*).
* For each ticker:

  * Latest price and daily/weekly change
  * Volume vs. average volume
  * Highlight of biggest movers
* The agent prioritizes which tickers are worth attention.

### 3. **Technical Analysis Snapshots**

* Automatically computes:

  * 20 / 50 / 200-day moving averages
  * RSI (14)
  * Trend flags (above/below key MAs)
* Included in the daily brief when technical signals matter.

### 4. **News & Sentiment Monitoring**

* Pulls recent headlines for each ticker.
* Summarizes sentiment trends (positive / negative / mixed).
* Identifies themes that may be influencing stock movements.

### 5. **LLM-Generated Natural Language Summary**

* Converts structured market data into a narrative explanation.
* Tailored by user preferences (concise vs detailed).
* Avoids financial advice; focuses on explanations and context.

### 6. **Text-to-Speech Daily Report**

* Converts the daily briefing into spoken audio (e.g., MP3).
* Perfect for listening in the morning commute or while multitasking.
