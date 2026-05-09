const SYMBOLS = [
  { symbol: "BZ=F",  label: "Brent Crude",    unit: "/bbl" },
  { symbol: "CL=F",  label: "WTI Crude",       unit: "/bbl" },
  { symbol: "CC=F",  label: "Cocoa (ICE)",     unit: "/t",  scale: 1 },
  { symbol: "KC=F",  label: "Arabica Coffee",  unit: "/lb" },
  { symbol: "ZW=F",  label: "Wheat (CBOT)",    unit: "/bu" },
  { symbol: "ZS=F",  label: "Soybeans",        unit: "/bu" },
  { symbol: "NG=F",  label: "Natural Gas",     unit: "/MMBtu" },
  { symbol: "HG=F",  label: "Copper",          unit: "/lb" },
  { symbol: "GC=F",  label: "Gold",            unit: "/oz" },
];

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Cache-Control", "s-maxage=300, stale-while-revalidate=60");

  const query = SYMBOLS.map(s => s.symbol).join(",");
  const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${query}&fields=regularMarketPrice,regularMarketChangePercent`;

  try {
    const response = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0" },
    });

    if (!response.ok) throw new Error(`Yahoo Finance returned ${response.status}`);

    const data = await response.json();
    const quotes = data?.quoteResponse?.result ?? [];

    const priceMap = {};
    quotes.forEach(q => { priceMap[q.symbol] = q; });

    const result = SYMBOLS.map(({ symbol, label, unit }) => {
      const q = priceMap[symbol];
      if (!q) return null;
      const price = q.regularMarketPrice;
      const change = q.regularMarketChangePercent;
      return {
        label,
        price: formatPrice(symbol, price),
        unit,
        change: change != null ? parseFloat(change.toFixed(2)) : null,
      };
    }).filter(Boolean);

    res.json({ ok: true, prices: result });
  } catch (err) {
    res.status(502).json({ ok: false, error: err.message });
  }
}

function formatPrice(symbol, price) {
  if (!price) return "—";
  if (symbol === "CC=F") return price.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (["BZ=F", "CL=F", "GC=F"].includes(symbol)) return price.toFixed(2);
  if (["KC=F", "HG=F"].includes(symbol)) return price.toFixed(2);
  if (symbol === "NG=F") return price.toFixed(3);
  return price.toFixed(2);
}
