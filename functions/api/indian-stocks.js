export async function onRequest() {
  const symbols = [
    'RELIANCE.NS','TCS.NS','HDFCBANK.NS',
    'INFY.NS','WIPRO.NS','ICICIBANK.NS',
    '%5ENSEI','%5EBSESN'
  ].join(',');

  try {
    const r = await fetch(
      'https://query1.finance.yahoo.com/v7/finance/quote?symbols=' + symbols,
      {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
          'Accept': 'application/json',
          'Accept-Language': 'en-US,en;q=0.9'
        }
      }
    );
    const data = await r.json();
    return new Response(JSON.stringify(data), {
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
