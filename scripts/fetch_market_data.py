#!/usr/bin/env python3
"""
fetch_market_data.py
Daily market data fetcher for thebusinessledger.theapurva.com

Run: python3 scripts/fetch_market_data.py
Output: public/data/*.json  (served as static files by the website)

Schedule: GitHub Actions runs this after Indian market close (10:00 UTC = 3:30 PM IST)
          and again after US market close (21:30 UTC = 4:30 PM EST)
"""

import json, os, sys
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system(f"{sys.executable} -m pip install yfinance -q")
    import yfinance as yf

# ── Output directory ──────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, 'public', 'data')
os.makedirs(OUT, exist_ok=True)

NOW = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# ── Symbol lists ──────────────────────────────────────────────────────────────

INDIA_INDICES = ['^NSEI', '^BSESN', '^NSEBANK', '^CNXIT', '^CNXAUTO', '^CNXPHARMA', '^CNXFMCG']
INDEX_NAMES   = {
    '^NSEI':      'NIFTY 50',
    '^BSESN':     'SENSEX',
    '^NSEBANK':   'NIFTY BANK',
    '^CNXIT':     'NIFTY IT',
    '^CNXAUTO':   'NIFTY AUTO',
    '^CNXPHARMA': 'NIFTY PHARMA',
    '^CNXFMCG':   'NIFTY FMCG',
}

NSE_STOCKS = [
    ('RELIANCE.NS',   'Reliance Industries'),
    ('TCS.NS',        'Tata Consultancy Services'),
    ('HDFCBANK.NS',   'HDFC Bank'),
    ('INFY.NS',       'Infosys'),
    ('ICICIBANK.NS',  'ICICI Bank'),
    ('HINDUNILVR.NS', 'Hindustan Unilever'),
    ('BAJFINANCE.NS', 'Bajaj Finance'),
    ('KOTAKBANK.NS',  'Kotak Mahindra Bank'),
    ('LT.NS',         'Larsen & Toubro'),
    ('SBIN.NS',       'State Bank of India'),
    ('WIPRO.NS',      'Wipro'),
    ('TMCV.NS',       'Tata Motors (CV)'),
    ('BHARTIARTL.NS', 'Bharti Airtel'),
    ('MARUTI.NS',     'Maruti Suzuki'),
    ('ADANIENT.NS',   'Adani Enterprises'),
    ('HCLTECH.NS',    'HCL Technologies'),
    ('TITAN.NS',      'Titan Company'),
    ('ASIANPAINT.NS', 'Asian Paints'),
]

BSE_STOCKS = [
    ('RELIANCE.BO',   'Reliance Industries'),
    ('TCS.BO',        'Tata Consultancy Services'),
    ('HDFCBANK.BO',   'HDFC Bank'),
    ('INFY.BO',       'Infosys'),
    ('ICICIBANK.BO',  'ICICI Bank'),
    ('TATASTEEL.BO',  'Tata Steel'),
    ('SUNPHARMA.BO',  'Sun Pharmaceutical'),
    ('ONGC.BO',       'ONGC'),
    ('BAJAJFINSV.BO', 'Bajaj Finserv'),
    ('POWERGRID.BO',  'Power Grid Corp'),
]

# All Indian sector stocks (for markets/index.astro)
SECTOR_STOCKS = [
    # Banking
    'HDFCBANK.NS','ICICIBANK.NS','KOTAKBANK.NS','AXISBANK.NS','SBIN.NS',
    'BANKBARODA.NS','PNB.NS','INDUSINDBK.NS','FEDERALBNK.NS','IDFCFIRSTB.NS','BANDHANBNK.NS','AUBANK.NS',
    # IT
    'TCS.NS','INFY.NS','WIPRO.NS','HCLTECH.NS','TECHM.NS','LTTS.NS','MPHASIS.NS','PERSISTENT.NS','COFORGE.NS','KPITTECH.NS',
    # Finance & NBFC
    'BAJFINANCE.NS','BAJAJFINSV.NS','HDFCAMC.NS','HDFCLIFE.NS','SBILIFE.NS','ICICIGI.NS','ICICIPRULI.NS','JIOFIN.NS','CHOLAFIN.NS','MUTHOOTFIN.NS',
    # Auto
    'TMCV.NS','MARUTI.NS','BAJAJ-AUTO.NS','HEROMOTOCO.NS','EICHERMOT.NS','TVSMOTOR.NS','ASHOKLEY.NS','BOSCHLTD.NS','MOTHERSON.NS',
    # Pharma
    'SUNPHARMA.NS','DRREDDY.NS','CIPLA.NS','DIVISLAB.NS','AUROPHARMA.NS','BIOCON.NS','LUPIN.NS','TORNTPHARM.NS','APOLLOHOSP.NS','MAXHEALTH.NS',
    # FMCG
    'HINDUNILVR.NS','ITC.NS','NESTLEIND.NS','BRITANNIA.NS','DABUR.NS','MARICO.NS','GODREJCP.NS','ASIANPAINT.NS','BERGEPAINT.NS','TATACONSUM.NS',
    # Energy
    'RELIANCE.NS','ONGC.NS','IOC.NS','BPCL.NS','HINDPETRO.NS','GAIL.NS','NTPC.NS','TATAPOWER.NS','ADANIGREEN.NS','ADANIPORTS.NS',
    # Infra
    'LT.NS','SIEMENS.NS','ABB.NS','BEL.NS','HAL.NS','RVNL.NS','IRFC.NS','CUMMINSIND.NS','THERMAX.NS','KEC.NS',
    # Metals
    'TATASTEEL.NS','JSWSTEEL.NS','HINDALCO.NS','VEDL.NS','SAIL.NS','NMDC.NS','COALINDIA.NS','MOIL.NS','JSWENERGY.NS','NATIONALUM.NS',
    # Telecom
    'BHARTIARTL.NS','IDEA.NS','HFCL.NS','TEJASNET.NS','NETWORK18.NS','ZEEL.NS','SUNTV.NS','INDIAMART.NS','NAUKRI.NS','TATACOMM.NS',
]

US_INDICES = ['^GSPC', '^DJI', '^IXIC', '^RUT']
US_INDEX_NAMES = {'^GSPC': 'S&P 500', '^DJI': 'Dow Jones', '^IXIC': 'NASDAQ', '^RUT': 'Russell 2000'}

US_TECH = [
    ('AAPL','Apple Inc'), ('MSFT','Microsoft'), ('GOOGL','Alphabet'),
    ('AMZN','Amazon'), ('META','Meta Platforms'), ('NVDA','NVIDIA'),
    ('TSLA','Tesla'), ('AMD','AMD'), ('INTC','Intel'), ('CRM','Salesforce'),
    ('ORCL','Oracle'), ('ADBE','Adobe'), ('NFLX','Netflix'), ('PYPL','PayPal'), ('QCOM','Qualcomm'),
]

US_FINANCE = [
    ('JPM','JPMorgan Chase'), ('BAC','Bank of America'), ('WFC','Wells Fargo'),
    ('GS','Goldman Sachs'), ('MS','Morgan Stanley'), ('C','Citigroup'),
    ('BLK','BlackRock'), ('V','Visa'), ('MA','Mastercard'),
    ('AXP','American Express'), ('BRK-B','Berkshire Hathaway'), ('SCHW','Charles Schwab'),
]

# ── Core fetch function ───────────────────────────────────────────────────────

def fetch_batch(symbols: list) -> dict:
    """
    Fetch latest close price + daily change for a list of symbols.
    Returns dict keyed by symbol.
    Uses yfinance batch download (single HTTP request for all symbols).
    """
    if not symbols:
        return {}

    print(f"  Fetching {len(symbols)} symbols...")
    try:
        raw = yf.download(
            symbols if len(symbols) > 1 else symbols[0],
            period='5d',
            interval='1d',
            progress=False,
            auto_adjust=True,
        )
        close = raw['Close'] if len(symbols) > 1 else raw['Close'].rename(symbols[0]).to_frame()
        if hasattr(close, 'to_frame'):
            close = close.to_frame()
    except Exception as e:
        print(f"  Batch download failed: {e}")
        return {}

    result = {}
    for sym in symbols:
        try:
            col = sym if sym in close.columns else close.columns[0] if len(symbols) == 1 else None
            if col is None:
                result[sym] = _empty(sym)
                continue
            series = close[col].dropna()
            if len(series) < 1:
                result[sym] = _empty(sym)
                continue
            price = float(series.iloc[-1])
            prev  = float(series.iloc[-2]) if len(series) >= 2 else price
            chg   = price - prev
            pct   = (chg / prev * 100) if prev else 0
            result[sym] = {
                'symbol': sym,
                'regularMarketPrice':         round(price, 2),
                'regularMarketChange':        round(chg,   2),
                'regularMarketChangePercent': round(pct,   2),
            }
        except Exception as e:
            print(f"  Error processing {sym}: {e}")
            result[sym] = _empty(sym)

    return result

def _empty(sym):
    return {'symbol': sym, 'regularMarketPrice': 0, 'regularMarketChange': 0, 'regularMarketChangePercent': 0}

def save(filename, data):
    path = os.path.join(OUT, filename)
    with open(path, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    size = os.path.getsize(path)
    print(f"  Saved {filename} ({size/1024:.1f} KB)")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*55}")
    print(f"  Market Data Fetch  —  {NOW}")
    print(f"{'='*55}")

    # 1. India indices
    print("\n[1/5] India Indices")
    idx_q = fetch_batch(INDIA_INDICES)
    save('india-indices.json', {
        'lastUpdated': NOW,
        'indices': [
            {**idx_q.get(s, _empty(s)), 'name': INDEX_NAMES.get(s, s)}
            for s in INDIA_INDICES
        ]
    })

    # 2. NSE + BSE stocks (india.astro page)
    print("\n[2/5] India NSE + BSE Stocks")
    all_india_syms = [s for s,_ in NSE_STOCKS] + [s for s,_ in BSE_STOCKS]
    india_q = fetch_batch(all_india_syms)
    save('india-stocks.json', {
        'lastUpdated': NOW,
        'nse': [
            {**india_q.get(s, _empty(s)), 'name': name}
            for s, name in NSE_STOCKS
        ],
        'bse': [
            {**india_q.get(s, _empty(s)), 'name': name}
            for s, name in BSE_STOCKS
        ],
    })

    # 3. India sector stocks (markets/index.astro page)
    print("\n[3/5] India Sector Stocks")
    unique_sector = list(dict.fromkeys(SECTOR_STOCKS))  # deduplicate, preserve order
    sector_q = fetch_batch(unique_sector)
    # Merge with already-fetched India data to avoid re-fetching
    sector_q.update(india_q)
    save('india-sectors.json', {
        'lastUpdated': NOW,
        'quotes': sector_q,
    })

    # 4. US Tech
    print("\n[4/5] US Tech Stocks")
    tech_syms = [s for s,_ in US_TECH]
    tech_q = fetch_batch(tech_syms)
    save('us-tech.json', {
        'lastUpdated': NOW,
        'stocks': [
            {**tech_q.get(s, _empty(s)), 'name': name}
            for s, name in US_TECH
        ],
    })

    # 5. US Finance + indices
    print("\n[5/5] US Finance Stocks + Indices")
    fin_syms = [s for s,_ in US_FINANCE]
    us_all = fetch_batch(fin_syms + US_INDICES)
    save('us-finance.json', {
        'lastUpdated': NOW,
        'stocks': [
            {**us_all.get(s, _empty(s)), 'name': name}
            for s, name in US_FINANCE
        ],
    })
    save('us-indices.json', {
        'lastUpdated': NOW,
        'indices': [
            {**us_all.get(s, _empty(s)), 'name': US_INDEX_NAMES.get(s, s)}
            for s in US_INDICES
        ],
    })

    # Meta file (for "last updated" display on site)
    save('meta.json', {'lastUpdated': NOW, 'status': 'ok'})

    print(f"\n✓ All data saved to public/data/")
    print(f"  Files: {', '.join(os.listdir(OUT))}\n")

if __name__ == '__main__':
    main()
