import sqlite3, hashlib, os, hmac
from datetime import date, datetime

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rental.db")

def _con():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def _hash(pw, salt=None):
    salt = salt or os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 100_000).hex()
    return f"{salt}${h}"

def _check(pw, stored):
    salt, _ = stored.split("$")
    return hmac.compare_digest(_hash(pw, salt), stored)

def init_db():
    c = _con()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, is_admin INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS vehicles(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, type TEXT NOT NULL,
        plate TEXT UNIQUE NOT NULL, price_per_day REAL NOT NULL, available INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, vehicle_id INTEGER NOT NULL,
        start_date TEXT NOT NULL, end_date TEXT NOT NULL, total REAL NOT NULL,
        status TEXT DEFAULT 'active');
    """)
    if not c.execute("SELECT 1 FROM users").fetchone():
        c.execute("INSERT INTO users(name,email,password,is_admin) VALUES('Admin','admin@rent.com',?,1)",
                  (_hash("admin123"),))
        c.executemany("INSERT INTO vehicles(name,type,plate,price_per_day) VALUES(?,?,?,?)", [
            ("Maruti Swift", "Car", "MH12AB1001", 1800),
            ("Hyundai Creta", "SUV", "MH12AB1002", 3200),
            ("Honda Activa", "Scooter", "MH12AB1003", 500),
            ("Royal Enfield Classic 350", "Bike", "MH12AB1004", 900),
            ("Toyota Innova", "SUV", "MH12AB1005", 4000)])
    c.commit(); c.close()

def register(name, email, pw):
    name, email = name.strip(), email.strip().lower()
    if not name or not email or len(pw) < 6:
        return False, "Fill all fields. Password needs 6+ characters."
    try:
        c = _con()
        c.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)", (name, email, _hash(pw)))
        c.commit(); c.close()
        return True, "Account created. You can log in now."
    except sqlite3.IntegrityError:
        return False, "That email is already registered."

def login(email, pw):
    c = _con()
    u = c.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    c.close()
    return dict(u) if u and _check(pw, u["password"]) else None

def list_vehicles(only_available=False):
    c = _con()
    q = "SELECT * FROM vehicles" + (" WHERE available=1" if only_available else "")
    r = [dict(x) for x in c.execute(q)]
    c.close(); return r

def rent(user_id, vehicle_id, start, end):
    try:
        s = datetime.strptime(start, "%Y-%m-%d").date()
        e = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        return False, "Dates must be in YYYY-MM-DD format."
    if s < date.today():
        return False, "Start date can't be in the past."
    if e < s:
        return False, "End date can't be before start date."
    c = _con()
    v = c.execute("SELECT * FROM vehicles WHERE id=?", (vehicle_id,)).fetchone()
    if not v or not v["available"]:
        c.close(); return False, "Vehicle is not available."
    days = (e - s).days + 1
    total = days * v["price_per_day"]
    c.execute("INSERT INTO bookings(user_id,vehicle_id,start_date,end_date,total) VALUES(?,?,?,?,?)",
              (user_id, vehicle_id, s.isoformat(), e.isoformat(), total))
    c.execute("UPDATE vehicles SET available=0 WHERE id=?", (vehicle_id,))
    c.commit(); c.close()
    return True, f"Booked {v['name']} for {days} day(s). Total: Rs {total:,.0f}"

def bookings(user_id=None):
    c = _con()
    q = """SELECT b.*, v.name AS vehicle, v.plate, u.name AS customer FROM bookings b
           JOIN vehicles v ON v.id=b.vehicle_id JOIN users u ON u.id=b.user_id"""
    args = ()
    if user_id:
        q += " WHERE b.user_id=?"; args = (user_id,)
    r = [dict(x) for x in c.execute(q + " ORDER BY b.id DESC", args)]
    c.close(); return r

def _close_booking(booking_id, new_status, user_id=None):
    c = _con()
    b = c.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
    if not b or b["status"] != "active" or (user_id and b["user_id"] != user_id):
        c.close(); return False
    c.execute("UPDATE bookings SET status=? WHERE id=?", (new_status, booking_id))
    c.execute("UPDATE vehicles SET available=1 WHERE id=?", (b["vehicle_id"],))
    c.commit(); c.close(); return True

def cancel_booking(booking_id, user_id): return _close_booking(booking_id, "cancelled", user_id)
def return_booking(booking_id):          return _close_booking(booking_id, "returned")

def add_vehicle(name, vtype, plate, price):
    try:
        price = float(price)
        if price <= 0 or not name.strip() or not vtype.strip() or not plate.strip():
            raise ValueError
        c = _con()
        c.execute("INSERT INTO vehicles(name,type,plate,price_per_day) VALUES(?,?,?,?)",
                  (name.strip(), vtype.strip(), plate.strip().upper(), price))
        c.commit(); c.close(); return True, "Vehicle added."
    except (ValueError, sqlite3.IntegrityError):
        return False, "Invalid data or duplicate plate number."

def delete_vehicle(vid):
    c = _con()
    if c.execute("SELECT 1 FROM bookings WHERE vehicle_id=?", (vid,)).fetchone():
        c.close(); return False, "Can't delete a vehicle that has booking history."
    c.execute("DELETE FROM vehicles WHERE id=?", (vid,)); c.commit(); c.close()
    return True, "Vehicle deleted."
