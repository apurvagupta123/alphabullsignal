export async function onRequest() {
  const ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
  const cors = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Cache-Control': 'public, max-age=60'
  };
  const debug = [];

  // 1. Yahoo Finance with crumb authentication
  try {
    // Get session cookies from fc.yahoo.com (Yahoo consent endpoint)
    const fcResp = await fetch('https://fc.yahoo.com', {
      headers: { 'User-Agent': ua, 'Accept-Language': 'en-US,en;q=0.9', 'Accept': 'text/html,application/xhtml+xml,*/*' },
      redirect: 'follow'
    });
    const rawCookies = [];
    const setCookie = fcResp.headers.getSetCookie ? fcResp.headers.getSetCookie() : [fcResp.headers.get('set-cookie') || ''];
    for (const c of setCookie) rawCookies.push(c.split(';')[0]);
    const cookies = rawCookies.join('; ');
    debug.push('fc_cookies:' + rawCookies.length);

    // Get crumb
    const crumbResp = await fetch('https://query1.finance.yahoo.com/v1/test/getcrumb', {
      headers: { 'User-Agent': ua, 'Cookie': cookies, 'Accept': '*/*' }
    });
    const crumb = (await crumbResp.text()).trim();
    debug.push('crumb:' + crumb.slice(0, 20));

    if (crumb && !crumb.includes('{') && !crumb.includes('<') && crumb.length < 50) {
      const symbols = 'RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS,WIPRO.NS,ICICIBANK.NS,%5ENSEI,%5EBSESN,%5ENSEBANK';
      const qResp = await fetch(
        `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${symbols}&crumb=${encodeURIComponent(crumb)}`,
        { headers: { 'User-Agent': ua, 'Cookie': cookies, 'Accept': 'application/json' } }
      );
      const data = await qResp.json();
      debug.push('yf_status:' + qResp.status + ',results:' + (data?.quoteResponse?.result?.length || 0));
      const results = (data?.quoteResponse?.result || []).filter(q => q.regularMarketPrice).map(q => ({
        symbol: q.symbol,
        regularMarketPrice: q.regularMarketPrice,
        regularMarketChange: q.regularMarketChange || 0,
        regularMarketChangePercent: q.regularMarketChangePercent || 0
      }));
      if (results.length >= 3) {
        return new Response(JSON.stringify({ quoteResponse: { result: results, error: null }, _debug: debug }), { headers: cors });
      }
    }
  } catch(e) { debug.push('yf_err:' + e.message); }

  // 2. Stooq fallback for all symbols
  const stooqMap = [
    ['reliance.ns','RELIANCE.NS'],['tcs.ns','TCS.NS'],['hdfcbank.ns','HDFCBANK.NS'],
    ['infy.ns','INFY.NS'],['wipro.ns','WIPRO.NS'],['icicibank.ns','ICICIBANK.NS'],
    ['%5ensei','^NSEI'],['%5ebsesn','^BSESN'],['%5ensebank','^NSEBANK']
  ];
  const stooqResults = await Promise.allSettled(stooqMap.map(async ([s, out]) => {
    try {
      const r = await fetch(`https://stooq.com/q/d/l/?s=${s}&i=d`, { headers: { 'User-Agent': ua } });
      const text = await r.text();
      const lines = text.trim().split('\n').filter(l => l && !l.startsWith('Date'));
      if (!lines.length) return null;
      const last = lines[lines.length - 1].split(',');
      const prev = lines.length > 1 ? lines[lines.length - 2].split(',') : last;
      const close = parseFloat(last[4]);
      const prevClose = parseFloat(prev[4]);
      if (!close || isNaN(close)) return null;
      const change = close - prevClose;
      return { symbol: out, regularMarketPrice: close, regularMarketChange: change, regularMarketChangePercent: prevClose ? (change/prevClose)*100 : 0 };
    } catch(e) { return null; }
  }));
  const fallback = stooqResults.filter(r => r.status==='fulfilled' && r.value).map(r => r.value);
  debug.push('stooq:' + fallback.length);

  return new Response(JSON.stringify({ quoteResponse: { result: fallback, error: null }, _debug: debug }), {
    headers: { ...cors, 'Cache-Control': 'public, max-age=300' }
  });
}
