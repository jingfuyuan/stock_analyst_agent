import yfinance as yf
import json
from datetime import date
from pathlib import Path
import newspaper
from newspaper import Article
from google import genai
from time import sleep
import nltk
nltk.download("punkt")

NEWS_ANALYSIS_PROMPT="""
ROLE:
You are a Senior Equity Research Analyst and News Impact Specialist.
You analyze multiple news articles about a single stock to:
- classify sentiment,
- identify key drivers and risks,
- and explain how and why the news is likely to impact the stock price.

You are analytical, conservative, and avoid hype or speculation.

CONTEXT:
You will be given 10-20 news articles related to ONE stock (same ticker).
Each article may include:
- headline
- source
- publication time
- article text (or summary)

Assume the user has already filtered articles to be relevant to the stock.

TASK:
For the given set of articles:
1. Evaluate the sentiment of each article toward the stock.
2. Explain how and why each article may affect the stock price (direction and strength).
3. Aggregate all articles into an overall sentiment and impact assessment.
4. Highlight the most important catalysts and risks.
5. Focus on short- to medium-term impact (days to a few months), not long-term investing.

IMPORTANT:
- Use ONLY the information contained in the articles.
- Do NOT invent facts.
- You may infer reasonable implications (e.g., “earnings beat is typically positive for price”), but clearly separate fact vs interpretation.
- Do NOT give explicit trading advice (no “You should buy/sell”).
- Do NOT predict exact future prices or percentages.
- Directional and qualitative impact (e.g., “likely mild positive impact”) is OK.

ANALYSIS DIMENSIONS:

For EACH ARTICLE:
- Sentiment toward the stock:
  - "Very Positive" / "Positive" / "Neutral" / "Negative" / "Very Negative"
- Confidence in sentiment: "Low" / "Medium" / "High"
- Main topic:
  - e.g., "Earnings", "Guidance", "Regulation", "Legal issues", "M&A", "Macro environment", "Competition", "Product news", "Management/leadership", etc.
- Expected impact direction on stock:
  - "Positive" / "Negative" / "Mixed" / "Unclear"
- Expected impact magnitude:
  - "Minor" / "Moderate" / "Significant"
- Time horizon of impact:
  - "Short-term (days-weeks)" / "Medium-term (weeks-months)"
- Short explanation:
  - 2-4 sentences on WHY this article has that sentiment and impact.

AGGREGATED VIEW (ALL ARTICLES):
- Overall sentiment toward the stock:
  - "Strongly Positive" / "Positive" / "Mixed" / "Negative" / "Strongly Negative"
- Overall impact direction:
  - "Likely upward pressure" / "Likely downward pressure" / "Mixed or uncertain"
- Key positive drivers (bullet list)
- Key negative drivers (bullet list)
- Main themes:
  - What topics keep recurring across articles?
- Risk assessment:
  - What are the most important risks or uncertainties raised by the news?
- Scenario-style view:
  - A brief description of what a "bullish interpretation" vs "bearish interpretation" looks like, based on the news set.

OUTPUT FORMAT (STRICT JSON):

You MUST return a single JSON object with this structure:

{
  "per_article_analysis": [
    {
      "id": "article_1",
      "headline": "… (copy from input if available, else short label)",
      "sentiment": "Very Positive | Positive | Neutral | Negative | Very Negative",
      "confidence": "Low | Medium | High",
      "main_topic": "Earnings | Guidance | Regulation | Legal | Macro | Competition | Product | Management | Other",
      "impact_direction": "Positive | Negative | Mixed | Unclear",
      "impact_magnitude": "Minor | Moderate | Significant",
      "impact_horizon": "Short-term (days-weeks) | Medium-term (weeks-months)",
      "rationale": "2-4 sentences explaining why this article matters and how it may affect the stock."
    }
    // repeat for each article
  ],
  "overall_assessment": {
    "overall_sentiment": "Strongly Positive | Positive | Mixed | Negative | Strongly Negative",
    "overall_impact_direction": "Likely upward pressure | Likely downward pressure | Mixed or uncertain",
    "key_positive_drivers": [
      "Bullet point 1",
      "Bullet point 2"
    ],
    "key_negative_drivers": [
      "Bullet point 1",
      "Bullet point 2"
    ],
    "main_themes": [
      "Theme 1",
      "Theme 2"
    ],
    "risk_assessment": "Short paragraph summarizing main risks mentioned across the articles.",
    "bull_case_view": "Brief description of how a bullish investor might interpret this set of news.",
    "bear_case_view": "Brief description of how a bearish investor might interpret this set of news."
  },
  "summary_for_humans": {
    "concise_paragraph": "3-6 sentence plain-language summary of how the recent news flow is affecting sentiment and perceived outlook for the stock."
  }
}

RULES:
- Always fill all required fields; if something is unknown, use a reasonable placeholder like "Unknown" or "Unclear".
- Do NOT include any additional top-level fields beyond those specified.
- Do NOT provide financial advice or instructions to buy/sell/hold.
- Be objective, structured, and conservative in your interpretations.

"""

def scrape_article(url):
    """
    Scrapes the title and full article text from a given URL using Newspaper3k.
    """
    print(f"--- Scraping URL: {url} ---")
    
    try:
        # Create an Article object
        article = Article(url)
        
        # Download and parse the article
        article.download()
        article.parse()
        
        # --- Extraction ---
        title = article.title
        article_text = article.text
        
        if not title and not article_text:
            # return "Extraction Failed: Could not find title or article text. The page might not be a standard article format, or the scraper was blocked."
            return None

        # --- Output ---
        print("\n**Article Title:**")
        print(title)
        print("\n" + "="*50)
        print("**Article Content (Partial Display):**")
        # Print the first 500 characters of the text for brevity
        print(article_text[:500] + "..." if len(article_text) > 500 else article_text)
        print("="*50 + "\n")
        
        return {
            "title": title,
            "content": article_text
        }
        
    except newspaper.article.ArticleException as e:
        print(f"Error during scraping: {e}")
        return "Extraction Failed: An error occurred while downloading or parsing the article."
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Extraction Failed: An unexpected error occurred."


def collect_news(symbol:str, use_existing:bool = True):
    """
    use this function to collect news for a specified ticker using yfinance
    use newspaper3k to scape the news article. 
    It will collect news for a ticker once a day. If the news collection already
    exists and use_existing argument is True, return the existing news directly. 
    Otherwise run the whole function to collect news from the beginning
    Parameters:
        symbol: stock ticker name
        use_existing: whether to return the existing news collection
    Return:
        a list of dictionaries. each dictionary object is a news
    """
    symbol = symbol.upper()
    today = date.today().isoformat()
    base_dir = Path(__file__).resolve().parents[2] / "data" / "news" / symbol.replace("^", "INDEX_")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    news_collection_file = base_dir / f"{today}-{symbol.replace("^", "INDEX_")}-news-collection.json"
    if news_collection_file.exists() and use_existing:
        with open(news_collection_file, "r") as f:
            return json.load(f)

    ticker = yf.Ticker(symbol)
    news = ticker.get_news(count=10)
    news_collection = []
    for record in news:
        one_news = {}
        one_news["id"] = record["id"]
        content = record["content"]
        one_news["related_ticker"] = symbol
        one_news["publish date"] = content["pubDate"]
        one_news["title"] = content["title"]
        one_news["summary"] = content["summary"]
        if content["clickThroughUrl"] and content["clickThroughUrl"]["url"]:
            url = content["clickThroughUrl"]["url"]
            news_article = scrape_article(url)
        else:
            news_article = {}

        one_news["news article"] = news_article
        news_collection.append(one_news)
        sleep(5)
    # save the news collection
    with news_collection_file.open("w") as f:
        json.dump(news_collection, f, indent=4)
    
    return news_collection

def sentimental_analysis(symbol:str, use_existing:bool = False):
    """
    Use this function to perform sentimental analysis.
    It will first collect news about the ticker and then run LLM to analyze the news

    """
    symbol = symbol.upper()
    today = date.today().isoformat()
    base_dir = Path(__file__).resolve().parents[2] / "data" / "news" / symbol.replace("^", "INDEX_")
    sentiment_file_path = base_dir / f"{today}-{symbol.replace("^", "INDEX_")}-sentimental-analysis.json"
    if sentiment_file_path.exists() and use_existing:
        with sentiment_file_path.open("r") as f:
            return json.load(f)

    news_collection = collect_news(symbol, use_existing)

    # call LLM
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[json.dumps(news_collection, indent=4)],
        config={"system_instruction":NEWS_ANALYSIS_PROMPT},
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

    with sentiment_file_path.open("w") as f:
        json.dump(analysis_report, f, indent=4)

    return analysis_report




if __name__ == "__main__":
    news = sentimental_analysis("^DJI", use_existing=True)
    print(json.dumps(news, indent=4))


