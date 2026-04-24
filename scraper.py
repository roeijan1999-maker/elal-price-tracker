import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# ──────────────────────────────────────────────
# הגדרות – שנה כאן לפי הצורך
# ──────────────────────────────────────────────
ORIGIN      = "TLV"          # נמל מוצא
DESTINATION = "BKK"          # בנגקוק (או HKT לפוקט)
DEPART_DATE = os.getenv("DEPART_DATE", "2025-11-01")   # תאריך יציאה
RETURN_DATE = os.getenv("RETURN_DATE", "2025-11-15")   # תאריך חזרה
PASSENGERS  = 1

PRICE_FILE  = Path("last_price.json")
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# ──────────────────────────────────────────────

def build_elal_url():
    """בנה URL לחיפוש באתר אל על"""
    return (
        f"https://www.elal.com/he-il/flights-and-destinations/book-a-flight/"
        f"?origin={ORIGIN}&destination={DESTINATION}"
        f"&departureDate={DEPART_DATE}&returnDate={RETURN_DATE}"
        f"&adults={PASSENGERS}&cabinClass=Economy"
    )


async def scrape_price():
    """סרוק את המחיר הנוכחי מאתר אל על"""
    url = build_elal_url()
    print(f"[{datetime.now():%H:%M:%S}] סורק: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            locale="he-IL",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=60_000, wait_until="networkidle")

            # המתן לטעינת תוצאות
            await page.wait_for_timeout(5000)

            # נסה לאתר מחירים בדף (selectors שונים שאל על משתמש בהם)
            price_selectors = [
                "[data-testid='price']",
                ".price-value",
                ".fare-price",
                "[class*='price']",
                "[class*='Price']",
                "[class*='fare']",
                "span[class*='amount']",
            ]

            price_text = None
            for selector in price_selectors:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        text = await el.inner_text()
                        if any(c.isdigit() for c in text):
                            price_text = text.strip()
                            print(f"  נמצא עם selector: {selector} → {price_text}")
                            break
                except Exception:
                    continue

            if not price_text:
                # נסיון שני: חפש כל טקסט שנראה כמו מחיר (₪ / USD / NIS)
                content = await page.content()
                import re
                matches = re.findall(r"₪\s*[\d,]+|[\d,]+\s*₪|\$\s*[\d,]+", content)
                if matches:
                    price_text = matches[0]
                    print(f"  נמצא בתוכן הדף: {price_text}")

            # חלץ מספר מהטקסט
            if price_text:
                import re
                digits = re.sub(r"[^\d]", "", price_text)
                if digits:
                    price = int(digits)
                    print(f"  מחיר: {price} ₪")
                    return price

            print("  ⚠️  לא נמצא מחיר בדף")
            return None

        except Exception as e:
            print(f"  ❌ שגיאה בסריקה: {e}")
            return None
        finally:
            await browser.close()


def load_last_price():
    """טען את המחיר האחרון שנשמר"""
    if PRICE_FILE.exists():
        data = json.loads(PRICE_FILE.read_text())
        return data.get("price"), data.get("timestamp")
    return None, None


def save_price(price):
    """שמור מחיר חדש"""
    PRICE_FILE.write_text(json.dumps({
        "price": price,
        "timestamp": datetime.now().isoformat(),
        "route": f"{ORIGIN}→{DESTINATION}",
        "dates": f"{DEPART_DATE} / {RETURN_DATE}"
    }, ensure_ascii=False, indent=2))


async def send_telegram(message: str):
    """שלח הודעה לטלגרם"""
    import urllib.request
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        f"?chat_id={TELEGRAM_CHAT_ID}"
        f"&text={urllib.parse.quote(message)}"
        f"&parse_mode=HTML"
    )
    import urllib.parse
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                print("  ✅ הודעת טלגרם נשלחה בהצלחה")
            else:
                print(f"  ❌ שגיאת טלגרם: {result}")
    except Exception as e:
        print(f"  ❌ שגיאה בשליחת טלגרם: {e}")


async def main():
    current_price = await scrape_price()

    if current_price is None:
        print("לא נמצא מחיר – מדלג על השוואה")
        # שלח התראה על כשל אם רוצים
        await send_telegram(
            "⚠️ <b>אל על Price Bot</b>\n"
            f"לא הצלחתי לסרוק מחיר לטיסה {ORIGIN}→{DESTINATION}\n"
            f"תאריכים: {DEPART_DATE} / {RETURN_DATE}"
        )
        sys.exit(0)

    last_price, last_ts = load_last_price()
    print(f"  מחיר קודם: {last_price} ₪ ({last_ts})")
    print(f"  מחיר נוכחי: {current_price} ₪")

    if last_price is None:
        # הפעלה ראשונה – שמור ועדכן
        save_price(current_price)
        msg = (
            f"✈️ <b>אל על Price Bot – הפעלה ראשונה</b>\n\n"
            f"מסלול: {ORIGIN} → {DESTINATION}\n"
            f"יציאה: {DEPART_DATE} | חזרה: {RETURN_DATE}\n"
            f"💰 מחיר נוכחי: <b>{current_price:,} ₪</b>\n\n"
            f"הסוכן יתריע כשהמחיר ירד מרמה זו 🔔"
        )
        await send_telegram(msg)

    elif current_price < last_price:
        diff = last_price - current_price
        pct  = (diff / last_price) * 100
        save_price(current_price)
        msg = (
            f"🚨 <b>ירידת מחיר! אל על {ORIGIN}→{DESTINATION}</b>\n\n"
            f"יציאה: {DEPART_DATE} | חזרה: {RETURN_DATE}\n\n"
            f"📉 מחיר קודם: {last_price:,} ₪\n"
            f"💚 מחיר חדש: <b>{current_price:,} ₪</b>\n"
            f"חיסכון: {diff:,} ₪ ({pct:.1f}%)\n\n"
            f"🔗 <a href='{build_elal_url()}'>לחץ כאן להזמנה</a>"
        )
        await send_telegram(msg)

    elif current_price > last_price:
        diff = current_price - last_price
        print(f"  📈 מחיר עלה ב-{diff:,} ₪ – אין התראה")
        save_price(current_price)

    else:
        print("  ➡️ מחיר לא השתנה – אין התראה")


if __name__ == "__main__":
    asyncio.run(main())
