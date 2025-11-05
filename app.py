from flask import Flask, Response
import time
from collections import deque
import threading

app = Flask(__name__)

ITEM_CACHE = deque(maxlen=50)  # نگه داشتن 50 آیتم آخر
COUNTER = 0
LOCK = threading.Lock()

def build_item(number):
    now = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    title = f"شماره {number}"
    description = f"این آیتم شماره {number} است."
    guid = f"counter-{number}-{int(time.time()*1000)}"
    item_xml = f"""<item>
  <title>{title}</title>
  <description><![CDATA[{description}]]></description>
  <pubDate>{now}</pubDate>
  <guid isPermaLink="false">{guid}</guid>
</item>"""
    return item_xml

def increment_counter():
    global COUNTER
    while True:
        with LOCK:
            COUNTER += 1
            ITEM_CACHE.appendleft(build_item(COUNTER))
        time.sleep(10)  # هر ۱۰ ثانیه یک آیتم جدید

# اجرای ترد برای اضافه کردن خودکار آیتم‌ها
threading.Thread(target=increment_counter, daemon=True).start()

@app.route("/")
def home():
    return "<h1>فید شمارنده خودکار آماده است</h1><p><a href='/counter.rss'>لینک فید RSS</a></p>"

@app.route("/counter.rss")
def counter_rss():
    with LOCK:
        items = "\n".join(ITEM_CACHE)
    now = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>فید شمارنده خودکار</title>
  <link>http://localhost:5000/</link>
  <description>فید شمارنده ساده که به‌صورت خودکار هر ۱۰ ثانیه یک عدد اضافه می‌کند</description>
  <language>fa-IR</language>
  <lastBuildDate>{now}</lastBuildDate>
  {items}
</channel>
</rss>"""
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
