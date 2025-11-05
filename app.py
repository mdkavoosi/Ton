https://api.coingecko.com/api/v3/simple/price🔗 منبع: https://www.coingecko.com/en/coins/toncoin
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

    r = requests.get(COINGECKO_URL, params=COINGECKO_PARAMS, timeout=10)
    data = r.json()

    r2 = requests.get(EXCHANGE_URL, timeout=10)
    ir_rate = r2.json().get("rates", {}).get("IRR", 42000)

    rss = build_rss(data, ir_rate)
    CACHE["rss"] = rss
    CACHE["updated"] = time.time()
    return rss

@app.route("/ton.rss")
def ton_rss():
    rss = fetch_and_cache()
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
