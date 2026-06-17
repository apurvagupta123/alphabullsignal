#!/usr/bin/env python3
"""
Fetch Indian financial news from RSS feeds → public/data/news.json
Sources: NDTV Profit, Livemint, Economic Times, Google News (all verified live)
Runs every 30 minutes via GitHub Actions
"""

import json, re, html, os, time
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError
from xml.etree import ElementTree as ET

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(IST).strftime('%Y-%m-%dT%H:%M:%S+05:30')

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# ── RSS feeds ── confirmed live as of 2026-06-17 ──────────────────────────
FEEDS = [
    # NDTV Profit — fresh + media:content images ✅
    {
        "url": "https://feeds.feedburner.com/ndtvprofit-latest",
        "source": "NDTV Profit",
        "category": "Markets",
    },
    # Livemint Markets — fresh + media:content images ✅
    {
        "url": "https://www.livemint.com/rss/markets",
        "source": "Mint",
        "category": "Markets",
    },
    # Livemint Economy — fresh + images ✅
    {
        "url": "https://www.livemint.com/rss/economy",
        "source": "Mint",
        "category": "Economy",
    },
    # Economic Times default feed — fresh, no images but high volume ✅
    {
        "url": "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        "source": "Economic Times",
        "category": "Markets",
    },
    # Google News Markets — aggregates all sources, when:7d for freshness ✅
    {
        "url": (
            "https://news.google.com/rss/search"
            "?q=india+stock+market+nifty+sensex+NSE+BSE+when:7d"
            "&hl=en-IN&gl=IN&ceid=IN:en"
        ),
        "source": "Google News",
        "category": "Markets",
    },
    # Google News Economy ✅
    {
        "url": (
            "https://news.google.com/rss/search"
            "?q=india+economy+RBI+rupee+budget+finance+when:7d"
            "&hl=en-IN&gl=IN&ceid=IN:en"
        ),
        "source": "Google News",
        "category": "Economy",
    },
]

NS = {
    "media":   "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc":      "http://purl.org/dc/elements/1.1/",
}


# ── helpers ────────────────────────────────────────────────────────────────

def fetch_url(url):
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=20) as r:
            return r.read()
    except Exception as e:
        print(f"  ⚠ fetch failed [{url[:55]}…]: {e}")
        return None


def parse_date(raw):
    """RFC 822 / ISO pubDate → IST ISO string."""
    if not raw:
        return NOW
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
    ):
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(IST).strftime('%Y-%m-%dT%H:%M:%S+05:30')
        except ValueError:
            pass
    return NOW


def clean_title(raw):
    if not raw:
        return ""
    t = html.unescape(raw).strip()
    # Google News appends " - Source Name" — strip it
    t = re.sub(r'\s*[-–]\s*[A-Z][^-–]{3,50}$', '', t)
    return t.strip()


def extract_img_from_html(desc_html):
    """Pull first img src from an HTML-encoded description (MoneyControl style)."""
    if not desc_html:
        return None
    decoded = html.unescape(desc_html)
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', decoded, re.I)
    return m.group(1) if m else None


def strip_html(desc_html):
    """Convert HTML description to plain text excerpt."""
    if not desc_html:
        return ""
    decoded = html.unescape(desc_html)
    text = re.sub(r'<[^>]+>', ' ', decoded)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:220]


def parse_feed(cfg):
    url = cfg["url"]
    print(f"  → {cfg['source']}: {url[:60]}…")
    raw = fetch_url(url)
    if not raw:
        return []

    # Handle ISO-8859-1 encoded feeds
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        try:
            text = re.sub(r'<\?xml[^>]+\?>', '', raw.decode("latin-1"))
            root = ET.fromstring(text.encode("utf-8"))
        except Exception as e:
            print(f"    ⚠ XML parse error: {e}")
            return []

    channel = root.find("channel")
    if channel is None:
        return []

    articles = []
    for item in channel.findall("item"):
        title_el = item.find("title")
        link_el  = item.find("link")
        desc_el  = item.find("description")
        pub_el   = item.find("pubDate")
        src_el   = item.find("source")

        title = clean_title(title_el.text if title_el is not None else "")
        if not title:
            continue

        link     = (link_el.text or "").strip() if link_el is not None else ""
        desc_raw = desc_el.text if desc_el is not None else ""
        pub_date = parse_date(pub_el.text if pub_el is not None else "")

        # ── image: try media:content → media:thumbnail → enclosure → img in desc
        image = None
        for tag in ("media:content", "media:thumbnail"):
            el = item.find(tag, NS)
            if el is not None:
                image = el.get("url")
                if image:
                    break
        if not image:
            enc = item.find("enclosure")
            if enc is not None and (enc.get("type", "").startswith("image") or
                                     enc.get("url", "").endswith((".jpg", ".png", ".webp"))):
                image = enc.get("url")
        if not image:
            image = extract_img_from_html(desc_raw)

        # ── excerpt
        excerpt = strip_html(desc_raw)
        if len(excerpt) < 20:
            excerpt = title

        # ── source label
        source = cfg["source"]
        if src_el is not None and src_el.text:
            source = src_el.text.strip()

        articles.append({
            "title":       title,
            "excerpt":     excerpt,
            "url":         link,
            "source":      source,
            "image":       image,
            "publishedAt": pub_date,
            "category":    cfg["category"],
        })

    print(f"    {len(articles)} articles, {sum(1 for a in articles if a['image'])} with images")
    return articles


# ── Claude AI summarisation ────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def ai_summarise(title: str, excerpt: str) -> str:
    """Call Claude Haiku to generate a 4-5 sentence plain-English summary."""
    if not ANTHROPIC_API_KEY:
        return excerpt  # fallback: use RSS excerpt

    prompt = (
        f"You are a financial news summariser for an Indian market dashboard. "
        f"Write a clear, engaging 4-5 sentence summary of this news article for retail investors. "
        f"Use plain English. No bullet points. No markdown. Focus on what it means for markets/investors.\n\n"
        f"Headline: {title}\n"
        f"Excerpt: {excerpt}"
    )

    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
        return resp["content"][0]["text"].strip()
    except Exception as e:
        print(f"    ⚠ AI summarise failed: {e}")
        return excerpt


def add_summaries(articles: list, prev_cache: dict) -> list:
    """Add AI summaries to articles, reusing cache for already-summarised URLs."""
    api_calls = 0
    for a in articles:
        url = a.get("url", "")
        # Reuse cached summary if article already processed
        if url in prev_cache and prev_cache[url].get("summary"):
            a["summary"] = prev_cache[url]["summary"]
            continue
        # Only summarise if we have meaningful content
        if len(a.get("excerpt", "")) > 40:
            print(f"    ✨ Summarising: {a['title'][:55]}…")
            a["summary"] = ai_summarise(a["title"], a["excerpt"])
            api_calls += 1
            time.sleep(0.3)  # gentle rate limit
        else:
            a["summary"] = a.get("excerpt", "")

    print(f"  AI calls made: {api_calls} (cached: {len(articles)-api_calls})")
    return articles


# ── main ───────────────────────────────────────────────────────────────────

def main():
    print(f"📰 Fetching news  [{NOW}]")

    # ── Load previous news.json to reuse AI summaries (avoid re-calling API)
    out_path = os.path.join(os.path.dirname(__file__), "..", "public", "data", "news.json")
    prev_cache: dict = {}
    try:
        with open(out_path, encoding="utf-8") as f:
            prev_data = json.load(f)
        prev_cache = {a["url"]: a for a in prev_data.get("articles", []) if a.get("url")}
        print(f"  Loaded {len(prev_cache)} cached summaries")
    except Exception:
        pass

    all_articles, seen = [], set()
    for cfg in FEEDS:
        try:
            for a in parse_feed(cfg):
                key = re.sub(r'\W+', '', a["title"].lower())[:60]
                if key not in seen:
                    seen.add(key)
                    all_articles.append(a)
        except Exception as e:
            print(f"  ⚠ feed error: {e}")

    # ── filter: last 30 days only
    cutoff = (datetime.now(IST) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S+05:30')
    all_articles = [a for a in all_articles if a.get("publishedAt", "") >= cutoff]

    # ── sort by date desc
    all_articles.sort(key=lambda a: a.get("publishedAt", ""), reverse=True)

    # ── Ensure featured (first) article has an image
    with_img    = [a for a in all_articles if a.get("image")]
    without_img = [a for a in all_articles if not a.get("image")]

    if with_img:
        featured = with_img[0]
        rest = sorted(with_img[1:] + without_img,
                      key=lambda a: a.get("publishedAt", ""), reverse=True)
        final = [featured] + rest
    else:
        final = all_articles

    final = final[:25]

    # ── Add AI summaries (cached where possible)
    print(f"\n🤖 Adding AI summaries…")
    final = add_summaries(final, prev_cache)

    out = {
        "lastUpdated": NOW,
        "count": len(final),
        "articles": final,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(final)} articles saved → public/data/news.json")
    if final:
        print(f"   Featured [{final[0]['source']}]: {final[0]['title'][:65]}")
    print(f"   With image: {sum(1 for a in final if a.get('image'))}/{len(final)}")
    print(f"   With summary: {sum(1 for a in final if a.get('summary'))}/{len(final)}")


if __name__ == "__main__":
    main()
