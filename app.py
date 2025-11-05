from flask import Flask, Response
import requests
import time
from datetime import datetime, timedelta
import os
from collections import deque

app = Flask(__name__)

ITEM_CACHE = deque(maxlen=10)
CACHE = {"updated": 0}

# Endpoint ساده CoinGecko برای TON
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd,btc&include_24hr_change=true&include_last_updated_at=true"
EXCHANGE_URL = "https://api.exchangerate.host/latest?base=USD&symbols=IRR"

RENDER_URL = "https://ton-1-rleg.onrender.com/ton.rss"

def build_item(data, ir_rate):
    now = datetime.utcnow()
    now_str = now.strftime("%a, %d %b %Y %H:%M:%S +0000")

    coin = data.get("the-open-network", {})

    usd = coin.get("usd", 0)
    btc = coin.get("btc", 0)
    change_24h = coin.get("usd_24h_change", 0)
    updated_ts = coin.get("last_updated_at", int(time.time()))

    ir = round(usd * ir_rate)

    updated_utc = datetime.utcfromtimestamp(updated_ts).strftime("%Y-%m-%d %H:%M:%S UTC")
    iran_offset = timedelta(hours=3, minutes=30)
    updated_iran = (datetime.utcfromtimestamp(updated_ts) + iran_offset).strftime("%Y-%m-%d %H:%M:%S IRST")

    title = f"Toncoin (TON) قیمت: ${usd} | {ir} ریال"
    description = f"""💵 قیمت دلاری: {usd} USD
🇮🇷 قیمت ریالی: {ir} IRR
⏱ آخرین بروزرسانی: {updated_utc} | {updated_iran}
🔺 تغییر 24ساعته: {change_24h:.2f}%
💹 قیمت BTC: {btc}
🔗 منبع: https://www.coingecko.com/en/coins/the-open-network
"""

    guid = f"ton-{int(time.time()*1000)}"
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
        r = requests.get(COINGECKO_URL, timeout=10)
        data = r.json()
    except:
        data = {"the-open-network": {}}

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
    <h2>Toncoin RSS Feed آماده و صحیح</h2>
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
  <description>فید حرفه‌ای قیمت Toncoin از CoinGecko</description>
  <lastBuildDate>{now}</lastBuildDate>
  {items}
</channel>
</rss>"""
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
