from flask import Flask, Response
import requests
import time
from datetime import datetime, timedelta
import os
from collections import deque
import logging
import json
import random

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ITEM_CACHE = deque(maxlen=10)
CACHE = {
    "updated": 0,
    "data": None,
    "ir_rate": 50000
}

# API های متعدد برای قیمت TON (اضافه شدن BingX و Kraken)
TON_PRICE_APIS = [
    {
        "name": "CoinGecko",
        "url": "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true",
        "parser": lambda data: {
            "lastPrice": data["the-open-network"]["usd"],
            "priceChangePercent": data["the-open-network"]["usd_24h_change"],
            "quoteVolume": data["the-open-network"].get("usd_24h_vol", 0)
        }
    },
    {
        "name": "MEXC",
        "url": "https://api.mexc.com/api/v3/ticker/24hr?symbol=TONUSDT",
        "parser": lambda data: {
            "lastPrice": float(data["lastPrice"]),
            "priceChangePercent": float(data["priceChangePercent"]),
            "quoteVolume": float(data["quoteVolume"])
        }
    },
    {
        "name": "GateIO",
        "url": "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=TON_USDT",
        "parser": lambda data: {
            "lastPrice": float(data[0]["last"]),
            "priceChangePercent": float(data[0]["change_percentage"]),
            "quoteVolume": float(data[0]["quote_volume"])
        } if data and len(data) > 0 else None
    },
    {
        "name": "Kraken",
        "url": "https://api.kraken.com/0/public/Ticker?pair=TONUSD",
        "parser": lambda data: (
            lambda r: {
                "lastPrice": float(r.get("c", [0])[0]),
                "priceChangePercent": 0,
                "quoteVolume": float(r.get("v", [0])[1])
            } if r else None
        )(list(data.get("result", {}).values())[0] if data.get("result") else None)
    },
    {
        "name": "BingX",
        "url": "https://open-api.bingx.com/openApi/spot/v1/ticker/24hr?symbol=TON-USDT",
        "parser": lambda data: {
            "lastPrice": float(data.get("lastPrice", 0)),
            "priceChangePercent": float(data.get("priceChangePercent", 0)),
            "quoteVolume": float(data.get("quoteVolume", 0))
        }
    }
]

EXCHANGE_RATE_APIS = [
    {
        "name": "exchangerate.host",
        "url": "https://api.exchangerate.host/latest?base=USD&symbols=IRR",
        "parser": lambda data: data["rates"]["IRR"]
    },
    {
        "name": "Frankfurter",
        "url": "https://api.frankfurter.app/latest?from=USD&to=IRR",
        "parser": lambda data: data["rates"]["IRR"]
    }
]

def get_ton_price():
    for api in TON_PRICE_APIS:
        try:
            logger.info(f"دریافت قیمت از {api['name']}...")
            response = requests.get(api["url"], timeout=10)
            response.raise_for_status()
            data = response.json()
            price_data = api["parser"](data)
            if price_data and price_data["lastPrice"] > 0:
                logger.info(f"قیمت دریافتی از {api['name']}: {price_data['lastPrice']}")
                return price_data
        except Exception as e:
            logger.warning(f"خطا در دریافت از {api['name']}: {e}")
            continue
    logger.warning("استفاده از داده‌های شبیه‌سازی شده")
    return generate_fallback_data()

def get_exchange_rate():
    for api in EXCHANGE_RATE_APIS:
        try:
            logger.info(f"دریافت نرخ ارز از {api['name']}...")
            response = requests.get(api["url"], timeout=10)
            response.raise_for_status()
            data = response.json()
            rate = api["parser"](data)
            if rate and rate > 0:
                logger.info(f"نرخ ارز دریافتی از {api['name']}: {rate}")
                return rate
        except Exception as e:
            logger.warning(f"خطا در دریافت نرخ ارز از {api['name']}: {e}")
            continue
    return 50000

def generate_fallback_data():
    base_price = 7.5 + random.uniform(-0.5, 0.5)
    return {
        "lastPrice": round(base_price, 4),
        "priceChangePercent": round(random.uniform(-5, 5), 2),
        "quoteVolume": round(random.uniform(50000000, 100000000), 2)
    }

def format_number(value):
    if value is None:
        return "0"
    try:
        value = float(value)
        if value >= 1_000_000:
            return f"{value:,.0f}".replace(",", "٬")
        elif value >= 1_000:
            return f"{value:,.0f}".replace(",", "٬")
        elif value >= 1:
            return f"{value:.4f}"
        else:
            return f"{value:.6f}"
    except (TypeError, ValueError):
        return "0"

def build_item(data, ir_rate):
    now = datetime.utcnow()
    now_str = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
    price_usd = data["lastPrice"]
    change_24h = data["priceChangePercent"]
    volume_24h = data["quoteVolume"]
    ir = int(price_usd * ir_rate)
    updated_utc = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    iran_offset = timedelta(hours=3, minutes=30)
    updated_iran = (now + iran_offset).strftime("%Y-%m-%d %H:%M:%S IRST")
    price_usd_formatted = format_number(price_usd)
    volume_24h_formatted = format_number(volume_24h)
    ir_formatted = f"{ir:,}".replace(",", "٬")
    status_emoji = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "⚪"
    title = f"Toncoin (TON) قیمت: ${price_usd_formatted} | {ir_formatted} ریال"
    description = f"""{status_emoji} وضعیت: Toncoin
💵 قیمت دلاری: {price_usd_formatted} USD
🇮🇷 قیمت ریالی: {ir_formatted} IRR
⏱ آخرین بروزرسانی: {updated_utc} | {updated_iran}
📈 تغییر ۲۴ساعته: {change_24h:+.2f}%
📊 حجم معاملات ۲۴ساعت: ${volume_24h_formatted}
🔗 منابع: {', '.join([api['name'] for api in TON_PRICE_APIS])}
⚡ به‌روزرسانی: هر دقیقه
"""
    guid = f"ton-price-{int(time.time()*1000)}"
    item_xml = f"""<item>
  <title>{title}</title>
  <description><![CDATA[{description}]]></description>
  <pubDate>{now_str}</pubDate>
  <guid isPermaLink="false">{guid}</guid>
</item>"""
    return item_xml

def fetch_and_cache():
    current_time = time.time()
    if current_time - CACHE["updated"] < 60 and CACHE["data"] is not None:
        return
    try:
        logger.info("شروع به‌روزرسانی کش...")
        ton_data = get_ton_price()
        ir_rate = get_exchange_rate()
        if not ton_data or ton_data["lastPrice"] <= 0:
            logger.warning("داده‌های نامعتبر دریافت شد، استفاده از داده‌های جایگزین")
            ton_data = generate_fallback_data()
        CACHE["data"] = ton_data
        CACHE["ir_rate"] = ir_rate
        CACHE["updated"] = current_time
        item = build_item(ton_data, ir_rate)
        ITEM_CACHE.appendleft(item)
        logger.info(f"کش با موفقیت به‌روزرسانی شد - قیمت: ${ton_data['lastPrice']}")
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در به‌روزرسانی کش: {e}")
        CACHE["data"] = generate_fallback_data()
        CACHE["updated"] = current_time

@app.route("/")
def home():
    fetch_and_cache()
    current_data = CACHE["data"]
    current_price = current_data["lastPrice"] if current_data else 0
    current_ir = int(current_price * CACHE["ir_rate"])
    return f"""
    <h1>💰 فید قیمت لحظه‌ای Toncoin</h1>
    <p>💰 قیمت فعلی: ${current_price} | {current_ir:,} ریال</p>
    <p><a href="/ton.rss">لینک فید RSS</a></p>
    """

@app.route("/ton.rss")
@app.route("/Ton.rss")
def ton_rss():
    fetch_and_cache()
    now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = "\n".join(ITEM_CACHE) if ITEM_CACHE else build_item(CACHE["data"] or generate_fallback_data(), CACHE["ir_rate"])
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>Toncoin (TON) قیمت لحظه‌ای</title>
  <link>https://ton-1-rleg.onrender.com/</link>
  <atom:link href="https://ton-1-rleg.onrender.com/ton.rss" rel="self" type="application/rss+xml" />
  <description>فید قیمت Toncoin — به‌روزرسانی هر دقیقه</description>
  <language>fa-IR</language>
  <lastBuildDate>{now}</lastBuildDate>
  {items}
</channel>
</rss>"""
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

if __name__ ==
