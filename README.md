# ✈️ אל על Price Tracker

סוכן Python שסורק מחירי טיסות אל על לתאילנד ושולח התראות בטלגרם כשהמחיר יורד.

---

## 🚀 הגדרה – שלב אחר שלב

### שלב 1 – צור Bot בטלגרם

1. פתח טלגרם וחפש **@BotFather**
2. שלח `/newbot` ותן לו שם
3. תקבל **TOKEN** – שמור אותו

4. כדי לקבל את ה-**Chat ID** שלך:
   - שלח הודעה לבוט שלך
   - פתח בדפדפן:
     ```
     https://api.telegram.org/bot<TOKEN>/getUpdates
     ```
   - חפש `"chat":{"id":` – זה ה-Chat ID שלך

---

### שלב 2 – צור Repository ב-GitHub

1. לך ל-[github.com/new](https://github.com/new)
2. צור repo חדש (פרטי מומלץ) בשם `elal-price-tracker`
3. העלה את הקבצים:
   ```
   scraper.py
   .github/workflows/price-tracker.yml
   ```

---

### שלב 3 – הוסף Secrets ב-GitHub

לך ל: `Settings → Secrets and variables → Actions`

#### Secrets (מידע רגיש):
| שם | ערך |
|----|-----|
| `TELEGRAM_TOKEN` | הטוקן מ-BotFather |
| `TELEGRAM_CHAT_ID` | ה-Chat ID שלך |

#### Variables (הגדרות):
לך ל: `Settings → Secrets and variables → Actions → Variables`

| שם | ערך (דוגמה) |
|----|-------------|
| `DEPART_DATE` | `2025-11-01` |
| `RETURN_DATE` | `2025-11-15` |

---

### שלב 4 – הרץ ידנית לבדיקה

1. לך ל-`Actions` ב-GitHub
2. בחר `El Al Price Tracker`
3. לחץ `Run workflow`
4. אם הכל תקין – תקבל הודעה בטלגרם! 🎉

---

## ⏱️ תזמון

ברירת המחדל: **פעם בשעה**.

לשינוי ל-30 דקות, ערוך בקובץ ה-workflow:
```yaml
- cron: "*/30 * * * *"
```

---

## 📱 הודעות טלגרם

| מצב | הודעה |
|-----|-------|
| הפעלה ראשונה | מחיר נוכחי + הפעלת המעקב |
| מחיר ירד | 🚨 התראה עם סכום החיסכון + קישור להזמנה |
| מחיר עלה | שקט (שומר מחיר חדש) |
| לא נמצא מחיר | ⚠️ התראת כשל |

---

## 🛠️ שינוי יעד

ברירת מחדל: **TLV → BKK** (בנגקוק)

לשינוי ליעד אחר, ערוך ב-`scraper.py`:
```python
DESTINATION = "HKT"  # פוקט
DESTINATION = "CNX"  # צ'יאנג מאי
```

---

## 🔧 פתרון בעיות

**לא מגיע מחיר?**
- אל על משתמשת ב-JavaScript כבד – ייתכן שה-selectors השתנו
- פתח issue ב-repo או עדכן את `price_selectors` ב-`scraper.py`

**הודעת טלגרם לא מגיעה?**
- ודא ששלחת הודעה ראשונה לבוט שלך לפני שהפעלת את הסורק
- בדוק את ה-`TELEGRAM_CHAT_ID` – חייב להיות מספר (לא שם)
