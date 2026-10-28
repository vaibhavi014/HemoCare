import os
import sqlite3
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = os.environ.get("HEMOCARE_DB_NAME", "bloodbank.db")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.path.isabs(DB_NAME):
    DB_PATH = DB_NAME
else:
    DB_PATH = os.path.join(BASE_DIR, DB_NAME)

VALID_COMPONENTS = ["Whole Blood", "PRBC", "FFP", "Platelets"]
VALID_BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
VALID_TEST_RESULTS = ["Non-Reactive", "Reactive", "Pending"]
VALID_INVENTORY_STATUSES = ["Available", "Issued", "Discarded", "Expired", "Reserved", "Quarantined"]

def get_db_connection():
    """Returns a SQLite connection configured with Row factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes the database, creates required tables, and seeds initial configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            created_at TEXT NOT NULL
        );
    """)

    # Donors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT,
            dob TEXT,
            last_donation_date TEXT,
            donor_type TEXT NOT NULL DEFAULT 'Voluntary',
            status TEXT NOT NULL DEFAULT 'Active',
            remarks TEXT,
            created_at TEXT NOT NULL
        );
    """)

    # Donations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donation_code TEXT UNIQUE NOT NULL,
            donor_id INTEGER NOT NULL,
            donor_code TEXT NOT NULL,
            donor_name TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            donation_date TEXT NOT NULL,
            donation_type TEXT NOT NULL DEFAULT 'Voluntary',
            volume_ml INTEGER NOT NULL DEFAULT 450,
            bag_number TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Collected',
            remarks TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (donor_id) REFERENCES donors (id) ON DELETE RESTRICT
        );
    """)

    # Serology table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS serology (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serology_code TEXT UNIQUE NOT NULL,
            donation_id INTEGER NOT NULL UNIQUE,
            donation_code TEXT NOT NULL,
            donor_id INTEGER NOT NULL,
            donor_code TEXT NOT NULL,
            donor_name TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            hiv TEXT NOT NULL DEFAULT 'Non-Reactive',
            hbsag TEXT NOT NULL DEFAULT 'Non-Reactive',
            hcv TEXT NOT NULL DEFAULT 'Non-Reactive',
            syphilis TEXT NOT NULL DEFAULT 'Non-Reactive',
            malaria TEXT NOT NULL DEFAULT 'Non-Reactive',
            overall_result TEXT NOT NULL,
            test_date TEXT NOT NULL,
            remarks TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (donation_id) REFERENCES donations (id) ON DELETE CASCADE,
            FOREIGN KEY (donor_id) REFERENCES donors (id) ON DELETE RESTRICT
        );
    """)

    # Inventory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_code TEXT UNIQUE NOT NULL,
            donation_id INTEGER,
            donation_code TEXT,
            donor_id INTEGER,
            donor_code TEXT,
            blood_group TEXT NOT NULL,
            component_type TEXT NOT NULL,
            collection_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            volume_ml INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available',
            storage_location TEXT NOT NULL,
            serology_status TEXT NOT NULL DEFAULT 'Pending',
            remarks TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (donation_id) REFERENCES donations (id) ON DELETE SET NULL,
            FOREIGN KEY (donor_id) REFERENCES donors (id) ON DELETE SET NULL
        );
    """)

    # Hospitals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT,
            license_number TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            remarks TEXT,
            created_at TEXT NOT NULL
        );
    """)

    # Issues table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_code TEXT UNIQUE NOT NULL,
            issue_date TEXT NOT NULL,
            hospital_id INTEGER NOT NULL,
            hospital_code TEXT NOT NULL,
            hospital_name TEXT NOT NULL,
            unit_id INTEGER NOT NULL,
            unit_code TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            component_type TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            patient_name TEXT NOT NULL,
            patient_id TEXT,
            doctor_dept TEXT,
            reason TEXT,
            issued_by TEXT NOT NULL,
            remarks TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (hospital_id) REFERENCES hospitals (id) ON DELETE RESTRICT,
            FOREIGN KEY (unit_id) REFERENCES inventory (id) ON DELETE RESTRICT
        );
    """)

    # Discard records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS discard_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discard_code TEXT UNIQUE NOT NULL,
            unit_id INTEGER NOT NULL,
            unit_code TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            component_type TEXT NOT NULL,
            discard_date TEXT NOT NULL,
            reason TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            authorized_by TEXT NOT NULL,
            remarks TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (unit_id) REFERENCES inventory (id) ON DELETE RESTRICT
        );
    """)

    # Stock settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_type TEXT UNIQUE NOT NULL,
            min_stock_level INTEGER NOT NULL DEFAULT 10,
            expiring_days_threshold INTEGER NOT NULL DEFAULT 7
        );
    """)

    # Seed default admin user if not exists
    cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        hashed_password = generate_password_hash("admin123")
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", hashed_password, "System Administrator", "admin", datetime.now().isoformat()))

    # Seed stock settings for the 4 valid components
    for comp in VALID_COMPONENTS:
        cursor.execute("SELECT id FROM stock_settings WHERE component_type = ?", (comp,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO stock_settings (component_type, min_stock_level, expiring_days_threshold)
                VALUES (?, 10, 7)
            """, (comp,))

    conn.commit()
    conn.close()

    # Sync any expired inventory units immediately
    sync_expired_units()

def get_next_code(table_name, code_column, prefix, padding=4):
    """Generates the next sequential code such as DNR0001, DON0001, UNIT0001, etc."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT {code_column} FROM {table_name} ORDER BY id DESC LIMIT 1"
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()

    if not row or not row[code_column]:
        return f"{prefix}{1:0{padding}d}"

    last_code = row[code_column]
    try:
        # Extract trailing digits
        num_str = "".join([c for c in last_code if c.isdigit()])
        next_num = int(num_str) + 1 if num_str else 1
    except ValueError:
        next_num = 1

    return f"{prefix}{next_num:0{padding}d}"

def calculate_serology_result(hiv, hbsag, hcv, syphilis, malaria):
    """
    Computes overall serology result:
    - If any required infection test is 'Reactive' -> 'Reactive'
    - If all 5 tests are 'Non-Reactive' -> 'Non-Reactive'
    - If any test is 'Pending' and none 'Reactive' -> 'Pending'
    """
    tests = [hiv, hbsag, hcv, syphilis, malaria]
    if any(t == "Reactive" for t in tests):
        return "Reactive"
    if all(t == "Non-Reactive" for t in tests):
        return "Non-Reactive"
    return "Pending"

def sync_expired_units():
    """
    Marks available units whose expiry_date < today as 'Expired'.
    Ensures expired units are never considered Available.
    """
    today_str = date.today().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE inventory
        SET status = 'Expired'
        WHERE status = 'Available' AND expiry_date < ?
    """, (today_str,))
    conn.commit()
    conn.close()

def get_stock_settings():
    """Retrieves minimum stock thresholds and expiring days configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT component_type, min_stock_level, expiring_days_threshold FROM stock_settings")
    rows = cursor.fetchall()
    conn.close()
    settings = {}
    for r in rows:
        settings[r["component_type"]] = {
            "min_stock": r["min_stock_level"],
            "expiring_days": r["expiring_days_threshold"]
        }
    return settings
