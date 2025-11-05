from flask import Flask, Response
import requests
import time
from datetime import datetime, timedelta
import os  # برای گرفتن پورت از Render

app = Flask(__name__)

CACHE = {"rss": None, "updated": 0}

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_PARAMS = {
    "ids": "toncoin",
    "vs_currencies": "usd,btc",
    "include_24hr_change": "true",
    "include_last_updated_at": "true"
}

EXCHANGE_URL = "https://api.exchangerate.host/latest?base=USD&symbols=IRR"

def build_rss(data, ir_rate):
    now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    price = data.get("toncoin", {})

    # استفاده از مقدار پیش‌فرض در صورت نبود داده
    usd = price.get("usd", 0)
    btc = price.get("btc", 0)
    change_24h = price.get("usd_24h_change", 0)
    updated_at = price.get("last_updated_at", int(time.time()))
    ir = round(usd * ir_rate)

    # زمان به UTC
    updated_utc = datetime.utcfromtimestamp(updated_at).strftime("%Y-%m-%d %H:%M:%S UTC")
    # زمان به ایران (IRST)
    iran_offset = timedelta(hours=3, minutes=30)
    updated_iran = (datetime.utcfromtimestamp(updated_at) + iran_offset).strftime("%Y-%m-%d %H:%M:%S IRST")

    title = f"Toncoin (TON) قیمت: ${usd} | {ir} IRR"
    description = f"""💵 قیمت دلاری: {usd} USD
🇮🇷 قیمت ریالی: {ir} IRR
⏱ آخرین بروزرسانی: {updated_utc} | {updated_iran}
🔺 تغییر 24 ساعته: {change_24h:.2f}%
💹 قیمت BTC: {btc}
🔗 منبع: https://www.coingecko.com/en/coins/toncoin
"""

    item = f"""<item>
  <title>{title}</title>
  <description><![CDATA[{description}]]></description>
  <pubDate>{now}</pubDate>
  <guid isPermaLink="false">ton-{int(time.time())}</guid>
</item>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Toncoin (TON) قیمت لحظه‌ای</title>
  <link>https://your-render-app-url/</link>
  <description>فید لحظه‌ای قیمت Toncoin از CoinGecko</description>
  <lastBuildDate>{now}</lastBuildDate>
  {item}
</channel>
</rss>"""
    return rss

def fetch_and_cache():
    if time.time() - CACHE["updated"] < 60 and CACHE["rss"]:
        return CACHE["rss"]

    # درخواست به CoinGecko
    try:
        r = requests.get(COINGECKO_URL, params=COINGECKO_PARAMS, timeout=10)
        data = r.json()
    except:
        data = {"toncoin": {"usd": 0, "btc": 0, "usd_24h_change": 0, "last_updated_at": int(time.time())}}

    # درخواست به ExchangeRate.host
    try:
        r2 = requests.get(EXCHANGE_URL, timeout=10)
        ir_rate = r2.json().get("rates", {}).get("IRR", 42000)
    except:
        ir_rate = 42000

    rss = build_rss(data, ir_rate)
    CACHE["rss"] = rss
    CACHE["updated"] = time.time()
    return rss

# مسیر اصلی / → صفحه ساده با لینک RSS
@app.route("/")
def home():
    return """
    <h2>Toncoin RSS Feed</h2>
    <p>برای مشاهده فید: <a href="/ton.rss">ton.rss</a></p>
    """

# مسیر RSS
@app.route("/ton.rss")
@app.route("/Ton.rss")  # پشتیبانی از T بزرگ
def ton_rss():
    rss = fetch_and_cache()
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)🔺 تغییر 24 ساعته: {change_24h:.2f}%
💹 قیمت BTC: {btc}
🔗 منبع: https://www.coingecko.com/en/coins/toncoin
"""

    item = f"""<item>
  <title>{title}</title>
  <description><![CDATA[{description}]]></description>
  <pubDate>{now}</pubDate>
  <guid isPermaLink="false">ton-{int(time.time())}</guid>
</item>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Toncoin (TON) قیمت لحظه‌ای</title>
  <link>https://your-render-app-url/</link>
  <description>فید لحظه‌ای قیمت Toncoin از CoinGecko</description>
  <lastBuildDate>{now}</lastBuildDate>
  {item}
</channel>
</rss>"""
    return rss

def fetch_and_cache():
    if time.time() - CACHE["updated"] < 60 and CACHE["rss"]:
        return CACHE["rss"]

    # درخواست به CoinGecko
    try:
        r = requests.get(COINGECKO_URL, params=COINGECKO_PARAMS, timeout=10)
        data = r.json()
    except:
        data = {"toncoin": {"usd": 0, "btc": 0, "usd_24h_change": 0, "last_updated_at": int(time.time())}}

    # درخواست به ExchangeRate.host
    try:
        r2 = requests.get(EXCHANGE_URL, timeout=10)
        ir_rate = r2.json().get("rates", {}).get("IRR", 42000)
    except:
        ir_rate = 42000

    rss = build_rss(data, ir_rate)
    CACHE["rss"] = rss
    CACHE["updated"] = time.time()
    return rss

# مسیر اصلی / → صفحه ساده با لینک RSS
@app.route("/")
def home():
    return """
    <h2>Toncoin RSS Feed</h2>
    <p>برای مشاهده فید: <a href="/ton.rss">ton.rss</a></p>
    """

# مسیر RSS
@app.route("/ton.rss")
@app.route("/Ton.rss")  # پشتیبانی از T بزرگ
def ton_rss():
    rss = fetch_and_cache()
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
