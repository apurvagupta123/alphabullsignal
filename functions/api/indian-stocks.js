export async function onRequest() {
  const ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
  const stocks = ['RELIANCE','TCS','HDFCBANK','INFY','WIPRO','ICICIBANK'];

  const cors = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Cache-Control': 'public, max-age=60'
  };

  // ── Primary: NSE India public API ────────────────────────────────────
  try {
    const homeResp = await fetch('https://www.nseindia.com/', {
      headers: {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive'
      }
    });

    // Collect cookies
    const cookieParts = [];
    if (homeResp.headers.getSetCookie) {
      homeResp.headers.getSetCookie().forEach(c => cookieParts.push(c.split(';')[0]));
    } else {
      const raw = homeResp.headers.get('set-cookie') || '';
      raw.split(',').forEach(c => cookieParts.push(c.trim().split(';')[0]));
    }
    const cookie = cookieParts.join('; ');

    const nseHdrs = {
      'User-Agent': ua,
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'en-US,en;q=0.5',
      'Referer': 'https://www.nseindia.com/',
      'Cookie': cookie
    };

    const results = [];

    // Indices
    const idxResp = await fetch('https://www.nseindia.com/api/allIndices', { headers: nseHdrs });
    const idxData = await idxResp.json();
    const idxMap = [
      ['NIFTY 50', '^NSEI'],
      ['NIFTY BANK', '^NSEBANK'],
      ['INDIA VIX', '^INDIAVIX']
    ];
    for (const [name, sym] of idxMap) {
      const idx = idxData?.data?.find(i => i.indexSymbol === name);
      if (idx) results.push({
        symbol: sym,
        regularMarketPrice: idx.last,
        regularMarketChange: idx.variation,
        regularMarketChangePercent: idx.percentChange
      });
    }

    // Stocks in parallel
    const stockResults = await Promise.all(stocks.map(async sym => {
      const r = await fetch('https://www.nseindia.com/api/quote-equity?symbol=' + sym, { headers: nseHdrs });
      const d = await r.json();
      if (!d?.priceInfo?.lastPrice) return null;
      return {
        symbol: sym + '.NS',
        regularMarketPrice: d.priceInfo.lastPrice,
        regularMarketChange: d.priceInfo.change || 0,
        regularMarketChangePercent: d.priceInfo.pChange || 0
      };
    }));
    results.push(...stockResults.filter(Boolean));

    if (results.length >= 3) {
      return new Response(JSON.stringify({ quoteResponse: { result: results, error: null } }), { headers: cors });
    }
  } catch(e) {}

  // ── Fallback: Stooq end-of-day data ──────────────────────────────────
  const stooqMap = [
    ['reliance.ns','RELIANCE.NS'],['tcs.ns','TCS.NS'],
    ['hdfcbank.ns','HDFCBANK.NS'],['infy.ns','INFY.NS'],
    ['wipro.ns','WIPRO.NS'],['icicibank.ns','ICICIBANK.NS'],
    ['%5ensei','^NSEI'],['%5ebsesn','^BSESN']
  ];

  const fallback = await Promise.all(stooqMap.map(async ([s, out]) => {
    try {
      const r = await fetch('https://stooq.com/q/d/l/?s=' + s + '&i=d', { headers: { 'User-Agent': ua } });
      const text = await r.text();
      const lines = text.trim().split('\n').slice(1);
      if (!lines.length) return null;
      const last = lines[lines.length - 1].split(',');
      const prev = lines.length > 1 ? lines[lines.length - 2].split(',') : last;
      const close = parseFloat(last[4]);
      const prevClose = parseFloat(prev[4]);
      if (!close || isNaN(close)) return null;
      const change = close - prevClose;
      return { symbol: out, regularMarketPrice: close, regularMarketChange: change, regularMarketChangePercent: prevClose ? (change / prevClose) * 100 : 0 };
    } catch(e) { return null; }
  }));

  return new Response(JSON.stringify({ quoteResponse: { result: fallback.filter(Boolean), error: null } }), {
    headers: { ...cors, 'Cache-Control': 'public, max-age=300' }
  });
}
