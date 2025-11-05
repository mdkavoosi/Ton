from flask import Flask, Response
import requests
import time
from datetime import datetime

app = Flask(__name__)

# Cache برای کاهش درخواست‌ها به API
CACHE = {"rss": None, "updated": 0}

# تنظیمات API
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_PARAMS = {
    "ids": "toncoin",
    "vs_currencies": "usd,btc",
    "include_24hr_change": "true",
    "include_last_updated_at": "true"
}

EXCHANGE_URL = "https://api.exchangerate.host/latest?base=USD&symbols=IRR"

# تابع ساخت RSS
def build_rss(data, ir_rate):
    now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    price = data.get("toncoin", {})
    usd = price.get("usd", "n/a")
    btc = price.get("btc", "n/a")
    change_24h = price.get("usd_24h_change", 0)
    ir = round(usd * ir_rate)
    updated_at = price.get("last_updated_at", int(time.time()))
    updated_iso = datetime.utcfromtimestamp(updated_at).strftime("%Y-%m-%d %H:%M:%S UTC")

    title = f"Toncoin (TON) قیمت: ${usd} | {ir} IRR"
    description = f"""💵 قیمت دلاری: {usd} USD
🇮🇷 قیمت ریالی: {ir} IRR
⏱ آخرین بروزرسانی: {updated_iso}
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

# تابع گرفتن داده‌ها
def fetch_and_cache():
    if time.time() - CACHE["updated"] < 60 and CACHE["rss"]:
        return CACHE["rss"]

    # قیمت TON
    r = requests.get(COINGECKO_URL, params=COINGECKO_PARAMS, timeout=10)
    data = r.json()

    # نرخ دلار به ریال
    r2 = requests.get(EXCHANGE_URL, timeout=10)
    ir_rate = r2.json().get("rates", {}).get("IRR", 42000)  # پیش‌فرض 42000

    rss = build_rss(data, ir_rate)
    CACHE["rss"] = rss
    CACHE["updated"] = time.time()
    return rss

@app.route("/ton.rss")
def ton_rss():
    rss = fetch_and_cache()
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
