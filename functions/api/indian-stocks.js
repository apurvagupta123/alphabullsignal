export async function onRequest() {
  const symbols = [
    'RELIANCE.NS','TCS.NS','HDFCBANK.NS',
    'INFY.NS','WIPRO.NS','ICICIBANK.NS',
    '%5ENSEI','%5EBSESN'
  ];

  const hdrs = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9'
  };

  try {
    const fetches = symbols.map(sym =>
      fetch('https://query1.finance.yahoo.com/v8/finance/chart/' + sym + '?interval=1d&range=1d', { headers: hdrs })
        .then(r => r.json())
        .catch(() => null)
    );
    const rawResults = await Promise.all(fetches);

    const result = rawResults
      .map((d, i) => {
        if (!d) return null;
        const meta = d?.chart?.result?.[0]?.meta;
        if (!meta || !meta.regularMarketPrice) return null;
        const price = meta.regularMarketPrice;
        const prev = meta.previousClose || meta.chartPreviousClose || price;
        const change = price - prev;
        const pct = prev ? (change / prev) * 100 : 0;
        const rawSym = symbols[i];
        const sym = rawSym === '%5ENSEI' ? '^NSEI' : rawSym === '%5EBSESN' ? '^BSESN' : rawSym;
        return { symbol: sym, regularMarketPrice: price, regularMarketChange: change, regularMarketChangePercent: pct };
      })
      .filter(Boolean);

    return new Response(JSON.stringify({ quoteResponse: { result, error: null } }), {
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=60'
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }
}
