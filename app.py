
"""
DistroFlow Pro - Advanced Distribution Management Software
"""
import os
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, send_from_directory, g, session
from flask_cors import CORS
from functools import wraps

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = os.environ.get("SECRET_KEY", "distroflow-pro-secret-key-change-me-2026")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False  # True only with custom domain HTTPS strict
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7
CORS(app, supports_credentials=True, origins="*")

DATABASE = os.environ.get("DATABASE_PATH", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "distroflow.db")))

def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def audit(action, entity=None, entity_id=None, details=None):
    try:
        db = get_db()
        db.execute(
            "INSERT INTO audit_logs (user, action, entity, entity_id, details) VALUES (?,?,?,?,?)",
            (session.get("username") or "system", action, entity, entity_id, details)
        )
        db.commit()
    except Exception:
        pass

def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT "admin",
        status TEXT DEFAULT "Active",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT DEFAULT "Grocery",
        unit TEXT DEFAULT "Piece",
        barcode TEXT,
        cost REAL DEFAULT 0,
        wholesale REAL NOT NULL,
        retail REAL NOT NULL,
        stock INTEGER DEFAULT 0,
        min_stock INTEGER DEFAULT 10,
        status TEXT DEFAULT "Active",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        type TEXT DEFAULT "Wholesale",
        phone TEXT,
        city TEXT,
        address TEXT,
        credit_limit REAL DEFAULT 0,
        outstanding REAL DEFAULT 0,
        status TEXT DEFAULT "Active",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        city TEXT,
        outstanding REAL DEFAULT 0,
        status TEXT DEFAULT "Active",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        customer_name TEXT NOT NULL,
        type TEXT DEFAULT "Wholesale",
        subtotal REAL DEFAULT 0,
        tax_rate REAL DEFAULT 0,
        tax_amount REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        amount REAL NOT NULL,
        paid REAL DEFAULT 0,
        status TEXT DEFAULT "Pending",
        payment_status TEXT DEFAULT "Unpaid",
        notes TEXT,
        order_date TEXT NOT NULL,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        sku TEXT,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_no TEXT UNIQUE NOT NULL,
        supplier_id INTEGER,
        supplier_name TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT "Pending",
        notes TEXT,
        order_date TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS purchase_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_cost REAL NOT NULL,
        total REAL NOT NULL,
        FOREIGN KEY (purchase_id) REFERENCES purchases(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        customer_name TEXT,
        sale_id INTEGER,
        amount REAL NOT NULL,
        method TEXT DEFAULT "Cash",
        notes TEXT,
        payment_date TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        product_name TEXT,
        type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        reference TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS sale_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        return_no TEXT UNIQUE NOT NULL,
        sale_id INTEGER,
        order_no TEXT,
        customer_id INTEGER,
        customer_name TEXT,
        amount REAL DEFAULT 0,
        reason TEXT,
        status TEXT DEFAULT "Completed",
        return_date TEXT NOT NULL,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS return_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        return_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT DEFAULT "General",
        amount REAL NOT NULL,
        expense_date TEXT NOT NULL,
        notes TEXT,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS quotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_no TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        customer_name TEXT NOT NULL,
        subtotal REAL DEFAULT 0,
        tax_rate REAL DEFAULT 0,
        tax_amount REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        amount REAL NOT NULL,
        status TEXT DEFAULT "Draft",
        notes TEXT,
        quote_date TEXT NOT NULL,
        valid_until TEXT,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS quote_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS warehouses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT,
        status TEXT DEFAULT "Active"
    );
    
    CREATE TABLE IF NOT EXISTS warehouse_stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        warehouse_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 0,
        UNIQUE(warehouse_id, product_id)
    );
    CREATE TABLE IF NOT EXISTS stock_transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transfer_no TEXT UNIQUE,
        from_warehouse_id INTEGER,
        to_warehouse_id INTEGER,
        product_id INTEGER,
        product_name TEXT,
        quantity INTEGER,
        notes TEXT,
        transfer_date TEXT,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER,
        order_no TEXT,
        customer_name TEXT,
        driver_name TEXT,
        vehicle TEXT,
        status TEXT DEFAULT "Pending",
        delivery_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS branches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        city TEXT,
        phone TEXT,
        status TEXT DEFAULT "Active"
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT NOT NULL,
        entity TEXT,
        entity_id INTEGER,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    """)
    db.commit()

    if not db.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        db.execute("INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,?)",
                   ("admin", hash_password("admin123"), "Administrator", "admin"))
        db.execute("INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,?)",
                   ("sales", hash_password("sales123"), "Sales Person", "sales"))
        db.commit()

    if db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        seed_data(db)

def seed_data(db):
    products = [
        ("PRD-001","Premium Basmati Rice 5kg","Grocery","Bag","8901001",1200,1350,1500,120,50),
        ("PRD-002","Sunflower Oil 1L","Grocery","Bottle","8901002",980,1100,1200,85,40),
        ("PRD-003","Detergent Powder 1kg","Household","Pack","8901003",450,520,600,45,50),
        ("PRD-004","Green Tea Bags 100s","Beverages","Box","8901004",480,550,650,210,30),
        ("PRD-005","Wheat Flour 10kg","Grocery","Bag","8901005",1250,1400,1550,67,40),
        ("PRD-006","Hand Wash 500ml","Personal Care","Bottle","8901006",220,280,350,18,25),
        ("PRD-007","Toothpaste 150g","Personal Care","Tube","8901007",180,220,280,95,30),
        ("PRD-008","Sugar 5kg","Grocery","Bag","8901008",850,950,1050,140,60),
        ("PRD-009","Cooking Oil 5L","Grocery","Can","8901009",2800,3100,3400,55,20),
        ("PRD-010","Soap Bar 3-Pack","Personal Care","Pack","8901010",150,180,220,200,40),
        ("PRD-011","Milk Powder 400g","Grocery","Tin","8901011",650,720,850,90,25),
        ("PRD-012","Biscuits Family Pack","Grocery","Pack","8901012",280,320,380,150,40),
    ]
    db.executemany("INSERT INTO products (sku,name,category,unit,barcode,cost,wholesale,retail,stock,min_stock) VALUES (?,?,?,?,?,?,?,?,?,?)", products)

    customers = [
        ("CUS-001","Al-Madina Store","Wholesale","0300-1234567","Lahore","Main Bazaar",500000,125000),
        ("CUS-002","City Mart","Wholesale","0321-9876543","Karachi","Saddar",300000,45000),
        ("CUS-003","Khan Traders","Wholesale","0333-5556677","Islamabad","Blue Area",750000,215000),
        ("CUS-004","Super Value","Wholesale","0312-4445566","Faisalabad","Clock Tower",400000,0),
        ("CUS-005","Ahmed General Store","Retail","0301-7788990","Lahore","Model Town",50000,12000),
        ("CUS-006","Bismillah Mart","Wholesale","0345-1122334","Multan","Cantt",250000,89000),
        ("CUS-007","Family Superstore","Wholesale","0302-6677889","Rawalpindi","Saddar",350000,56000),
        ("CUS-008","Walk-in Counter","Retail","","Local","",0,0),
    ]
    db.executemany("INSERT INTO customers (code,name,type,phone,city,address,credit_limit,outstanding) VALUES (?,?,?,?,?,?,?,?)", customers)

    suppliers = [
        ("SUP-001","National Foods Ltd","042-111222333","Lahore",450000),
        ("SUP-002","Unilever Pakistan","021-333444555","Karachi",280000),
        ("SUP-003","Dalda Foods","042-555666777","Lahore",125000),
        ("SUP-004","Shan Foods","021-777888999","Karachi",0),
        ("SUP-005","Tapal Tea","021-222333444","Karachi",95000),
        ("SUP-006","Nestle Pakistan","021-111000111","Karachi",320000),
    ]
    db.executemany("INSERT INTO suppliers (code,name,phone,city,outstanding) VALUES (?,?,?,?,?)", suppliers)

    settings = [
        ("company_name","DistroFlow Traders"),
        ("business_type","Wholesale & Retail"),
        ("phone","042-1234567"),
        ("email","info@distroflow.com"),
        ("address","123 Business Avenue, Lahore, Pakistan"),
        ("currency","PKR"),
        ("tax_rate","18"),
    ]
    db.executemany("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", settings)
    if db.execute("SELECT COUNT(*) FROM warehouses").fetchone()[0] == 0:
        db.execute("INSERT INTO warehouses (name, location) VALUES (?,?)", ("Main Warehouse", "Lahore"))
        db.execute("INSERT INTO warehouses (name, location) VALUES (?,?)", ("Secondary Godown", "Karachi"))
    if db.execute("SELECT COUNT(*) FROM branches").fetchone()[0] == 0:
        db.execute("INSERT INTO branches (name, city, phone) VALUES (?,?,?)", ("Main Branch", "Lahore", "042-1234567"))
    db.commit()


@app.route("/api/health")
def health():
    db = get_db()
    users = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    return jsonify({"ok": True, "users": users, "message": "DistroFlow Pro running"})

@app.route("/api/setup", methods=["POST"])
def setup_admin():
    """Ensure default admin exists (safe to call anytime)."""
    db = get_db()
    user = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not user:
        db.execute("INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,?)",
                   ("admin", hash_password("admin123"), "Administrator", "admin"))
        db.commit()
        return jsonify({"ok": True, "created": True, "message": "Admin created: admin / admin123"})
    # Reset password option
    data = request.json or {}
    if data.get("reset") is True:
        db.execute("UPDATE users SET password=? WHERE username='admin'", (hash_password("admin123"),))
        db.commit()
        return jsonify({"ok": True, "reset": True, "message": "Admin password reset to admin123"})
    return jsonify({"ok": True, "created": False, "message": "Admin already exists"})


# ---- AUTH ----
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND status='Active'", (username,)).fetchone()
    if user and user["password"] == hash_password(password):
        session.permanent = True
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]
        return jsonify({"ok": True, "user": {"id": user["id"], "username": user["username"], "full_name": user["full_name"], "role": user["role"]}})
    return jsonify({"error": "Invalid username or password"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/me")
def me():
    if not session.get("user_id"):
        return jsonify({"user": None})
    return jsonify({"user": {"id": session["user_id"], "username": session.get("username"), "full_name": session.get("full_name"), "role": session.get("role")}})

# ---- DASHBOARD ----
@app.route("/api/dashboard")
def dashboard():
    db = get_db()
    today = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()
    today_sales = db.execute("SELECT COALESCE(SUM(amount),0) as total, COUNT(*) as count FROM sales WHERE order_date=?", (today,)).fetchone()
    month_sales = db.execute("SELECT COALESCE(SUM(amount),0) as total FROM sales WHERE order_date>=?", (month_start,)).fetchone()["total"]
    pending = db.execute("SELECT COUNT(*) as c FROM sales WHERE status IN ('Pending','Processing')").fetchone()["c"]
    low_stock = db.execute("SELECT COUNT(*) as c FROM products WHERE stock <= min_stock AND status='Active'").fetchone()["c"]
    outstanding = db.execute("SELECT COALESCE(SUM(outstanding),0) as t FROM customers").fetchone()["t"]
    unpaid = db.execute("SELECT COALESCE(SUM(amount-paid),0) as t FROM sales WHERE payment_status != 'Paid'").fetchone()["t"]
    total_products = db.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
    total_customers = db.execute("SELECT COUNT(*) as c FROM customers").fetchone()["c"]
    recent = rows_to_list(db.execute("SELECT * FROM sales ORDER BY id DESC LIMIT 8").fetchall())
    top_products = rows_to_list(db.execute("SELECT id, sku, name, stock, wholesale, (stock*wholesale) as value FROM products ORDER BY value DESC LIMIT 5").fetchall())
    low_stock_items = rows_to_list(db.execute("SELECT id, sku, name, stock, min_stock FROM products WHERE stock <= min_stock ORDER BY stock ASC LIMIT 5").fetchall())
    days = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        row = db.execute("SELECT COALESCE(SUM(amount),0) as total FROM sales WHERE order_date=?", (d,)).fetchone()
        days.append({"date": d, "amount": row["total"]})
    return jsonify({
        "today_sales": today_sales["total"], "today_orders": today_sales["count"],
        "month_sales": month_sales, "pending_orders": pending, "low_stock": low_stock,
        "outstanding": outstanding, "unpaid": unpaid, "total_products": total_products,
        "total_customers": total_customers, "recent_orders": recent, "top_products": top_products,
        "low_stock_items": low_stock_items, "sales_trend": days,
    })

# ---- PRODUCTS ----
@app.route("/api/products", methods=["GET"])
def get_products():
    db = get_db()
    q = request.args.get("q", "").strip()
    if q:
        rows = db.execute("SELECT * FROM products WHERE name LIKE ? OR sku LIKE ? OR barcode LIKE ? ORDER BY name", (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    else:
        rows = db.execute("SELECT * FROM products ORDER BY name").fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/products", methods=["POST"])
def create_product():
    data = request.json or {}
    db = get_db()
    sku = data.get("sku") or f"PRD-{datetime.now().strftime('%H%M%S')}"
    try:
        cur = db.execute(
            "INSERT INTO products (sku,name,category,unit,barcode,cost,wholesale,retail,stock,min_stock) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sku, data["name"], data.get("category","Grocery"), data.get("unit","Piece"), data.get("barcode",""),
             data.get("cost",0), data["wholesale"], data["retail"], data.get("stock",0), data.get("min_stock",10))
        )
        db.commit()
        return jsonify(row_to_dict(db.execute("SELECT * FROM products WHERE id=?", (cur.lastrowid,)).fetchone())), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "SKU already exists"}), 400
    except KeyError as e:
        return jsonify({"error": f"Missing: {e}"}), 400

@app.route("/api/products/<int:pid>", methods=["PUT"])
def update_product(pid):
    data = request.json or {}
    db = get_db()
    db.execute(
        "UPDATE products SET name=?, category=?, unit=?, barcode=?, cost=?, wholesale=?, retail=?, stock=?, min_stock=?, status=? WHERE id=?",
        (data.get("name"), data.get("category"), data.get("unit"), data.get("barcode"), data.get("cost"),
         data.get("wholesale"), data.get("retail"), data.get("stock"), data.get("min_stock"), data.get("status","Active"), pid)
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()))

@app.route("/api/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    db = get_db()
    db.execute("DELETE FROM products WHERE id=?", (pid,))
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/products/<int:pid>/stock", methods=["POST"])
def adjust_stock(pid):
    data = request.json or {}
    new_stock = int(data.get("stock", 0))
    notes = data.get("notes", "")
    db = get_db()
    prod = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not prod:
        return jsonify({"error": "Not found"}), 404
    old = prod["stock"]
    db.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, pid))
    db.execute("INSERT INTO stock_movements (product_id, product_name, type, quantity, notes) VALUES (?,?,?,?,?)",
               (pid, prod["name"], "Adjustment", new_stock - old, notes))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()))

# ---- CUSTOMERS ----
@app.route("/api/customers", methods=["GET"])
def get_customers():
    db = get_db()
    q = request.args.get("q", "").strip()
    if q:
        rows = db.execute("SELECT * FROM customers WHERE name LIKE ? OR code LIKE ? OR phone LIKE ? ORDER BY name", (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    else:
        rows = db.execute("SELECT * FROM customers ORDER BY name").fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/customers", methods=["POST"])
def create_customer():
    data = request.json or {}
    db = get_db()
    code = data.get("code") or f"CUS-{datetime.now().strftime('%H%M%S')}"
    cur = db.execute(
        "INSERT INTO customers (code,name,type,phone,city,address,credit_limit,outstanding) VALUES (?,?,?,?,?,?,?,?)",
        (code, data["name"], data.get("type","Wholesale"), data.get("phone",""), data.get("city",""),
         data.get("address",""), data.get("credit_limit",0), data.get("outstanding",0))
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM customers WHERE id=?", (cur.lastrowid,)).fetchone())), 201

@app.route("/api/customers/<int:cid>", methods=["PUT"])
def update_customer(cid):
    data = request.json or {}
    db = get_db()
    db.execute(
        "UPDATE customers SET name=?, type=?, phone=?, city=?, address=?, credit_limit=?, outstanding=?, status=? WHERE id=?",
        (data.get("name"), data.get("type"), data.get("phone"), data.get("city"), data.get("address"),
         data.get("credit_limit"), data.get("outstanding"), data.get("status","Active"), cid)
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()))

@app.route("/api/customers/<int:cid>", methods=["DELETE"])
def delete_customer(cid):
    db = get_db()
    db.execute("DELETE FROM customers WHERE id=?", (cid,))
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/customers/<int:cid>/ledger")
def customer_ledger(cid):
    db = get_db()
    customer = row_to_dict(db.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone())
    sales = rows_to_list(db.execute("SELECT * FROM sales WHERE customer_id=? ORDER BY order_date DESC", (cid,)).fetchall())
    payments = rows_to_list(db.execute("SELECT * FROM payments WHERE customer_id=? ORDER BY payment_date DESC", (cid,)).fetchall())
    return jsonify({"customer": customer, "sales": sales, "payments": payments})

# ---- SUPPLIERS ----
@app.route("/api/suppliers", methods=["GET"])
def get_suppliers():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM suppliers ORDER BY name").fetchall()))

@app.route("/api/suppliers", methods=["POST"])
def create_supplier():
    data = request.json or {}
    db = get_db()
    code = data.get("code") or f"SUP-{datetime.now().strftime('%H%M%S')}"
    cur = db.execute("INSERT INTO suppliers (code,name,phone,city,outstanding) VALUES (?,?,?,?,?)",
                     (code, data["name"], data.get("phone",""), data.get("city",""), data.get("outstanding",0)))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM suppliers WHERE id=?", (cur.lastrowid,)).fetchone())), 201

@app.route("/api/suppliers/<int:sid>", methods=["PUT"])
def update_supplier(sid):
    data = request.json or {}
    db = get_db()
    db.execute("UPDATE suppliers SET name=?, phone=?, city=?, outstanding=?, status=? WHERE id=?",
               (data.get("name"), data.get("phone"), data.get("city"), data.get("outstanding"), data.get("status","Active"), sid))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM suppliers WHERE id=?", (sid,)).fetchone()))

@app.route("/api/suppliers/<int:sid>", methods=["DELETE"])
def delete_supplier(sid):
    db = get_db()
    db.execute("DELETE FROM suppliers WHERE id=?", (sid,))
    db.commit()
    return jsonify({"ok": True})

# ---- SALES WITH LINE ITEMS ----
@app.route("/api/sales", methods=["GET"])
def get_sales():
    db = get_db()
    q = request.args.get("q", "").strip()
    if q:
        rows = db.execute("SELECT * FROM sales WHERE order_no LIKE ? OR customer_name LIKE ? ORDER BY id DESC", (f"%{q}%", f"%{q}%")).fetchall()
    else:
        rows = db.execute("SELECT * FROM sales ORDER BY id DESC LIMIT 100").fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/sales/<int:sid>")
def get_sale(sid):
    db = get_db()
    sale = row_to_dict(db.execute("SELECT * FROM sales WHERE id=?", (sid,)).fetchone())
    if not sale:
        return jsonify({"error": "Not found"}), 404
    sale["items"] = rows_to_list(db.execute("SELECT * FROM sale_items WHERE sale_id=?", (sid,)).fetchall())
    return jsonify(sale)

@app.route("/api/sales", methods=["POST"])
def create_sale():
    data = request.json or {}
    db = get_db()
    items = data.get("items", [])
    if not items:
        return jsonify({"error": "Add at least one product"}), 400

    last = db.execute("SELECT order_no FROM sales ORDER BY id DESC LIMIT 1").fetchone()
    num = int(last["order_no"].replace("SO-", "")) + 1 if last else 1001
    order_no = f"SO-{num}"

    subtotal = sum(float(i["quantity"]) * float(i["unit_price"]) for i in items)
    tax_rate = float(data.get("tax_rate", 0))
    discount = float(data.get("discount", 0))
    tax_amount = round(subtotal * tax_rate / 100, 2)
    amount = round(subtotal + tax_amount - discount, 2)
    paid = float(data.get("paid", 0))
    payment_status = "Paid" if paid >= amount else ("Partial" if paid > 0 else "Unpaid")

    cur = db.execute(
        """INSERT INTO sales (order_no, customer_id, customer_name, type, subtotal, tax_rate, tax_amount,
           discount, amount, paid, status, payment_status, notes, order_date, created_by)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (order_no, data.get("customer_id"), data["customer_name"], data.get("type", "Wholesale"),
         subtotal, tax_rate, tax_amount, discount, amount, paid,
         data.get("status", "Completed"), payment_status, data.get("notes", ""),
         data.get("order_date", date.today().isoformat()), session.get("username", "admin"))
    )
    sale_id = cur.lastrowid

    for item in items:
        db.execute(
            "INSERT INTO sale_items (sale_id, product_id, product_name, sku, quantity, unit_price, total) VALUES (?,?,?,?,?,?,?)",
            (sale_id, item.get("product_id"), item["product_name"], item.get("sku", ""),
             item["quantity"], item["unit_price"], float(item["quantity"]) * float(item["unit_price"]))
        )
        if item.get("product_id"):
            db.execute("UPDATE products SET stock = stock - ? WHERE id=?", (item["quantity"], item["product_id"]))
            db.execute("INSERT INTO stock_movements (product_id, product_name, type, quantity, reference) VALUES (?,?,?,?,?)",
                       (item["product_id"], item["product_name"], "Sale", -int(item["quantity"]), order_no))

    if data.get("customer_id") and paid < amount:
        db.execute("UPDATE customers SET outstanding = outstanding + ? WHERE id=?", (amount - paid, data["customer_id"]))

    if paid > 0:
        db.execute(
            "INSERT INTO payments (customer_id, customer_name, sale_id, amount, method, payment_date) VALUES (?,?,?,?,?,?)",
            (data.get("customer_id"), data["customer_name"], sale_id, paid, data.get("payment_method", "Cash"), date.today().isoformat())
        )

    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone())), 201

@app.route("/api/sales/<int:sid>", methods=["PUT"])
def update_sale(sid):
    data = request.json or {}
    db = get_db()
    db.execute("UPDATE sales SET status=?, notes=? WHERE id=?", (data.get("status"), data.get("notes"), sid))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM sales WHERE id=?", (sid,)).fetchone()))

@app.route("/api/sales/<int:sid>", methods=["DELETE"])
def delete_sale(sid):
    db = get_db()
    db.execute("DELETE FROM sale_items WHERE sale_id=?", (sid,))
    db.execute("DELETE FROM sales WHERE id=?", (sid,))
    db.commit()
    return jsonify({"ok": True})

# ---- PAYMENTS ----
@app.route("/api/payments", methods=["GET"])
def get_payments():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM payments ORDER BY id DESC LIMIT 50").fetchall()))

@app.route("/api/payments", methods=["POST"])
def create_payment():
    data = request.json or {}
    db = get_db()
    amount = float(data["amount"])
    customer_id = data.get("customer_id")
    sale_id = data.get("sale_id")
    db.execute(
        "INSERT INTO payments (customer_id, customer_name, sale_id, amount, method, notes, payment_date) VALUES (?,?,?,?,?,?,?)",
        (customer_id, data.get("customer_name"), sale_id, amount, data.get("method", "Cash"), data.get("notes", ""),
         data.get("payment_date", date.today().isoformat()))
    )
    if customer_id:
        db.execute("UPDATE customers SET outstanding = MAX(0, outstanding - ?) WHERE id=?", (amount, customer_id))
    if sale_id:
        sale = db.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
        if sale:
            new_paid = sale["paid"] + amount
            payment_status = "Paid" if new_paid >= sale["amount"] else "Partial"
            db.execute("UPDATE sales SET paid=?, payment_status=? WHERE id=?", (new_paid, payment_status, sale_id))
    db.commit()
    return jsonify({"ok": True}), 201

# ---- PURCHASES ----
@app.route("/api/purchases", methods=["GET"])
def get_purchases():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM purchases ORDER BY id DESC").fetchall()))

@app.route("/api/purchases", methods=["POST"])
def create_purchase():
    data = request.json or {}
    db = get_db()
    items = data.get("items", [])
    last = db.execute("SELECT po_no FROM purchases ORDER BY id DESC LIMIT 1").fetchone()
    num = int(last["po_no"].replace("PO-", "")) + 1 if last else 4501
    po_no = f"PO-{num}"
    amount = sum(float(i["quantity"]) * float(i["unit_cost"]) for i in items) if items else float(data.get("amount", 0))
    cur = db.execute(
        "INSERT INTO purchases (po_no, supplier_id, supplier_name, amount, status, notes, order_date) VALUES (?,?,?,?,?,?,?)",
        (po_no, data.get("supplier_id"), data["supplier_name"], amount, data.get("status", "Pending"),
         data.get("notes", ""), data.get("order_date", date.today().isoformat()))
    )
    purchase_id = cur.lastrowid
    for item in items:
        db.execute(
            "INSERT INTO purchase_items (purchase_id, product_id, product_name, quantity, unit_cost, total) VALUES (?,?,?,?,?,?)",
            (purchase_id, item.get("product_id"), item["product_name"], item["quantity"], item["unit_cost"],
             float(item["quantity"]) * float(item["unit_cost"]))
        )
        if item.get("product_id") and data.get("status") == "Received":
            db.execute("UPDATE products SET stock = stock + ? WHERE id=?", (item["quantity"], item["product_id"]))
            db.execute("INSERT INTO stock_movements (product_id, product_name, type, quantity, reference) VALUES (?,?,?,?,?)",
                       (item["product_id"], item["product_name"], "Purchase", int(item["quantity"]), po_no))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM purchases WHERE id=?", (purchase_id,)).fetchone())), 201

@app.route("/api/purchases/<int:pid>", methods=["PUT"])
def update_purchase(pid):
    data = request.json or {}
    db = get_db()
    old = db.execute("SELECT * FROM purchases WHERE id=?", (pid,)).fetchone()
    db.execute("UPDATE purchases SET status=?, notes=? WHERE id=?", (data.get("status"), data.get("notes"), pid))
    if data.get("status") == "Received" and old and old["status"] != "Received":
        items = db.execute("SELECT * FROM purchase_items WHERE purchase_id=?", (pid,)).fetchall()
        for item in items:
            if item["product_id"]:
                db.execute("UPDATE products SET stock = stock + ? WHERE id=?", (item["quantity"], item["product_id"]))
                db.execute("INSERT INTO stock_movements (product_id, product_name, type, quantity, reference) VALUES (?,?,?,?,?)",
                           (item["product_id"], item["product_name"], "Purchase", item["quantity"], old["po_no"]))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM purchases WHERE id=?", (pid,)).fetchone()))

@app.route("/api/purchases/<int:pid>", methods=["DELETE"])
def delete_purchase(pid):
    db = get_db()
    db.execute("DELETE FROM purchase_items WHERE purchase_id=?", (pid,))
    db.execute("DELETE FROM purchases WHERE id=?", (pid,))
    db.commit()
    return jsonify({"ok": True})

# ---- STOCK MOVEMENTS ----
@app.route("/api/stock-movements")
def stock_movements():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM stock_movements ORDER BY id DESC LIMIT 50").fetchall()))

# ---- SETTINGS ----
@app.route("/api/settings", methods=["GET"])
def get_settings():
    db = get_db()
    rows = db.execute("SELECT * FROM settings").fetchall()
    return jsonify({r["key"]: r["value"] for r in rows})

@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.json or {}
    db = get_db()
    for k, v in data.items():
        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (k, str(v)))
    db.commit()
    return jsonify({"ok": True})

# ---- REPORTS ----
@app.route("/api/reports/summary")
def report_summary():
    db = get_db()
    from_date = request.args.get("from", (date.today() - timedelta(days=30)).isoformat())
    to_date = request.args.get("to", date.today().isoformat())
    sales = db.execute("SELECT COALESCE(SUM(amount),0) as total, COUNT(*) as count FROM sales WHERE order_date BETWEEN ? AND ?", (from_date, to_date)).fetchone()
    purchases = db.execute("SELECT COALESCE(SUM(amount),0) as total, COUNT(*) as count FROM purchases WHERE order_date BETWEEN ? AND ?", (from_date, to_date)).fetchone()
    payments = db.execute("SELECT COALESCE(SUM(amount),0) as total FROM payments WHERE payment_date BETWEEN ? AND ?", (from_date, to_date)).fetchone()
    by_type = rows_to_list(db.execute("SELECT type, SUM(amount) as total, COUNT(*) as count FROM sales WHERE order_date BETWEEN ? AND ? GROUP BY type", (from_date, to_date)).fetchall())
    top_customers = rows_to_list(db.execute(
        "SELECT customer_name, SUM(amount) as total, COUNT(*) as orders FROM sales WHERE order_date BETWEEN ? AND ? GROUP BY customer_name ORDER BY total DESC LIMIT 10",
        (from_date, to_date)).fetchall())
    return jsonify({
        "from": from_date, "to": to_date,
        "sales_total": sales["total"], "sales_count": sales["count"],
        "purchases_total": purchases["total"], "purchases_count": purchases["count"],
        "payments_total": payments["total"], "by_type": by_type, "top_customers": top_customers,
    })



# ---- RETURNS ----
@app.route("/api/returns", methods=["GET"])
def get_returns():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM sale_returns ORDER BY id DESC LIMIT 100").fetchall()))

@app.route("/api/returns", methods=["POST"])
def create_return():
    data = request.json or {}
    db = get_db()
    items = data.get("items", [])
    last = db.execute("SELECT return_no FROM sale_returns ORDER BY id DESC LIMIT 1").fetchone()
    num = int(last["return_no"].replace("RT-", "")) + 1 if last else 1001
    return_no = f"RT-{num}"
    amount = sum(float(i["quantity"]) * float(i["unit_price"]) for i in items) if items else float(data.get("amount", 0))
    cur = db.execute(
        """INSERT INTO sale_returns (return_no, sale_id, order_no, customer_id, customer_name, amount, reason, status, return_date, created_by)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (return_no, data.get("sale_id"), data.get("order_no"), data.get("customer_id"), data.get("customer_name", ""),
         amount, data.get("reason", ""), "Completed", data.get("return_date", date.today().isoformat()), session.get("username", "admin"))
    )
    rid = cur.lastrowid
    for item in items:
        db.execute(
            "INSERT INTO return_items (return_id, product_id, product_name, quantity, unit_price, total) VALUES (?,?,?,?,?,?)",
            (rid, item.get("product_id"), item["product_name"], item["quantity"], item["unit_price"], float(item["quantity"]) * float(item["unit_price"]))
        )
        if item.get("product_id"):
            db.execute("UPDATE products SET stock = stock + ? WHERE id=?", (item["quantity"], item["product_id"]))
            db.execute("INSERT INTO stock_movements (product_id, product_name, type, quantity, reference) VALUES (?,?,?,?,?)",
                       (item["product_id"], item["product_name"], "Return", int(item["quantity"]), return_no))
    if data.get("customer_id") and amount:
        db.execute("UPDATE customers SET outstanding = MAX(0, outstanding - ?) WHERE id=?", (amount, data["customer_id"]))
    audit("create_return", "sale_returns", rid, return_no)
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM sale_returns WHERE id=?", (rid,)).fetchone())), 201

# ---- EXPENSES ----
@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 100").fetchall()))

@app.route("/api/expenses", methods=["POST"])
def create_expense():
    data = request.json or {}
    db = get_db()
    cur = db.execute(
        "INSERT INTO expenses (title, category, amount, expense_date, notes, created_by) VALUES (?,?,?,?,?,?)",
        (data["title"], data.get("category", "General"), float(data["amount"]),
         data.get("expense_date", date.today().isoformat()), data.get("notes", ""), session.get("username", "admin"))
    )
    audit("create_expense", "expenses", cur.lastrowid, data.get("title"))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM expenses WHERE id=?", (cur.lastrowid,)).fetchone())), 201

@app.route("/api/expenses/<int:eid>", methods=["DELETE"])
def delete_expense(eid):
    db = get_db()
    db.execute("DELETE FROM expenses WHERE id=?", (eid,))
    db.commit()
    return jsonify({"ok": True})

# ---- QUOTATIONS ----
@app.route("/api/quotations", methods=["GET"])
def get_quotations():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM quotations ORDER BY id DESC LIMIT 100").fetchall()))

@app.route("/api/quotations/<int:qid>")
def get_quotation(qid):
    db = get_db()
    q = row_to_dict(db.execute("SELECT * FROM quotations WHERE id=?", (qid,)).fetchone())
    if not q:
        return jsonify({"error": "Not found"}), 404
    q["items"] = rows_to_list(db.execute("SELECT * FROM quote_items WHERE quote_id=?", (qid,)).fetchall())
    return jsonify(q)

@app.route("/api/quotations", methods=["POST"])
def create_quotation():
    data = request.json or {}
    db = get_db()
    items = data.get("items", [])
    last = db.execute("SELECT quote_no FROM quotations ORDER BY id DESC LIMIT 1").fetchone()
    num = int(last["quote_no"].replace("QT-", "")) + 1 if last else 1001
    quote_no = f"QT-{num}"
    subtotal = sum(float(i["quantity"]) * float(i["unit_price"]) for i in items) if items else float(data.get("amount", 0))
    tax_rate = float(data.get("tax_rate", 0))
    discount = float(data.get("discount", 0))
    tax_amount = round(subtotal * tax_rate / 100, 2)
    amount = round(subtotal + tax_amount - discount, 2)
    cur = db.execute(
        """INSERT INTO quotations (quote_no, customer_id, customer_name, subtotal, tax_rate, tax_amount, discount, amount, status, notes, quote_date, valid_until, created_by)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (quote_no, data.get("customer_id"), data.get("customer_name", "Customer"), subtotal, tax_rate, tax_amount, discount, amount,
         data.get("status", "Draft"), data.get("notes", ""), data.get("quote_date", date.today().isoformat()),
         data.get("valid_until"), session.get("username", "admin"))
    )
    qid = cur.lastrowid
    for item in items:
        db.execute(
            "INSERT INTO quote_items (quote_id, product_id, product_name, quantity, unit_price, total) VALUES (?,?,?,?,?,?)",
            (qid, item.get("product_id"), item["product_name"], item["quantity"], item["unit_price"], float(item["quantity"]) * float(item["unit_price"]))
        )
    audit("create_quotation", "quotations", qid, quote_no)
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM quotations WHERE id=?", (qid,)).fetchone())), 201

@app.route("/api/quotations/<int:qid>", methods=["PUT"])
def update_quotation(qid):
    data = request.json or {}
    db = get_db()
    db.execute("UPDATE quotations SET status=?, notes=? WHERE id=?", (data.get("status"), data.get("notes"), qid))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM quotations WHERE id=?", (qid,)).fetchone()))

@app.route("/api/quotations/<int:qid>/convert", methods=["POST"])
def convert_quotation(qid):
    """Convert quotation to sale."""
    db = get_db()
    q = row_to_dict(db.execute("SELECT * FROM quotations WHERE id=?", (qid,)).fetchone())
    if not q:
        return jsonify({"error": "Not found"}), 404
    items = rows_to_list(db.execute("SELECT * FROM quote_items WHERE quote_id=?", (qid,)).fetchall())
    sale_items = [{"product_id": i["product_id"], "product_name": i["product_name"], "sku": "", "quantity": i["quantity"], "unit_price": i["unit_price"]} for i in items]
    # reuse create sale logic via internal call pattern
    last = db.execute("SELECT order_no FROM sales ORDER BY id DESC LIMIT 1").fetchone()
    num = int(last["order_no"].replace("SO-", "")) + 1 if last else 1001
    order_no = f"SO-{num}"
    cur = db.execute(
        """INSERT INTO sales (order_no, customer_id, customer_name, type, subtotal, tax_rate, tax_amount, discount, amount, paid, status, payment_status, notes, order_date, created_by)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (order_no, q["customer_id"], q["customer_name"], "Wholesale", q["subtotal"], q["tax_rate"], q["tax_amount"], q["discount"], q["amount"], 0,
         "Pending", "Unpaid", f"From quote {q['quote_no']}", date.today().isoformat(), session.get("username", "admin"))
    )
    sale_id = cur.lastrowid
    for item in sale_items:
        db.execute(
            "INSERT INTO sale_items (sale_id, product_id, product_name, sku, quantity, unit_price, total) VALUES (?,?,?,?,?,?,?)",
            (sale_id, item.get("product_id"), item["product_name"], "", item["quantity"], item["unit_price"], float(item["quantity"]) * float(item["unit_price"]))
        )
        if item.get("product_id"):
            db.execute("UPDATE products SET stock = stock - ? WHERE id=?", (item["quantity"], item["product_id"]))
            db.execute("INSERT INTO stock_movements (product_id, product_name, type, quantity, reference) VALUES (?,?,?,?,?)",
                       (item["product_id"], item["product_name"], "Sale", -int(item["quantity"]), order_no))
    db.execute("UPDATE quotations SET status=? WHERE id=?", ("Converted", qid))
    if q.get("customer_id"):
        db.execute("UPDATE customers SET outstanding = outstanding + ? WHERE id=?", (q["amount"], q["customer_id"]))
    audit("convert_quotation", "sales", sale_id, order_no)
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone())), 201

# ---- WAREHOUSES ----
@app.route("/api/warehouses", methods=["GET"])
def get_warehouses():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM warehouses ORDER BY id").fetchall()))

@app.route("/api/warehouses", methods=["POST"])
def create_warehouse():
    data = request.json or {}
    db = get_db()
    cur = db.execute("INSERT INTO warehouses (name, location) VALUES (?,?)", (data["name"], data.get("location", "")))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM warehouses WHERE id=?", (cur.lastrowid,)).fetchone())), 201

# ---- AUDIT ----
@app.route("/api/audit-logs")
def get_audit_logs():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100").fetchall()))

# ---- PROFIT REPORT ----
@app.route("/api/reports/profit")
def report_profit():
    db = get_db()
    from_date = request.args.get("from", (date.today() - timedelta(days=30)).isoformat())
    to_date = request.args.get("to", date.today().isoformat())
    # Approximate COGS from sale_items * product cost
    rows = db.execute(
        """SELECT si.product_name, SUM(si.quantity) as qty, SUM(si.total) as revenue,
                  SUM(si.quantity * COALESCE(p.cost, 0)) as cogs
           FROM sale_items si
           JOIN sales s ON s.id = si.sale_id
           LEFT JOIN products p ON p.id = si.product_id
           WHERE s.order_date BETWEEN ? AND ?
           GROUP BY si.product_name
           ORDER BY revenue DESC""",
        (from_date, to_date)
    ).fetchall()
    items = rows_to_list(rows)
    total_rev = sum(i["revenue"] or 0 for i in items)
    total_cogs = sum(i["cogs"] or 0 for i in items)
    expenses = db.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM expenses WHERE expense_date BETWEEN ? AND ?",
        (from_date, to_date)
    ).fetchone()["t"]
    return jsonify({
        "from": from_date, "to": to_date,
        "revenue": total_rev, "cogs": total_cogs,
        "gross_profit": total_rev - total_cogs,
        "expenses": expenses,
        "net_profit": total_rev - total_cogs - expenses,
        "items": items
    })



# ---- WAREHOUSE STOCK + TRANSFERS ----
@app.route("/api/warehouse-stocks")
def warehouse_stocks():
    db = get_db()
    wid = request.args.get("warehouse_id")
    if wid:
        rows = db.execute(
            """SELECT ws.*, p.name as product_name, p.sku, w.name as warehouse_name
               FROM warehouse_stocks ws
               JOIN products p ON p.id = ws.product_id
               JOIN warehouses w ON w.id = ws.warehouse_id
               WHERE ws.warehouse_id=? ORDER BY p.name""", (wid,)
        ).fetchall()
    else:
        rows = db.execute(
            """SELECT ws.*, p.name as product_name, p.sku, w.name as warehouse_name
               FROM warehouse_stocks ws
               JOIN products p ON p.id = ws.product_id
               JOIN warehouses w ON w.id = ws.warehouse_id
               ORDER BY w.name, p.name"""
        ).fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/stock-transfers", methods=["GET"])
def get_transfers():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM stock_transfers ORDER BY id DESC LIMIT 50").fetchall()))

@app.route("/api/stock-transfers", methods=["POST"])
def create_transfer():
    data = request.json or {}
    db = get_db()
    last = db.execute("SELECT transfer_no FROM stock_transfers ORDER BY id DESC LIMIT 1").fetchone()
    num = int(last["transfer_no"].replace("TR-", "")) + 1 if last else 1001
    transfer_no = f"TR-{num}"
    qty = int(data["quantity"])
    pid = data["product_id"]
    from_w = data["from_warehouse_id"]
    to_w = data["to_warehouse_id"]
    # adjust warehouse stocks
    row = db.execute("SELECT quantity FROM warehouse_stocks WHERE warehouse_id=? AND product_id=?", (from_w, pid)).fetchone()
    from_qty = row["quantity"] if row else 0
    if from_qty < qty:
        # allow using main product stock as fallback
        pass
    db.execute(
        """INSERT INTO warehouse_stocks (warehouse_id, product_id, quantity) VALUES (?,?,?)
           ON CONFLICT(warehouse_id, product_id) DO UPDATE SET quantity = quantity - ?""",
        (from_w, pid, max(0, from_qty - qty), qty)
    )
    db.execute(
        """INSERT INTO warehouse_stocks (warehouse_id, product_id, quantity) VALUES (?,?,?)
           ON CONFLICT(warehouse_id, product_id) DO UPDATE SET quantity = quantity + ?""",
        (to_w, pid, qty, qty)
    )
    db.execute(
        """INSERT INTO stock_transfers (transfer_no, from_warehouse_id, to_warehouse_id, product_id, product_name, quantity, notes, transfer_date, created_by)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (transfer_no, from_w, to_w, pid, data.get("product_name", ""), qty, data.get("notes", ""),
         date.today().isoformat(), session.get("username", "admin"))
    )
    db.execute("INSERT INTO stock_movements (product_id, product_name, type, quantity, reference, notes) VALUES (?,?,?,?,?,?)",
               (pid, data.get("product_name", ""), "Transfer", qty, transfer_no, f"{from_w}->{to_w}"))
    audit("stock_transfer", "stock_transfers", None, transfer_no)
    db.commit()
    return jsonify({"ok": True, "transfer_no": transfer_no}), 201

# ---- DELIVERIES ----
@app.route("/api/deliveries", methods=["GET"])
def get_deliveries():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM deliveries ORDER BY id DESC LIMIT 100").fetchall()))

@app.route("/api/deliveries", methods=["POST"])
def create_delivery():
    data = request.json or {}
    db = get_db()
    cur = db.execute(
        """INSERT INTO deliveries (sale_id, order_no, customer_name, driver_name, vehicle, status, delivery_date, notes)
           VALUES (?,?,?,?,?,?,?,?)""",
        (data.get("sale_id"), data.get("order_no"), data.get("customer_name"), data.get("driver_name"),
         data.get("vehicle"), data.get("status", "Pending"), data.get("delivery_date", date.today().isoformat()), data.get("notes", ""))
    )
    if data.get("sale_id") and data.get("status") == "Delivered":
        db.execute("UPDATE sales SET status=? WHERE id=?", ("Delivered", data["sale_id"]))
    audit("create_delivery", "deliveries", cur.lastrowid, data.get("order_no"))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM deliveries WHERE id=?", (cur.lastrowid,)).fetchone())), 201

@app.route("/api/deliveries/<int:did>", methods=["PUT"])
def update_delivery(did):
    data = request.json or {}
    db = get_db()
    db.execute("UPDATE deliveries SET status=?, driver_name=?, vehicle=?, notes=? WHERE id=?",
               (data.get("status"), data.get("driver_name"), data.get("vehicle"), data.get("notes"), did))
    d = db.execute("SELECT * FROM deliveries WHERE id=?", (did,)).fetchone()
    if d and data.get("status") == "Delivered" and d["sale_id"]:
        db.execute("UPDATE sales SET status=? WHERE id=?", ("Delivered", d["sale_id"]))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM deliveries WHERE id=?", (did,)).fetchone()))

# ---- BRANCHES ----
@app.route("/api/branches", methods=["GET"])
def get_branches():
    db = get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM branches ORDER BY id").fetchall()))

@app.route("/api/branches", methods=["POST"])
def create_branch():
    data = request.json or {}
    db = get_db()
    cur = db.execute("INSERT INTO branches (name, city, phone) VALUES (?,?,?)",
                     (data["name"], data.get("city", ""), data.get("phone", "")))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM branches WHERE id=?", (cur.lastrowid,)).fetchone())), 201

# ---- PURCHASE WITH ITEMS DETAIL ----
@app.route("/api/purchases/<int:pid>")
def get_purchase(pid):
    db = get_db()
    p = row_to_dict(db.execute("SELECT * FROM purchases WHERE id=?", (pid,)).fetchone())
    if not p:
        return jsonify({"error": "Not found"}), 404
    p["items"] = rows_to_list(db.execute("SELECT * FROM purchase_items WHERE purchase_id=?", (pid,)).fetchall())
    return jsonify(p)


# ---- USERS ----
@app.route("/api/users", methods=["GET"])
def get_users():
    db = get_db()
    rows = db.execute("SELECT id, username, full_name, role, status, created_at FROM users ORDER BY id").fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.json or {}
    db = get_db()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    try:
        cur = db.execute(
            "INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,?)",
            (username, hash_password(password), data.get("full_name", username), data.get("role", "sales"))
        )
        db.commit()
        row = db.execute("SELECT id, username, full_name, role, status FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400

@app.route("/api/users/<int:uid>", methods=["PUT"])
def update_user(uid):
    data = request.json or {}
    db = get_db()
    if data.get("password"):
        db.execute("UPDATE users SET full_name=?, role=?, status=?, password=? WHERE id=?",
                   (data.get("full_name"), data.get("role"), data.get("status", "Active"), hash_password(data["password"]), uid))
    else:
        db.execute("UPDATE users SET full_name=?, role=?, status=? WHERE id=?",
                   (data.get("full_name"), data.get("role"), data.get("status", "Active"), uid))
    db.commit()
    row = db.execute("SELECT id, username, full_name, role, status FROM users WHERE id=?", (uid,)).fetchone()
    return jsonify(row_to_dict(row))

@app.route("/api/users/<int:uid>", methods=["DELETE"])
def delete_user(uid):
    db = get_db()
    if uid == session.get("user_id"):
        return jsonify({"error": "Cannot delete yourself"}), 400
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    with app.app_context():
        init_db()
    print("=" * 55)
    print("  DistroFlow Pro - Advanced Distribution Software")
    print("  Login: admin / admin123")
    print("  Open: http://127.0.0.1:5000")
    print("=" * 55)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
