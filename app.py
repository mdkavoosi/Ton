from flask import Flask, Response
import time
from datetime import datetime, timedelta
import os
from collections import deque
import logging
import json
import random

app = Flask(__name__)

# تنظیم لاگینگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ITEM_CACHE = deque(maxlen=10)

# داده‌های ثابت برای TON - قیمت واقعی تقریبی
TON_BASE_PRICE = 7.85
IR_BASE_RATE = 50000

CACHE = {
    "updated": 0, 
    "data": {
        "lastPrice": TON_BASE_PRICE,
        "priceChangePercent": 2.34,
        "quoteVolume": 85643210
    }, 
    "ir_rate": IR_BASE_RATE
}

RENDER_URL = "https://ton-1-rleg.onrender.com/ton.rss"

def generate_realistic_data():
    """تولید داده‌های واقع‌بینانه با تغییرات کوچک"""
    base_price = TON_BASE_PRICE
    
    # تغییرات تصادفی کوچک (±2%)
    price_change = random.uniform(-0.02, 0.02)
    new_price = base_price * (1 + price_change)
    
    # تغییرات 24 ساعته (±5%)
    change_24h = random.uniform(-0.05, 0.05)
    
    # حجم معاملات با تغییرات کوچک
    volume_change = random.uniform(-0.1, 0.1)
    new_volume = 85643210 * (1 + volume_change)
    
    # نرخ ارز با تغییرات کوچک
    ir_change = random.uniform(-0.01, 0.01)
    new_ir_rate = IR_BASE_RATE * (1 + ir_change)
    
    return {
        "lastPrice": round(new_price, 4),
        "priceChangePercent": round(change_24h * 100, 2),
        "quoteVolume": round(new_volume, 2)
    }, round(new_ir_rate)

def format_number(value):
    """فرمت اعداد برای نمایش زیباتر"""
    if value is None:
        return "0"
    
    try:
        value = float(value)
        if value >= 1_000_000:
            return f"{value:,.0f}".replace(",", "٬")
        elif value >= 1_000:
            return f"{value:,.0f}".replace(",", "٬")
        elif value >= 1:
            return f"{value:.2f}"
        else:
            return f"{value:.4f}"
    except (TypeError, ValueError):
        return "0"

def build_item(data, ir_rate):
    """ساخت آیتم RSS"""
    now = datetime.utcnow()
    now_str = now.strftime("%a, %d %b %Y %H:%M:%S +0000")

    # استفاده از داده‌های دریافتی
    price_usd = data["lastPrice"]
    change_24h = data["priceChangePercent"]
    volume_24h = data["quoteVolume"]

    # محاسبه قیمت ریالی
    ir = int(price_usd * ir_rate)

    # فرمت‌بندی تاریخ‌ها
    updated_utc = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    iran_offset = timedelta(hours=3, minutes=30)
    updated_iran = (now + iran_offset).strftime("%Y-%m-%d %H:%M:%S IRST")

    # فرمت‌بندی اعداد
    price_usd_formatted = format_number(price_usd)
    volume_24h_formatted = format_number(volume_24h)
    ir_formatted = f"{ir:,}".replace(",", "٬")

    title = f"Toncoin (TON) قیمت: ${price_usd_formatted} | {ir_formatted} ریال"
    
    # ایموجی‌های وضعیت
    status_emoji = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "⚪"
    
    description = f"""{status_emoji} وضعیت: Toncoin
💵 قیمت دلاری: {price_usd_formatted} USD
🇮🇷 قیمت ریالی: {ir_formatted} IRR
⏱ آخرین بروزرسانی: {updated_utc} | {updated_iran}
📈 تغییر ۲۴ساعته: {change_24h:+.2f}%
📊 حجم معاملات ۲۴ساعت: ${volume_24h_formatted}
🔗 منبع: داده‌های شبیه‌سازی شده
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
    """به‌روزرسانی کش با داده‌های شبیه‌سازی شده"""
    current_time = time.time()
    
    # کش برای 30 ثانیه
    if current_time - CACHE["updated"] < 30:
        logger.info("استفاده از داده‌های کش شده")
        return

    try:
        logger.info("تولید داده‌های جدید...")
        
        # تولید داده‌های واقع‌بینانه جدید
        new_data, new_ir_rate = generate_realistic_data()
        
        # به‌روزرسانی کش
        CACHE["data"] = new_data
        CACHE["ir_rate"] = new_ir_rate
        CACHE["updated"] = current_time
        
        # ساخت و اضافه کردن آیتم جدید به کش
        item = build_item(new_data, new_ir_rate)
        ITEM_CACHE.appendleft(item)
        logger.info(f"کش با موفقیت به‌روزرسانی شد - قیمت: ${new_data['lastPrice']}")
        
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در به‌روزرسانی کش: {e}")

@app.route("/")
def home():
    """صفحه اصلی"""
    fetch_and_cache()
    
    current_price = CACHE["data"]["lastPrice"]
    current_ir = int(current_price * CACHE["ir_rate"])
    
    return f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>فید قیمت Toncoin</title>
        <style>
            body {{ font-family: Tahoma, Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .info {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; }}
            .price {{ font-size: 24px; font-weight: bold; color: #28a745; }}
            .status {{ padding: 10px; border-radius: 5px; margin: 10px 0; }}
            .success {{ background: #d4edda; color: #155724; }}
            .warning {{ background: #fff3cd; color: #856404; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💰 فید قیمت لحظه‌ای Toncoin</h1>
            
            <div class="info">
                <div class="price">💰 قیمت فعلی: ${current_price} | {current_ir:,} ریال</div>
                <p>آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="info">
                <p>این سرویس قیمت لحظه‌ای Toncoin را در قالب RSS ارائه می‌دهد.</p>
                <p><strong>لینک فید RSS:</strong> <a href="/ton.rss">/ton.rss</a></p>
                <p><strong>به‌روزرسانی:</strong> هر 30 ثانیه</p>
                <p><strong>داده‌ها:</strong> قیمت دلاری، قیمت ریالی، تغییرات 24 ساعته، حجم معاملات</p>
            </div>
            
            <div class="status success">
                <strong>✅ وضعیت:</strong> سرویس فعال است - داده‌های شبیه‌سازی شده
            </div>
            
            <div class="status warning">
                <strong>📝 توجه:</strong> این سرویس از داده‌های شبیه‌سازی شده استفاده می‌کند
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
  <description>فید قیمت Toncoin — به‌روزرسانی هر 30 ثانیه</description>
  <language>fa-IR</language>
  <lastBuildDate>{now}</lastBuildDate>
  {items}
</channel>
</rss>"""
    
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

@app.route("/status")
def status():
    """صفحه وضعیت سرویس"""
    fetch_and_cache()
    
    status_info = {
        "status": "active",
        "last_update": datetime.fromtimestamp(CACHE["updated"]).isoformat(),
        "cache_size": len(ITEM_CACHE),
        "current_price": CACHE["data"]["lastPrice"],
        "current_irr": int(CACHE["data"]["lastPrice"] * CACHE["ir_rate"]),
        "change_24h": CACHE["data"]["priceChangePercent"],
        "volume": CACHE["data"]["quoteVolume"],
        "ir_rate": CACHE["ir_rate"],
        "data_source": "simulated"
    }
    return Response(json.dumps(status_info, indent=2, ensure_ascii=False), mimetype='application/json')

@app.route("/debug")
def debug():
    """صفحه دیباگ برای بررسی داده‌ها"""
    fetch_and_cache()
    
    debug_info = {
        "cache_updated": CACHE["updated"],
        "cache_data": CACHE["data"],
        "ir_rate": CACHE["ir_rate"],
        "item_cache_size": len(ITEM_CACHE),
        "current_time": time.time(),
        "time_diff": time.time() - CACHE["updated"]
    }
    
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>دیباگ سرویس</title>
        <style>
            body {{ font-family: Tahoma, Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .info {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; }}
            pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            .price {{ color: #28a745; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🐛 صفحه دیباگ سرویس</h1>
            
            <div class="info">
                <h3>💰 قیمت فعلی:</h3>
                <p class="price">${CACHE["data"]["lastPrice"]} | {int(CACHE["data"]["lastPrice"] * CACHE["ir_rate"]):,} ریال</p>
            </div>
            
            <div class="info">
                <h3>داده‌های فعلی:</h3>
                <pre>{json.dumps(debug_info, indent=2, ensure_ascii=False)}</pre>
            </div>
            
            <div class="info">
                <h3>آخرین آیتم RSS:</h3>
                <pre>{list(ITEM_CACHE)[0] if ITEM_CACHE else build_item(CACHE["data"], CACHE["ir_rate"])}</pre>
            </div>
        </div>
    </body>
    </html>
    """
    
    return Response(html, mimetype='text/html; charset=utf-8')

# مقداردهی اولیه
with app.app_context():
    logger.info("مقداردهی اولیه سرویس...")
    # اضافه کردن اولین آیتم به کش
    initial_item = build_item(CACHE["data"], CACHE["ir_rate"])
    ITEM_CACHE.appendleft(initial_item)
    logger.info("سرویس آماده است")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
