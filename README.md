# DistroFlow - Online Distribution Management Software

Complete **Retail + Wholesale** Distribution Management Software.

## Online Host Karne Ka Tarika (Free)

### Method 1: Render.com (Recommended - Free)

1. Jaao: https://render.com → Sign up (GitHub se)
2. **New** → **Web Service**
3. Apna code upload karo (ya GitHub repo connect karo)
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
   - **Instance Type:** Free
5. **Create Web Service** click karo
6. 2-3 minute baad aap ko **live URL** milegi jaise:
   `https://distroflow-xxxx.onrender.com`

Us URL ko browser mein kholo — software online chalega.

---

### Method 2: Railway.app

1. https://railway.app → Login with GitHub
2. **New Project** → Deploy
3. Live URL mil jayegi

---

### Method 3: PythonAnywhere

1. https://www.pythonanywhere.com → Free account
2. Files upload karo
3. Web tab se Flask configure karo

---

## Local Computer Pe Chalane Ke Liye

```bash
cd distroflow_app
pip install -r requirements.txt
python app.py
```

Browser: http://127.0.0.1:5000

## Features

- Dashboard (live stats + charts)
- Products (Add / Edit / Delete)
- Inventory + Stock Adjust
- Sales Orders (Wholesale + Retail)
- Purchase Orders
- Customers (Credit limit + Outstanding)
- Suppliers
- Reports
- Settings
- Real SQLite Database

## Note

Free hosting (Render) pe pehli baar open karne mein 30-50 second lag sakte hain (sleep mode).
