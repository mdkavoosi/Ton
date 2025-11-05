from flask import Flask, Response
import requests
import time
from datetime import datetime, timedelta
import os
from collections import deque

app = Flask(__name__)

ITEM_CACHE = deque(maxlen=10)
CACHE = {"updated": 0}

BINANCE_URL = "https://api.binance.com/api/v3/ticker/24hr?symbol=TONUSDT"
EXCHANGE_URL = "https://api.exchangerate.host/latest?base=USD&symbols=IRR"

RENDER_URL = "https://ton-1-rleg.onrender.com/ton.rss"

def build_item(data, ir_rate):
    now = datetime.utcnow()
    now_str = now.strftime("%a, %d %b %Y %H:%M:%S +0000")

    # گرفتن داده‌ها از Binance
    price_usd = float(data.get("lastPrice", 0))
    change_24h = float(data.get("priceChangePercent", 0))
    volume_24h = float(data.get("quoteVolume", 0))

    ir = round(price_usd * ir_rate)

    updated_utc = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    iran_offset = timedelta(hours=3, minutes=30)
    updated_iran = (now + iran_offset).strftime("%Y-%m-%d %H:%M:%S IRST")

    title = f"Toncoin (TON) قیمت: ${price_usd} | {ir} ریال"
    description = f"""💵 قیمت دلاری: {price_usd} USD
🇮🇷 قیمت ریالی: {ir} IRR
⏱ آخرین بروزرسانی: {updated_utc} | {updated_iran}
🔺 تغییر ۲۴ساعته: {change_24h}%
📊 حجم معاملات ۲۴ساعت: ${volume_24h}
🔗 منبع: Binance
"""

    guid = f"ton-binance-{int(time.time()*1000)}"
    item_xml = f"""<item>
  <title>{title}</title>
  <description><![CDATA[{description}]]></description>
  <pubDate>{now_str}</pubDate>
  <guid isPermaLink="false">{guid}</guid>
</item>"""

    return item_xml

def fetch_and_cache():
    if time.time() - CACHE["updated"] < 60:
        return

    try:
        r = requests.get(BINANCE_URL, timeout=10)
        data = r.json()
    except:
        data = {"lastPrice": 0, "priceChangePercent": 0, "quoteVolume": 0}

    try:
        r2 = requests.get(EXCHANGE_URL, timeout=10)
        ir_rate = r2.json().get("rates", {}).get("IRR", 42000)
    except:
        ir_rate = 42000

    item = build_item(data, ir_rate)
    ITEM_CACHE.appendleft(item)
    CACHE["updated"] = time.time()

@app.route("/")
def home():
    return """
    <h2>Toncoin RSS Feed با Binance API</h2>
    <p>برای مشاهده فید: <a href="/ton.rss">ton.rss</a></p>
    """

@app.route("/ton.rss")
@app.route("/Ton.rss")
def ton_rss():
    fetch_and_cache()
    now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = "\n".join(ITEM_CACHE)
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>Toncoin (TON) قیمت لحظه‌ای</title>
  <link>https://ton-1-rleg.onrender.com/</link>
  <atom:link href="{RENDER_URL}" rel="self" type="application/rss+xml" />
  <description>فید قیمت Toncoin از Binance — به‌روزرسانی هر دقیقه</description>
  <lastBuildDate>{now}</lastBuildDate>
  {items}
</channel>
</rss>"""
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
