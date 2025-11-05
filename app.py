from flask import Flask, Response
import requests
import time
from datetime import datetime, timedelta
import os
from collections import deque

app = Flask(__name__)

# نگهداری 10 آیتم آخر
ITEM_CACHE = deque(maxlen=10)
CACHE = {"updated": 0}

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/toncoin?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
EXCHANGE_URL = "https://api.exchangerate.host/latest?base=USD&symbols=IRR"

RENDER_URL = "https://ton-1-rleg.onrender.com/ton.rss"

def build_item(data, ir_rate):
    now = datetime.utcnow()
    now_str = now.strftime("%a, %d %b %Y %H:%M:%S +0000")

    market_data = data.get("market_data", {})
    usd = market_data.get("current_price", {}).get("usd", 0)
    btc = market_data.get("current_price", {}).get("btc", 0)
    change_1h = market_data.get("price_change_percentage_1h_in_currency", {}).get("usd", 0)
    change_24h = market_data.get("price_change_percentage_24h", 0)
    change_7d = market_data.get("price_change_percentage_7d", 0)
    market_cap = market_data.get("market_cap", {}).get("usd", 0)
    volume_24h = market_data.get("total_volume", {}).get("usd", 0)
    updated_at = market_data.get("last_updated", datetime.utcnow().isoformat())

    # تبدیل last_updated از ISO به timestamp
    try:
        updated_ts = int(datetime.fromisoformat(updated_at.replace("Z","")).timestamp())
    except:
        updated_ts = int(time.time())

    ir = round(usd * ir_rate)

    # زمان به UTC و IRST
    updated_utc = datetime.utcfromtimestamp(updated_ts).strftime("%Y-%m-%d %H:%M:%S UTC")
    iran_offset = timedelta(hours=3, minutes=30)
    updated_iran = (datetime.utcfromtimestamp(updated_ts) + iran_offset).strftime("%Y-%m-%d %H:%M:%S IRST")

    title = f"Toncoin (TON) قیمت: ${usd} | {ir} IRR"
    description = f"""💵 قیمت دلاری: {usd} USD
🇮🇷 قیمت ریالی: {ir} IRR
⏱ آخرین بروزرسانی: {updated_utc} | {updated_iran}
🔺 تغییر 1 ساعته: {change_1h:.2f}%
🔺 تغییر 24 ساعته: {change_24h:.2f}%
🔺 تغییر 7 روزه: {change_7d:.2f}%
💹 قیمت BTC: {btc}
💰 مارکت کپ: ${market_cap:,}
📊 حجم معاملات 24 ساعت: ${volume_24h:,}
🔗 منبع: https://www.coingecko.com/en/coins/toncoin
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
    # کش 60 ثانیه
    if time.time() - CACHE["updated"] < 60:
        return

    # دریافت داده‌ها
    try:
        r = requests.get(COINGECKO_URL, timeout=10)
        data = r.json()
    except:
        data = {"market_data": {}}

    try:
        r2 = requests.get(EXCHANGE_URL, timeout=10)
        ir_rate = r2.json().get("rates", {}).get("IRR", 42000)
    except:
        ir_rate = 42000

    # آیتم جدید
    item = build_item(data, ir_rate)
    ITEM_CACHE.appendleft(item)  # آیتم جدید در اول لیست
    CACHE["updated"] = time.time()

@app.route("/")
def home():
    return """
    <h2>Toncoin RSS Feed حرفه‌ای با آرشیو</h2>
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
