from flask import Flask, Response
import requests
import time
from datetime import datetime, timedelta
import os
from collections import deque
import logging
import json

app = Flask(__name__)

# تنظیم لاگینگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ITEM_CACHE = deque(maxlen=10)
CACHE = {"updated": 0, "data": None, "ir_rate": 42000}

BINANCE_URL = "https://api.binance.com/api/v3/ticker/24hr?symbol=TONUSDT"
EXCHANGE_URL = "https://api.exchangerate-api.com/v4/latest/USD"  # جایگزین قابل اعتمادتر

RENDER_URL = "https://ton-1-rleg.onrender.com/ton.rss"

def get_binance_data():
    """دریافت داده از Binance با مدیریت خطا"""
    try:
        response = requests.get(BINANCE_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # اعتبارسنجی داده‌های دریافتی
        required_fields = ["lastPrice", "priceChangePercent", "quoteVolume"]
        if all(field in data for field in required_fields):
            return {
                "lastPrice": float(data["lastPrice"]),
                "priceChangePercent": float(data["priceChangePercent"]),
                "quoteVolume": float(data["quoteVolume"])
            }
        else:
            logger.error("داده‌های دریافتی از Binance ناقص است")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"خطا در دریافت داده از Binance: {e}")
        return None
    except (ValueError, KeyError) as e:
        logger.error(f"خطا در پردازش داده‌های Binance: {e}")
        return None

def get_exchange_rate():
    """دریافت نرخ ارز با مدیریت خطا"""
    try:
        response = requests.get(EXCHANGE_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("rates", {}).get("IRR", 42000)
    except requests.exceptions.RequestException as e:
        logger.error(f"خطا در دریافت نرخ ارز: {e}")
        return 42000
    except (ValueError, KeyError) as e:
        logger.error(f"خطا در پردازش نرخ ارز: {e}")
        return 42000

def format_number(value):
    """فرمت اعداد برای نمایش زیباتر"""
    if value >= 1_000_000:
        return f"{value:,.2f}".replace(",", "٬")  # استفاده از جداکننده فارسی
    return f"{value:.4f}"

def build_item(data, ir_rate):
    """ساخت آیتم RSS"""
    now = datetime.utcnow()
    now_str = now.strftime("%a, %d %b %Y %H:%M:%S +0000")

    # استفاده از داده‌های کش شده در صورت خطا
    price_usd = data["lastPrice"] if data else 0
    change_24h = data["priceChangePercent"] if data else 0
    volume_24h = data["quoteVolume"] if data else 0

    # محاسبه قیمت ریالی
    ir = int(price_usd * ir_rate) if price_usd else 0

    # فرمت‌بندی تاریخ‌ها
    updated_utc = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    iran_offset = timedelta(hours=3, minutes=30)
    updated_iran = (now + iran_offset).strftime("%Y-%m-%d %H:%M:%S IRST")

    # فرمت‌بندی اعداد
    price_usd_formatted = format_number(price_usd)
    volume_24h_formatted = format_number(volume_24h)
    ir_formatted = f"{ir:,}".replace(",", "٬")  # جداکننده هزارگان فارسی

    title = f"Toncoin (TON) قیمت: ${price_usd_formatted} | {ir_formatted} ریال"
    
    # ایموجی‌های وضعیت
    status_emoji = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "⚪"
    
    description = f"""{status_emoji} وضعیت: Toncoin
💵 قیمت دلاری: {price_usd_formatted} USD
🇮🇷 قیمت ریالی: {ir_formatted} IRR
⏱ آخرین بروزرسانی: {updated_utc} | {updated_iran}
📈 تغییر ۲۴ساعته: {change_24h:+.2f}%
📊 حجم معاملات ۲۴ساعت: ${volume_24h_formatted}
🔗 منبع: Binance
⚡ به‌روزرسانی: هر دقیقه
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
    """به‌روزرسانی کش با مدیریت خطا"""
    current_time = time.time()
    
    # کش برای 60 ثانیه
    if current_time - CACHE["updated"] < 60 and CACHE["data"] is not None:
        return

    try:
        # دریافت داده‌ها به صورت موازی (در صورت نیاز به بهینه‌سازی بیشتر)
        binance_data = get_binance_data()
        ir_rate = get_exchange_rate()
        
        # استفاده از داده‌های قبلی در صورت خطا
        if binance_data is None and CACHE["data"] is not None:
            binance_data = CACHE["data"]
        
        # به‌روزرسانی کش
        if binance_data is not None:
            CACHE["data"] = binance_data
            CACHE["ir_rate"] = ir_rate
            CACHE["updated"] = current_time
            
            # ساخت و اضافه کردن آیتم جدید به کش
            item = build_item(binance_data, ir_rate)
            ITEM_CACHE.appendleft(item)
            logger.info("کش با موفقیت به‌روزرسانی شد")
        else:
            logger.warning("استفاده از داده‌های کش شده به دلیل خطا در دریافت داده‌های جدید")
            
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در به‌روزرسانی کش: {e}")

@app.route("/")
def home():
    """صفحه اصلی"""
    return """
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>فید قیمت Toncoin</title>
        <style>
            body { font-family: Tahoma, Arial, sans-serif; margin: 40px; line-height: 1.6; }
            .container { max-width: 800px; margin: 0 auto; }
            .info { background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💰 فید قیمت لحظه‌ای Toncoin</h1>
            <div class="info">
                <p>این سرویس قیمت لحظه‌ای Toncoin را از Binance دریافت و در قالب RSS ارائه می‌دهد.</p>
                <p><strong>لینک فید RSS:</strong> <a href="/ton.rss">/ton.rss</a></p>
                <p><strong>به‌روزرسانی:</strong> هر دقیقه</p>
                <p><strong>داده‌ها:</strong> قیمت دلاری، قیمت ریالی، تغییرات 24 ساعته، حجم معاملات</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/ton.rss")
@app.route("/Ton.rss")
def ton_rss():
    """فید RSS"""
    fetch_and_cache()
    
    now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = "\n".join(ITEM_CACHE) if ITEM_CACHE else build_item(CACHE["data"], CACHE["ir_rate"])
    
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>Toncoin (TON) قیمت لحظه‌ای</title>
  <link>https://ton-1-rleg.onrender.com/</link>
  <atom:link href="{RENDER_URL}" rel="self" type="application/rss+xml" />
  <description>فید قیمت Toncoin از Binance — به‌روزرسانی هر دقیقه</description>
  <language>fa-IR</language>
  <lastBuildDate>{now}</lastBuildDate>
  {items}
</channel>
</rss>"""
    
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

@app.route("/status")
def status():
    """صفحه وضعیت سرویس"""
    status_info = {
        "status": "active",
        "last_update": datetime.fromtimestamp(CACHE["updated"]).isoformat() if CACHE["updated"] else "never",
        "cache_size": len(ITEM_CACHE),
        "data_available": CACHE["data"] is not None
    }
    return Response(json.dumps(status_info, indent=2), mimetype='application/json')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
