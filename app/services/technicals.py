from pathlib import Path
from datetime import date
import json
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from google import genai
from google.genai import types

TA_PROMPT="""
ROLE:
You are a Senior Technical Analyst and Market Structure Specialist focused on mid- to long-term price behavior.
You specialize in position trading and trend-following strategies, prioritizing high-probability setups and ignoring 
short-term noise.

Your analysis integrates:
- Trend structure
- Momentum confirmation
- Volume analysis
- Volatility context
- Risk-managed entry/exit planning

TASK:
Analyze the provided price chart and technical indicators to determine the medium-to-long term technical outlook, 
focusing on trend direction, momentum quality, volume behavior, volatility conditions, and actionable entry/exit zones.

INPUT:
You will receive:
- Price chart
- Pre-calculated technical metrics

Assume input data is accurate and complete.

ANALYSIS DIMENSIONS:

1. TREND ANALYSIS
   - Identify dominant trend: Uptrend / Downtrend / Sideways
   - Evaluate trend strength and structure (higher highs/lows, channel integrity, slope consistency)

2. MOMENTUM ANALYSIS
   - Assess RSI/MACD or equivalent momentum indicators
   - Determine if momentum supports trend continuation or warns of exhaustion

3. VOLUME ANALYSIS
   - Examine volume behavior relative to price movement
   - Identify accumulation/distribution characteristics
   - Confirm or weaken breakout signals

4. VOLATILITY ANALYSIS
   - Assess current volatility conditions (ATR, Bollinger Band width)
   - Determine if volatility expansion or contraction is occurring
   - Evaluate impact on risk and entry timing

5. TECHNICAL STRUCTURE
   - Key support and resistance levels
   - Major zones of demand/supply
   - Breakout or pullback setup quality

6. TRADE PLANNING (MID-LONG TERM)
   - Optimal entry zone(s)
   - Exit/target zone(s)
   - Stop-loss region
   - Risk-reward viability based on trend structure

Ignore intraday fluctuations and micro patterns. Only consider signals relevant to trends spanning weeks to months.

---

OUTPUT FORMAT (STRICT JSON):

{
  "trend": {
    "direction": "Uptrend | Downtrend | Sideways",
    "strength": "Weak | Moderate | Strong",
    "structure_comment": "Description of trend quality and integrity"
  },
  "momentum": {
    "status": "Bullish | Neutral | Bearish",
    "interpretation": "Explanation of momentum alignment with trend"
  },
  "volume": {
    "behavior": "Accumulation | Distribution | Neutral",
    "confirmation_level": "Strong | Moderate | Weak",
    "analysis": "How volume supports or contradicts price action"
  },
  "volatility": {
    "condition": "Expanding | Contracting | Stable",
    "risk_implication": "Low | Medium | High",
    "analysis": "Impact on entry timing and position sizing"
  },
  "key_levels": {
    "support": ["level1", "level2"],
    "resistance": ["level1", "level2"]
  },
  "trade_setup": {
    "entry_zone": "Preferred price range or technical condition",
    "exit_zone": "Target price range",
    "stop_loss_zone": "Protective level",
    "risk_reward_assessment": "Favorable | Neutral | Unfavorable"
  },
  "strategy_bias": {
    "recommended_action": "Accumulate | Hold | Trim | Avoid Entry",
    "time_horizon": "Mid-term | Long-term",
    "confidence_level": "Low | Medium | High"
  },
  "overall_summary": "Concise technical outlook integrating trend, momentum, volume, and volatility"
}

IMPORTANT RULES:
- Ignore short-term noise and micro timeframes
- Prioritize trend confirmation over reversal guessing
- Flag conflicting signals clearly
- Always consider volatility impact on risk
- Focus on technically rational trade planning

"""


def get_ta_indicators(df: pd.DataFrame, data_interval="day") -> dict:
    ta_indicators = {}
    print(df.head())
    for period in [20, 50, 200]:
        sma = ta.sma(close=df["Close"], length=period)
        if sma is not None:
            ta_indicators[f"SMA_{period}{data_interval}"] = float(sma[-1])
    
    rsi = ta.rsi(close=df["Close"])
    ta_indicators["RSI_14"] = float(rsi[-1])
    macd = ta.macd(close=df["Close"])
    ta_indicators["MACD_12_26_9"] = float(macd.iloc[-1, 0])
    ta_indicators["MACDh_12_26_9"] = float(macd.iloc[-1, 1])
    ta_indicators["MACDs_12_26_9"] = float(macd.iloc[-1, 2])
    bbands = ta.bbands(close=df["Close"], length=20)
    ta_indicators["BollingerBand_lower_20_2.0_2.0"] = float(bbands.iloc[-1, 0])
    ta_indicators["BollingerBand_mid_20_2.0_2.0"] = float(bbands.iloc[-1, 1])
    ta_indicators["BollingerBand_upper_20_2.0_2.0"] = float(bbands.iloc[-1, 2])
    ta_indicators[f"20-{data_interval} average volume"] = float(ta.sma(close=df["Volume"], length=20)[-1])
    ta_indicators[f"50-{data_interval} average volume"] = float(ta.sma(close=df["Volume"], length=50)[-1])
    return ta_indicators

def gather_ta_data(symbol: str) -> dict:
    symbol = symbol.upper()
    all_ta_data = {}
    ticker = yf.Ticker(symbol)
    basic_info = dict(ticker.fast_info)
    all_ta_data["Basic Info"] = basic_info
    # get technical indicators for the daily chart
    df = yf.download(symbol, period="1y", interval="1d", multi_level_index=False)
    all_ta_data["technical indicators for daily chart"] = get_ta_indicators(df, data_interval="day")
    df = yf.download(symbol, period="2y", interval="1wk", multi_level_index=False)
    all_ta_data["technical indicators for weekly chart"] = get_ta_indicators(df, data_interval="week")
    return all_ta_data

def generate_chart(ticker: str, period: str, type: str="daily"):
    """
    Use this function to generate chart for a ticker. It returns the file path of the image
    Parameters:
        ticker: ticker name of a stock
        period: length of the data to download. choose from "1y", "2y", "5y".
                Recommend "1y" for daily chart and "5y" for weekly chart
        type: choose to make daily or weekly chart.
    Return:
        return the file path of the chart image.
        It will check if it exists already. If it does, return it directly. Otherwise, generate it and return the path

    files are saved at ../data/technicals/<ticker>/
    file name format: <date>-<ticker>-<type>-chart-<period>.png    
    """
    ticker = ticker.upper()

    # check if the chart already exists
    today = date.today().isoformat()
    base_dir = Path(__file__).resolve().parents[2] / "data" / "technicals" / ticker.replace("^", "INDEX_")
    base_dir.mkdir(parents=True, exist_ok=True)
    image_path = base_dir / f"{today}-{ticker.replace("^", "INDEX_")}-{type}-chart-{period}.png"
    if image_path.exists():
        return image_path

    # --- 1. Configuration ---
    if type == "daily":
        interval = '1d'      # Data interval
    elif type == "weekly":
        interval = "1wk"
    else:
        raise TypeError(f"Does not support chart type: {type}")
    VP_BINS = 50         # Number of price bins for Volume Profile
    VP_LOOKBACK = 252    # Approx 1 trading year

    # --- 2. Fetch Data ---
    # print(f"Fetching data for {ticker}...")
    try:
        df = yf.download(ticker, period=period, interval=interval, multi_level_index=False)
    except:
        print(f"Could not download data for ticker: {ticker}")

    # --- 3. Calculate Indicators ---
    # Simple Moving Averages
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    df['SMA_50'] = ta.sma(df['Close'], length=50)
    df['SMA_200'] = ta.sma(df['Close'], length=200)

    # Bollinger Bands
    bbands = ta.bbands(df['Close'], length=20, std=2)

    # NOTE: confirm these column names with your pandas_ta version:
    df['BB_Lower'] = bbands['BBL_20_2.0_2.0']
    df['BB_Mid']   = bbands['BBM_20_2.0_2.0']
    df['BB_Upper'] = bbands['BBU_20_2.0_2.0']

    # RSI
    df['RSI'] = ta.rsi(df['Close'], length=14)

    # MACD
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_Hist'] = macd['MACDh_12_26_9']
    df['MACD_Signal'] = macd['MACDs_12_26_9']

    # Volume Profile (Visible Range)
    vp_data = df.tail(VP_LOOKBACK)
    price_bins = np.linspace(vp_data['Low'].min(), vp_data['High'].max(), VP_BINS)
    hist_values, bin_edges = np.histogram(vp_data['Close'], bins=price_bins, weights=vp_data['Volume'])
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    max_vol = hist_values.max()

    # --- 4. Build the Plot ---

    #   Use 4 rows now:
    #   Row 1: Price + Volume Profile
    #   Row 2: Daily Volume
    #   Row 3: RSI
    #   Row 4: MACD
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.1, 0.2, 0.2],
        subplot_titles=(
            f'{ticker} Price & Volume Profile - {type} chart',
            'Volume',
            'RSI (14)',
            'MACD (12, 26, 9)'
        )
    )

    # --- Main Price Chart (Row 1) ---
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
        showlegend=False
    ), row=1, col=1)

    # SMAs
    fig.add_trace(go.Scatter(
        x=df.index, y=df['SMA_20'],
        line=dict(color='#ffeb3b', width=1.5),
        name='SMA 20'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['SMA_50'],
        line=dict(color='#2196f3', width=1.5),
        name='SMA 50'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['SMA_200'],
        line=dict(color='#9c27b0', width=1.5),
        name='SMA 200'
    ), row=1, col=1)

    # Bollinger Bands
    fig.add_trace(go.Scatter(
        x=df.index, y=df['BB_Upper'],
        line=dict(color='rgba(0, 188, 212, 0.6)', width=1),
        name='BB Upper',
        legendgroup='BB',
        showlegend=False
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['BB_Lower'],
        fill='tonexty',
        fillcolor='rgba(0, 188, 212, 0.08)',
        line=dict(color='rgba(0, 188, 212, 0.6)', width=1),
        legendgroup='BB',
        name='Bollinger Bands'
    ), row=1, col=1)

    # --- Volume Profile (Row 1 - Right Side Overlay) ---

    # >>> FIX: use a dedicated extra x-axis (xaxis5) for the volume profile,
    # so we don't steal xaxis2/xaxis3 that belong to other rows.
    fig.add_trace(go.Bar(
        y=bin_centers,
        x=hist_values,
        orientation='h',
        marker=dict(color='rgba(255, 255, 255, 0.3)', line=dict(width=0)),
        xaxis='x5',              # <<< use x5, not x2
        yaxis='y',               # still tied to top price pane y-axis
        name='Vol Profile',
        hoverinfo='skip',
        showlegend=False
    ))

    # --- Latest Indicator Summary Box (Bottom-Right of Price Pane) ---
    latest = df.iloc[-1]
    latest_price = latest['Close']

    info_text = f"""
    <b>CLOSE:</b> ${latest_price:.2f}  <b>SMA 20:</b> {latest['SMA_20']:.2f}  <b>SMA 50:</b> {latest['SMA_50']:.2f}  <b>SMA 200:</b> {latest['SMA_200']:.2f}<br>
    <b>BB Upper:</b> {latest['BB_Upper']:.2f}  <b>BB Lower:</b> {latest['BB_Lower']:.2f}  <b>RSI (14):</b> {latest['RSI']:.2f}  <b>MACD:</b> {latest['MACD']:.3f}  <b>Signal:</b> {latest['MACD_Signal']:.3f}
    """

    fig.add_annotation(
        text=info_text,
        align="left",

        # Position inside first pane (bottom-right)
        xref="x domain",
        yref="y domain",
        x=1,
        y=-0.05,

        showarrow=False,
        bordercolor="rgba(255,255,255,0.4)",
        borderwidth=1,
        bgcolor="rgba(0,0,0,0.6)",
        font=dict(size=10, color="#fffbc6"),
        row=1,
        col=1
    )

    # --- Daily Volume Bars (Row 2) ---
    # >>> NEW: volume bars directly under price pane
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        name='Volume',
        marker=dict(color='rgba(100, 181, 246, 0.7)'),
        showlegend=False
    ), row=2, col=1)

    # --- RSI (Row 3) ---
    fig.add_trace(go.Scatter(
        x=df.index, y=df['RSI'],
        line=dict(color='#ba68c8', width=2),
        name='RSI'
    ), row=3, col=1)

    fig.add_hline(y=70, line_dash="dot", line_color="gray", row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="gray", row=3, col=1)

    # --- MACD (Row 4) ---
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['MACD_Hist'],
        marker_color=np.where(df['MACD_Hist'] < 0, '#ef5350', '#26a69a'),
        name='Histogram'
    ), row=4, col=1)

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MACD'],
        line=dict(color='#2962ff', width=1.5),
        name='MACD'
    ), row=4, col=1)

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MACD_Signal'],
        line=dict(color='#ff6d00', width=1.5),
        name='Signal'
    ), row=4, col=1)

    # --- Layout Styling ---
    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        height=1000,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.96,
            xanchor="right",
            x=1
        ),

        # new xaxis5 for volume profile
        xaxis5=dict(
            overlaying='x',             # share the same horizontal space as xaxis (row 1)
            side='top',
            range=[0, max_vol * 6],     # adjust thickness
            showticklabels=False,
            showgrid=False
        ),
    )

    fig.update_xaxes(
        dtick="M1",                    # monthly ticks
        tickformat="%b %Y",            # Jan 2025 format
        ticklabelmode="period",
        showgrid=False,
        rangebreaks=[
            dict(bounds=["sat", "mon"]),  # hide weekends
        ]
    )
    # Grid styling
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)')

    # Axis labels / ranges
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MACD", row=4, col=1)

    # fig.show()
    fig.write_image(image_path, width=1600, height=1000, scale=2)
    return image_path


def technical_analysis(symbol: str):
    """
    Generate or fetch today's technical analysis for the given ticker.
    - Reuse the cached report for today if it already exists.
    - Otherwise, gather fresh technicals, persist the raw data, call the LLM,
      persist the analysis, and return it.
    """
    symbol = symbol.upper()
    today = date.today().isoformat()

    base_dir = Path(__file__).resolve().parents[2] / "data" / "technicals" / symbol.replace("^", "INDEX_")
    base_dir.mkdir(parents=True, exist_ok=True)

    analysis_path = base_dir / f"{today}-{symbol.replace("^", "INDEX_")}-technical-analysis-report.json"
    if analysis_path.exists():
        with analysis_path.open("r") as f:
            return json.load(f)

    ta_report = {}
    charts = {}
    # get daily chart
    charts["daily price chart path"] = str(generate_chart(symbol, period="1y", type="daily"))
    # get weekly chart
    charts["weekly price chart path"] = str(generate_chart(symbol, period="5y", type="weekly"))
    ta_report["chart image path"] = charts
    ta_data = gather_ta_data(symbol)
    ta_report["technical data"] = ta_data

    # use LLM for technical analysis. Need to call a multi-modal model
    contents = []
    contents.append(json.dumps(ta_data, indent=2))
    for img_path in ta_report['chart image path'].values():
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

    # call LLM
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config={"system_instruction":TA_PROMPT},
    )
    # print(response.text)
    analysis_text = response.text.strip()
    if analysis_text.startswith("```"):
        lines = analysis_text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        analysis_text = "\n".join(lines).lstrip("json").strip()

    analysis_report = json.loads(analysis_text)
    ta_report["technical analysis report"] = analysis_report

    with analysis_path.open("w") as f:
        json.dump(ta_report, f, indent=2)

    return ta_report


if __name__ == "__main__":
    ta_report = technical_analysis("^DJI")
    print(json.dumps(ta_report, indent=4))
