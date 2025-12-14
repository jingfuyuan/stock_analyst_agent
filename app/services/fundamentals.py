import json
from datetime import date
from pathlib import Path
import yfinance as yf
import pandas as pd
from typing import Dict
from google import genai

FA_PROMPT="""
ROLE:
You are a Senior Fundamental Equity Analyst specializing in long-term investing.
You apply proven strategies from Warren Buffett, Benjamin Graham, Peter Lynch, and Joel Greenblatt.
Your focus is strictly on fundamentals, not short-term price movement.

TASK:
Analyze the provided income statement, balance sheet, cash flow statement, and calculated indicators to determine whether this company is fundamentally strong and suitable for long-term investment.

INPUT:
You will receive:
- trainling 12-month Income Statement
- most recent quarter Balance Sheet
- trainling 12-month Cash Flow Statement
- Pre-calculated indicators (ROIC, ROE, margins, growth rates, PEG, P/E, FCF yield, debt ratios, etc.)
Assume all data is accurate.

ANALYSIS INSTRUCTIONS:
Evaluate the company based on:
1. Financial Safety (debt, liquidity, stability)
2. Business Quality (profitability, ROIC, margins, cash flow consistency)
3. Growth Sustainability (revenue, EPS, FCF trends)
4. Valuation Reasonableness (P/E, PEG, FCF yield, relative attractiveness)
5. Key Risks and Red Flags

OUTPUT FORMAT (STRICT):
Return your response using the following structure:

{
  "fundamental_overview": "Brief summary of overall financial condition",
  "key_strengths": [
    "Strength 1",
    "Strength 2",
    "Strength 3"
  ],
  "key_weaknesses": [
    "Weakness 1",
    "Weakness 2",
    "Weakness 3"
  ],
  "growth_assessment": "Short evaluation of growth quality and sustainability",
  "valuation_perspective": "Undervalued | Fairly Valued | Overvalued",
  "investment_verdict": {
    "rating": "Strong Buy | Buy | Hold | Cautious Hold | Avoid",
    "justification": "3-5 sentences explaining the verdict",
    "best_fit_investor": "Conservative | Balanced | Growth-oriented"
  }
}

IMPORTANT RULES:
- Base all conclusions strictly on the provided data
- Do not predict future stock prices
- Be conservative when assessing risks
- Flag any inconsistencies or anomalies in the data
- Prioritize long-term investment quality over short-term trends
"""

def get_valuation_indicators(symbol:str) -> Dict:
    """
    Use this function to calculate valuation indicators of a stock. 
    These tell you if the stock is cheap or expensive relative to what the company actually earns.
    The indicators to calculate are:
    - P/E Ratio TTM (Price-to-Earnings)
    - P/E Ration Forward
    - PEG Ratio (Price/Earnings-to-Growth)
    - P/B Ratio (Price-to-Book)

    Parameters:
        symbol: ticker symbol of a sotck
    Return:
        A dictionary containing these indicators. 
        Example: {"PE Ratio TTM": 20, "PE Ratio Forward": 19, "PEG Ratio": 1.2, "PB Ratio": 5}
    """

    valuation_indicators = {}
    ticker = yf.Ticker(symbol)
    yearly_income_statement = ticker.get_income_stmt(pretty=True, freq="trailing")
    last_filing_date = yearly_income_statement.columns[0].strftime('%Y-%m-%d')
    stmt_dict = yearly_income_statement[last_filing_date].to_dict()
    fast_info = dict(ticker.get_fast_info())
    last_price = fast_info["lastPrice"]
    diluted_eps = stmt_dict["Diluted EPS"]
    balance_sheet = ticker.get_balance_sheet(pretty=True, freq="quarterly")[last_filing_date].to_dict()
    stockholders_equity = balance_sheet["Stockholders Equity"]
    shares = stmt_dict["Diluted Average Shares"]
    valuation_indicators["PE Ratio TTM"] = last_price / diluted_eps
    valuation_indicators["PB Ratio"] = last_price * shares / stockholders_equity

    growth_indicators = get_growth_indicators(symbol)
    next_year_eps_estimate = growth_indicators["next_year_eps_estimate"]
    valuation_indicators["PE Ratio Forward"] = last_price / next_year_eps_estimate
    next_year_eps_growth_rate = growth_indicators["next_year_eps_growth_rate"]
    valuation_indicators["PEG Ratio"] = valuation_indicators["PE Ratio Forward"] / (100 * next_year_eps_growth_rate)

    return valuation_indicators

def get_profitability_indicators(symbol: str) -> dict:
    """
    Use this function to calculate profitability indicators of a stock. 
    These tell you how efficient the company is at turning capital into profit
    The indicators to calculate are:
    - EPS (Earnings Per Share)
    - ROE (Return on Equity)
    - Gross Margin
    - Operating Margin
    - Net Margin
    - Return on Invested Capital (ROIC)

    Parameters:
        symbol: ticker symbol of a sotck
    Return:
        A dictionary containing these indicators. 
        Example: {"Earning Per Share": ###, "Return on Equity": ###, "Operation Margin": ###, ...}

    """
    profitability_indicators = {}
    ticker = yf.Ticker(symbol)
    yearly_income_statement = ticker.get_income_stmt(pretty=True, freq="trailing")
    last_filing_date = yearly_income_statement.columns[0].strftime('%Y-%m-%d')
    stmt_dict = yearly_income_statement[last_filing_date].to_dict()
    balance_sheet = ticker.get_balance_sheet(pretty=True, freq="quarterly")[last_filing_date].to_dict()

    profitability_indicators["Earning Per Share"] = stmt_dict["Diluted EPS"]
    profitability_indicators["Return On Equity"] = stmt_dict["Net Income"] / balance_sheet["Stockholders Equity"]
    profitability_indicators["Gross Margin"] = stmt_dict["Gross Profit"] / stmt_dict["Total Revenue"]
    profitability_indicators["Operating Margin"] = stmt_dict["EBIT"] / stmt_dict["Total Revenue"]
    profitability_indicators["Net Profit Margin"] = stmt_dict["Net Income"] / stmt_dict["Total Revenue"]
    tax_rate = stmt_dict["Tax Provision"] / stmt_dict["Pretax Income"]
    invested_capital = balance_sheet["Total Debt"] + balance_sheet["Stockholders Equity"] - balance_sheet["Cash And Cash Equivalents"]
    profitability_indicators["ROIC"] = stmt_dict["EBIT"] * (1 - tax_rate) / invested_capital
    return profitability_indicators

def get_financial_health_indicators(symbol: str) -> dict:
    """
    Use this function to calculate the financial health indicators of a stock. 
    These tell you the risk that the company runs out of money
    The indicators to calculate are:
    - Debt-to-Equity (D/E) Ratio
    - Free Cash Flow (FCF)
    - Current Ratio
    - FCF Margin

    Parameters:
        symbol: ticker symbol of a sotck
    Return:
        A dictionary containing these indicators. 
        Example: {"Debet-to-Equity ration": ###, "Free Cash Flow": ###, "Current Ratio": ###}

    """

    financial_health_indicators = {}
    ticker = yf.Ticker(symbol)
    yearly_income_statement = ticker.get_income_stmt(pretty=True, freq="trailing")
    last_filing_date = yearly_income_statement.columns[0].strftime('%Y-%m-%d')
    stmt_dict = yearly_income_statement[last_filing_date].to_dict()
    balance_sheet = ticker.get_balance_sheet(pretty=True, freq="quarterly")[last_filing_date].to_dict()   
    cashflow = ticker.get_cashflow(pretty=True, freq="trailing")[last_filing_date].to_dict()
    financial_health_indicators["Free Cash Flow"] = cashflow["Free Cash Flow"]
    financial_health_indicators["Current Ratio"] = balance_sheet["Current Assets"] / balance_sheet["Current Liabilities"]
    total_liab = balance_sheet['Total Liabilities Net Minority Interest']
    total_equity = balance_sheet['Stockholders Equity']
    financial_health_indicators["Debt-to-Equity Ratio"] = total_liab / total_equity
    financial_health_indicators["FCF Margin"] = cashflow["Free Cash Flow"] / stmt_dict["Total Revenue"]
    return financial_health_indicators

def get_growth_indicators(symbol:str) -> Dict:
    """
    Use this function to get the growth indicators of a stock
    The indicators to calculated are:
    - EPS growth
    - EPS estimate
    """
    ticker = yf.Ticker(symbol)
    growth_indicators = {}
    earnings_estimate = ticker.earnings_estimate
    growth_indicators["current_year_eps_estimate"] = float(earnings_estimate.loc["0y", "avg"])
    growth_indicators["current_year_eps_growth_rate"] = float(earnings_estimate.loc["0y", "growth"])
    growth_indicators["number_analysts_current_year"] = int(earnings_estimate.loc["0y", "numberOfAnalysts"])
    growth_indicators["next_year_eps_estimate"] = float(earnings_estimate.loc["+1y", "avg"])
    growth_indicators["next_year_eps_growth_rate"] = float(earnings_estimate.loc["+1y", "growth"])
    growth_indicators["number_analysts_next_year"] = int(earnings_estimate.loc["+1y", "numberOfAnalysts"])
    
    return growth_indicators

def fundamental_data(symbol:str) -> Dict:
    # normalize the symbol
    symbol = symbol.upper()
    ticker = yf.Ticker(symbol)
    fast_info = dict(ticker.get_fast_info())
    yearly_income_statement = ticker.get_income_stmt(pretty=True, freq="trailing")
    last_filing_date = yearly_income_statement.columns[0].strftime('%Y-%m-%d')
    stmt_dict = yearly_income_statement[last_filing_date].to_dict()
    balance_sheet = ticker.get_balance_sheet(pretty=True, freq="quarterly")[last_filing_date].to_dict()   
    cashflow = ticker.get_cashflow(pretty=True, freq="trailing")[last_filing_date].to_dict()
    valuation_indicators = get_valuation_indicators(symbol)
    profitability_indicators = get_profitability_indicators(symbol)
    financial_health_indicators = get_financial_health_indicators(symbol)
    growth_indicators = get_growth_indicators(symbol)
    all_fundamental_info = {
        "Basic information": fast_info,
        "trailing 12-month income statement": stmt_dict,
        "most recent quarter balance sheet": balance_sheet,
        "trainling 12-month cashflow statement": cashflow,
        "valuation indicators": valuation_indicators,
        "profitability indicators": profitability_indicators,
        "financial health indicators": financial_health_indicators,
        "growth indicators": growth_indicators,
    }
    return all_fundamental_info

def fundamental_analysis(symbol: str):
    """
    Generate or fetch today's fundamental analysis for the given ticker.
    - Reuse the cached report for today if it already exists.
    - Otherwise, gather fresh fundamentals, persist the raw data, call the LLM,
      persist the analysis, and return it.
    """
    symbol = symbol.upper()
    today = date.today().isoformat()

    base_dir = Path(__file__).resolve().parents[2] / "data" / "fundamentals" / symbol
    base_dir.mkdir(parents=True, exist_ok=True)

    analysis_path = base_dir / f"{today}-{symbol}-fundamental-analysis-report.json"
    if analysis_path.exists():
        with analysis_path.open("r") as f:
            return json.load(f)

    fundamental_path = base_dir / f"{today}-{symbol}-fundamental-data.json"
    fundamentals = fundamental_data(symbol)
    with fundamental_path.open("w") as f:
        json.dump(fundamentals, f, indent=4, default=str)

    client = genai.Client()
    user_prompt = (
        "Analyze the following fundamentals and return ONLY valid JSON "
        "matching the specified output format.\n\n"
        f"{json.dumps(fundamentals, indent=4)}"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[user_prompt],
        config={"system_instruction": FA_PROMPT},
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

    with analysis_path.open("w") as f:
        json.dump(analysis_report, f, indent=2)

    return analysis_report

if __name__ == "__main__":
    # function test
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", type=str, help="stock ticker symbol")
    args = parser.parse_args()
    fa_report = fundamental_analysis(args.ticker)
    print(json.dumps(fa_report, indent=4))
