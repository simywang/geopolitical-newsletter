import sys
sys.path.insert(0, __file__.rsplit("/src/", 1)[0])

TICKERS = {
    "Brent Crude":       "BZ=F",
    "WTI Crude":         "CL=F",
    "Natural Gas":       "NG=F",
    "Wheat (CBOT)":      "ZW=F",
    "Corn (CBOT)":       "ZC=F",
    "Soybeans (CBOT)":   "ZS=F",
    "Cocoa (ICE)":       "CC=F",
    "Arabica Coffee":    "KC=F",
    "Copper":            "HG=F",
    "Gold":              "GC=F",
}

def fetch_prices() -> dict[str, str]:
    """Return {name: formatted_price_string}. Returns {} on any failure."""
    try:
        import yfinance as yf
        tickers = yf.Tickers(" ".join(TICKERS.values()))
        result = {}
        for name, symbol in TICKERS.items():
            try:
                info = tickers.tickers[symbol].fast_info
                price = info.last_price
                if price and price > 0:
                    result[name] = _fmt(name, price)
            except Exception:
                continue
        return result
    except Exception as e:
        print(f"[market_data] Price fetch failed: {e}")
        return {}


def _fmt(name: str, price: float) -> str:
    if "Coffee" in name:
        return f"${price:.2f}/lb"
    if "Cocoa" in name:
        return f"${price:,.0f}/t"
    if "Crude" in name or "Gold" in name:
        return f"${price:.2f}/bbl" if "Crude" in name else f"${price:.2f}/oz"
    if "Gas" in name:
        return f"${price:.3f}/MMBtu"
    if "Copper" in name:
        return f"${price:.3f}/lb"
    if any(g in name for g in ("Wheat", "Corn", "Soybeans")):
        return f"${price:.2f}/bu"
    return f"${price:.2f}"


def build_price_context(prices: dict[str, str]) -> str:
    """Format prices as a prompt context block."""
    if not prices:
        return ""
    lines = "\n".join(f"  {name}: {val}" for name, val in prices.items())
    return (
        "Current market reference prices (use as context only — "
        "do not invent price moves not supported by the articles):\n"
        + lines
    )
