from app.services.technicals import technical_analysis
from app.services.news import sentimental_analysis

SP500 = "^GSPC"
NASDAQ = "^IXIC"
DJI = "^DJI"

def get_index_performance() -> dict:
    """
    use this function to get the technical analysis of three major indices and the news
    related to the overall market
    return a dictionary with the following structure.
    {
        "technical analysis of three indices": {
          "SP500": {},
          "NASDAQ": {},
          "DJI": {},
        },
        "related news": {
          "SP500": {},
          "NASDAQ": {},
          "DJI": {}
        }
    }
    """
    output = {
        "technical analysis of three indices": {},
        "related news": {}
    }
    indices = {"SP500": SP500, "NASDAQ": NASDAQ, "DJI": DJI}
    for key, idx in indices.items():
        output["technical analysis of three indices"][key] = technical_analysis(symbol=idx)
        output["related news"][key] = sentimental_analysis(symbol=idx, use_existing=True)
    return output