"""
DistroFlow - Complete Distribution Management Software
Retail + Wholesale
"""
import os
import sqlite3
import json
from datetime import datetime, date
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

DATABASE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "distroflow.db"))


def get_db():
    if 'db' not in g:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'Grocery',
        unit TEXT DEFAULT 'Piece',
        cost REAL DEFAULT 0,
        wholesale REAL NOT NULL,
        retail REAL NOT NULL,
        stock INTEGER DEFAULT 0,
        min_stock INTEGER DEFAULT 10,
        status TEXT DEFAULT 'Active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        type TEXT DEFAULT 'Wholesale',
        phone TEXT,
        city TEXT,
        credit_limit REAL DEFAULT 0,
        outstanding REAL DEFAULT 0,
        status TEXT DEFAULT 'Active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        city TEXT,
        outstanding REAL DEFAULT 0,
        status TEXT DEFAULT 'Active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        customer_name TEXT NOT NULL,
        type TEXT DEFAULT 'Wholesale',
        amount REAL NOT NULL,
        status TEXT DEFAULT 'Pending',
        notes TEXT,
        order_date TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_no TEXT UNIQUE NOT NULL,
        supplier_id INTEGER,
        supplier_name TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'Pending',
        notes TEXT,
        order_date TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        product_name TEXT,
        type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        reference TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)
    db.commit()

    # Seed data if empty
    count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        seed_data(db)


def seed_data(db):
    products = [
        ('PRD-001', 'Premium Basmati Rice 5kg', 'Grocery', 'Bag', 1200, 1350, 1500, 120, 50),
        ('PRD-002', 'Sunflower Oil 1L', 'Grocery', 'Bottle', 980, 1100, 1200, 85, 40),
        ('PRD-003', 'Detergent Powder 1kg', 'Household', 'Pack', 450, 520, 600, 45, 50),
        ('PRD-004', 'Green Tea Bags 100s', 'Beverages', 'Box', 480, 550, 650, 210, 30),
        ('PRD-005', 'Wheat Flour 10kg', 'Grocery', 'Bag', 1250, 1400, 1550, 67, 40),
        ('PRD-006', 'Hand Wash 500ml', 'Personal Care', 'Bottle', 220, 280, 350, 18, 25),
        ('PRD-007', 'Toothpaste 150g', 'Personal Care', 'Tube', 180, 220, 280, 95, 30),
        ('PRD-008', 'Sugar 5kg', 'Grocery', 'Bag', 850, 950, 1050, 140, 60),
        ('PRD-009', 'Cooking Oil 5L', 'Grocery', 'Can', 2800, 3100, 3400, 55, 20),
        ('PRD-010', 'Soap Bar 3-Pack', 'Personal Care', 'Pack', 150, 180, 220, 200, 40),
    ]
    db.executemany(
        "INSERT INTO products (sku, name, category, unit, cost, wholesale, retail, stock, min_stock) VALUES (?,?,?,?,?,?,?,?,?)",
        products
    )

    customers = [
        ('CUS-001', 'Al-Madina Store', 'Wholesale', '0300-1234567', 'Lahore', 500000, 125000),
        ('CUS-002', 'City Mart', 'Wholesale', '0321-9876543', 'Karachi', 300000, 45000),
        ('CUS-003', 'Khan Traders', 'Wholesale', '0333-5556677', 'Islamabad', 750000, 215000),
        ('CUS-004', 'Super Value', 'Wholesale', '0312-4445566', 'Faisalabad', 400000, 0),
        ('CUS-005', 'Ahmed General Store', 'Retail', '0301-7788990', 'Lahore', 50000, 12000),
        ('CUS-006', 'Bismillah Mart', 'Wholesale', '0345-1122334', 'Multan', 250000, 89000),
        ('CUS-007', 'Family Superstore', 'Wholesale', '0302-6677889', 'Rawalpindi', 350000, 56000),
        ('CUS-008', 'Walk-in Counter', 'Retail', '', 'Local', 0, 0),
    ]
    db.executemany(
        "INSERT INTO customers (code, name, type, phone, city, credit_limit, outstanding) VALUES (?,?,?,?,?,?,?)",
        customers
    )

    suppliers = [
        ('SUP-001', 'National Foods Ltd', '042-111222333', 'Lahore', 450000),
        ('SUP-002', 'Unilever Pakistan', '021-333444555', 'Karachi', 280000),
        ('SUP-003', 'Dalda Foods', '042-555666777', 'Lahore', 125000),
        ('SUP-004', 'Shan Foods', '021-777888999', 'Karachi', 0),
        ('SUP-005', 'Tapal Tea', '021-222333444', 'Karachi', 95000),
        ('SUP-006', 'Nestle Pakistan', '021-111000111', 'Karachi', 320000),
    ]
    db.executemany(
        "INSERT INTO suppliers (code, name, phone, city, outstanding) VALUES (?,?,?,?,?)",
        suppliers
    )

    today = date.today().isoformat()
    sales = [
        ('SO-1024', None, 'Al-Madina Store', 'Wholesale', 125000, 'Pending', today),
        ('SO-1023', None, 'City Mart', 'Wholesale', 87500, 'Delivered', today),
        ('SO-1022', None, 'Walk-in Customer', 'Retail', 4200, 'Completed', today),
        ('SO-1021', None, 'Khan Traders', 'Wholesale', 215000, 'Processing', today),
        ('SO-1020', None, 'Super Value', 'Wholesale', 156000, 'Delivered', today),
        ('SO-1019', None, 'Bismillah Mart', 'Wholesale', 98000, 'Delivered', today),
        ('SO-1018', None, 'Family Superstore', 'Wholesale', 142000, 'Pending', today),
    ]
    db.executemany(
        "INSERT INTO sales (order_no, customer_id, customer_name, type, amount, status, order_date) VALUES (?,?,?,?,?,?,?)",
        sales
    )

    purchases = [
        ('PO-0456', None, 'National Foods Ltd', 285000, 'Received', today),
        ('PO-0455', None, 'Unilever Pakistan', 156000, 'Pending', today),
        ('PO-0454', None, 'Dalda Foods', 98000, 'Received', today),
        ('PO-0453', None, 'Shan Foods', 72000, 'Received', today),
        ('PO-0452', None, 'Tapal Tea', 45000, 'Pending', today),
    ]
    db.executemany(
        "INSERT INTO purchases (po_no, supplier_id, supplier_name, amount, status, order_date) VALUES (?,?,?,?,?,?)",
        purchases
    )

    settings = [
        ('company_name', 'DistroFlow Traders'),
        ('business_type', 'Wholesale & Retail'),
        ('phone', '042-1234567'),
        ('email', 'info@distroflow.com'),
        ('address', '123 Business Avenue, Lahore, Pakistan'),
        ('currency', 'PKR'),
        ('tax_rate', '18'),
    ]
    db.executemany("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", settings)
    db.commit()


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    return [dict(r) for r in rows]


# ===================== API ROUTES =====================

@app.route('/api/dashboard')
def dashboard():
    db = get_db()
    today = date.today().isoformat()

    today_sales = db.execute(
        "SELECT COALESCE(SUM(amount),0) as total, COUNT(*) as count FROM sales WHERE order_date = ?", (today,)
    ).fetchone()
    pending = db.execute(
        "SELECT COUNT(*) as c FROM sales WHERE status IN ('Pending','Processing')"
    ).fetchone()['c']
    low_stock = db.execute(
        "SELECT COUNT(*) as c FROM products WHERE stock <= min_stock"
    ).fetchone()['c']
    total_products = db.execute("SELECT COUNT(*) as c FROM products").fetchone()['c']
    total_customers = db.execute("SELECT COUNT(*) as c FROM customers").fetchone()['c']
    outstanding = db.execute("SELECT COALESCE(SUM(outstanding),0) as t FROM customers").fetchone()['t']
    monthly = db.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM sales WHERE order_date >= date('now', '-30 days')"
    ).fetchone()['t']

    recent = rows_to_list(db.execute(
        "SELECT * FROM sales ORDER BY id DESC LIMIT 8"
    ).fetchall())

    top_products = rows_to_list(db.execute(
        "SELECT id, sku, name, stock, wholesale, (stock * wholesale) as value FROM products ORDER BY value DESC LIMIT 5"
    ).fetchall())

    return jsonify({
        'today_sales': today_sales['total'],
        'today_orders': today_sales['count'],
        'pending_orders': pending,
        'low_stock': low_stock,
        'total_products': total_products,
        'total_customers': total_customers,
        'outstanding': outstanding,
        'monthly_sales': monthly,
        'recent_orders': recent,
        'top_products': top_products,
    })


# ---- Products ----
@app.route('/api/products', methods=['GET'])
def get_products():
    db = get_db()
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(
            "SELECT * FROM products WHERE name LIKE ? OR sku LIKE ? ORDER BY name",
            (f'%{q}%', f'%{q}%')
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM products ORDER BY name").fetchall()
    return jsonify(rows_to_list(rows))


@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.json or {}
    db = get_db()
    sku = data.get('sku') or f"PRD-{datetime.now().strftime('%H%M%S')}"
    try:
        cur = db.execute(
            """INSERT INTO products (sku, name, category, unit, cost, wholesale, retail, stock, min_stock)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (sku, data['name'], data.get('category', 'Grocery'), data.get('unit', 'Piece'),
             data.get('cost', 0), data['wholesale'], data['retail'],
             data.get('stock', 0), data.get('min_stock', 10))
        )
        db.commit()
        row = db.execute("SELECT * FROM products WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'SKU already exists'}), 400
    except KeyError as e:
        return jsonify({'error': f'Missing field: {e}'}), 400


@app.route('/api/products/<int:pid>', methods=['PUT'])
def update_product(pid):
    data = request.json or {}
    db = get_db()
    db.execute(
        """UPDATE products SET name=?, category=?, unit=?, cost=?, wholesale=?, retail=?,
           stock=?, min_stock=?, status=? WHERE id=?""",
        (data.get('name'), data.get('category'), data.get('unit'), data.get('cost'),
         data.get('wholesale'), data.get('retail'), data.get('stock'), data.get('min_stock'),
         data.get('status', 'Active'), pid)
    )
    db.commit()
    row = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    return jsonify(row_to_dict(row))


@app.route('/api/products/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (pid,))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/products/<int:pid>/stock', methods=['POST'])
def adjust_stock(pid):
    data = request.json or {}
    new_stock = int(data.get('stock', 0))
    notes = data.get('notes', '')
    db = get_db()
    prod = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not prod:
        return jsonify({'error': 'Not found'}), 404
    old = prod['stock']
    db.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, pid))
    db.execute(
        "INSERT INTO stock_movements (product_id, product_name, type, quantity, notes) VALUES (?,?,?,?,?)",
        (pid, prod['name'], 'Adjustment', new_stock - old, notes)
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()))


# ---- Customers ----
@app.route('/api/customers', methods=['GET'])
def get_customers():
    db = get_db()
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(
            "SELECT * FROM customers WHERE name LIKE ? OR code LIKE ? ORDER BY name",
            (f'%{q}%', f'%{q}%')
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM customers ORDER BY name").fetchall()
    return jsonify(rows_to_list(rows))


@app.route('/api/customers', methods=['POST'])
def create_customer():
    data = request.json or {}
    db = get_db()
    code = data.get('code') or f"CUS-{datetime.now().strftime('%H%M%S')}"
    try:
        cur = db.execute(
            """INSERT INTO customers (code, name, type, phone, city, credit_limit, outstanding)
               VALUES (?,?,?,?,?,?,?)""",
            (code, data['name'], data.get('type', 'Wholesale'), data.get('phone', ''),
             data.get('city', ''), data.get('credit_limit', 0), data.get('outstanding', 0))
        )
        db.commit()
        return jsonify(row_to_dict(db.execute("SELECT * FROM customers WHERE id = ?", (cur.lastrowid,)).fetchone())), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/customers/<int:cid>', methods=['PUT'])
def update_customer(cid):
    data = request.json or {}
    db = get_db()
    db.execute(
        """UPDATE customers SET name=?, type=?, phone=?, city=?, credit_limit=?, outstanding=?, status=?
           WHERE id=?""",
        (data.get('name'), data.get('type'), data.get('phone'), data.get('city'),
         data.get('credit_limit'), data.get('outstanding'), data.get('status', 'Active'), cid)
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()))


@app.route('/api/customers/<int:cid>', methods=['DELETE'])
def delete_customer(cid):
    db = get_db()
    db.execute("DELETE FROM customers WHERE id = ?", (cid,))
    db.commit()
    return jsonify({'ok': True})


# ---- Suppliers ----
@app.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    db = get_db()
    rows = db.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    return jsonify(rows_to_list(rows))


@app.route('/api/suppliers', methods=['POST'])
def create_supplier():
    data = request.json or {}
    db = get_db()
    code = data.get('code') or f"SUP-{datetime.now().strftime('%H%M%S')}"
    cur = db.execute(
        "INSERT INTO suppliers (code, name, phone, city, outstanding) VALUES (?,?,?,?,?)",
        (code, data['name'], data.get('phone', ''), data.get('city', ''), data.get('outstanding', 0))
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM suppliers WHERE id = ?", (cur.lastrowid,)).fetchone())), 201


@app.route('/api/suppliers/<int:sid>', methods=['PUT'])
def update_supplier(sid):
    data = request.json or {}
    db = get_db()
    db.execute(
        "UPDATE suppliers SET name=?, phone=?, city=?, outstanding=?, status=? WHERE id=?",
        (data.get('name'), data.get('phone'), data.get('city'), data.get('outstanding'), data.get('status', 'Active'), sid)
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM suppliers WHERE id = ?", (sid,)).fetchone()))


@app.route('/api/suppliers/<int:sid>', methods=['DELETE'])
def delete_supplier(sid):
    db = get_db()
    db.execute("DELETE FROM suppliers WHERE id = ?", (sid,))
    db.commit()
    return jsonify({'ok': True})


# ---- Sales ----
@app.route('/api/sales', methods=['GET'])
def get_sales():
    db = get_db()
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(
            "SELECT * FROM sales WHERE order_no LIKE ? OR customer_name LIKE ? ORDER BY id DESC",
            (f'%{q}%', f'%{q}%')
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM sales ORDER BY id DESC").fetchall()
    return jsonify(rows_to_list(rows))


@app.route('/api/sales', methods=['POST'])
def create_sale():
    data = request.json or {}
    db = get_db()
    last = db.execute("SELECT order_no FROM sales ORDER BY id DESC LIMIT 1").fetchone()
    if last:
        num = int(last['order_no'].replace('SO-', '')) + 1
    else:
        num = 1001
    order_no = f"SO-{num}"
    cur = db.execute(
        """INSERT INTO sales (order_no, customer_id, customer_name, type, amount, status, notes, order_date)
           VALUES (?,?,?,?,?,?,?,?)""",
        (order_no, data.get('customer_id'), data['customer_name'], data.get('type', 'Wholesale'),
         data['amount'], data.get('status', 'Pending'), data.get('notes', ''),
         data.get('order_date', date.today().isoformat()))
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM sales WHERE id = ?", (cur.lastrowid,)).fetchone())), 201


@app.route('/api/sales/<int:sid>', methods=['PUT'])
def update_sale(sid):
    data = request.json or {}
    db = get_db()
    db.execute(
        "UPDATE sales SET status=?, amount=?, notes=? WHERE id=?",
        (data.get('status'), data.get('amount'), data.get('notes'), sid)
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM sales WHERE id = ?", (sid,)).fetchone()))


@app.route('/api/sales/<int:sid>', methods=['DELETE'])
def delete_sale(sid):
    db = get_db()
    db.execute("DELETE FROM sales WHERE id = ?", (sid,))
    db.commit()
    return jsonify({'ok': True})


# ---- Purchases ----
@app.route('/api/purchases', methods=['GET'])
def get_purchases():
    db = get_db()
    rows = db.execute("SELECT * FROM purchases ORDER BY id DESC").fetchall()
    return jsonify(rows_to_list(rows))


@app.route('/api/purchases', methods=['POST'])
def create_purchase():
    data = request.json or {}
    db = get_db()
    last = db.execute("SELECT po_no FROM purchases ORDER BY id DESC LIMIT 1").fetchone()
    if last:
        num = int(last['po_no'].replace('PO-', '')) + 1
    else:
        num = 4501
    po_no = f"PO-{num}"
    cur = db.execute(
        """INSERT INTO purchases (po_no, supplier_id, supplier_name, amount, status, notes, order_date)
           VALUES (?,?,?,?,?,?,?)""",
        (po_no, data.get('supplier_id'), data['supplier_name'], data['amount'],
         data.get('status', 'Pending'), data.get('notes', ''),
         data.get('order_date', date.today().isoformat()))
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM purchases WHERE id = ?", (cur.lastrowid,)).fetchone())), 201


@app.route('/api/purchases/<int:pid>', methods=['PUT'])
def update_purchase(pid):
    data = request.json or {}
    db = get_db()
    db.execute(
        "UPDATE purchases SET status=?, amount=?, notes=? WHERE id=?",
        (data.get('status'), data.get('amount'), data.get('notes'), pid)
    )
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM purchases WHERE id = ?", (pid,)).fetchone()))


@app.route('/api/purchases/<int:pid>', methods=['DELETE'])
def delete_purchase(pid):
    db = get_db()
    db.execute("DELETE FROM purchases WHERE id = ?", (pid,))
    db.commit()
    return jsonify({'ok': True})


# ---- Settings ----
@app.route('/api/settings', methods=['GET'])
def get_settings():
    db = get_db()
    rows = db.execute("SELECT * FROM settings").fetchall()
    return jsonify({r['key']: r['value'] for r in rows})


@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.json or {}
    db = get_db()
    for k, v in data.items():
        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (k, str(v)))
    db.commit()
    return jsonify({'ok': True})


# ---- Serve Frontend ----
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('static', path)


# ===================== START =====================
if __name__ == '__main__':
    with app.app_context():
        init_db()
    print("=" * 50)
    print("  DistroFlow - Distribution Management Software")
    print("  Open: http://127.0.0.1:5000")
    print("=" * 50)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
