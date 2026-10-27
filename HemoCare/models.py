from datetime import datetime, date, timedelta
from database import (
    get_db_connection,
    get_next_code,
    calculate_serology_result,
    sync_expired_units,
    VALID_COMPONENTS,
    VALID_BLOOD_GROUPS,
    VALID_TEST_RESULTS,
    VALID_INVENTORY_STATUSES
)

DEFAULT_SHELF_LIFE_DAYS = {
    "Whole Blood": 35,
    "PRBC": 42,
    "FFP": 365,
    "Platelets": 5
}

# ==========================================
# DONOR OPERATIONS
# ==========================================

def get_donors(search=None, blood_group=None, status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM donors WHERE 1=1"
    params = []

    if search:
        s = f"%{search.strip()}%"
        query += " AND (donor_code LIKE ? OR name LIKE ? OR phone LIKE ? OR email LIKE ?)"
        params.extend([s, s, s, s])

    if blood_group and blood_group in VALID_BLOOD_GROUPS:
        query += " AND blood_group = ?"
        params.append(blood_group)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_donor_by_id(donor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM donors WHERE id = ? OR donor_code = ?", (donor_id, donor_id))
    row = cursor.fetchone()
    conn.close()
    return row

def create_donor(data):
    # Validation
    if not data.get("name") or not data.get("blood_group") or not data.get("phone"):
        raise ValueError("Name, Blood Group, and Phone are required fields.")
    if data["blood_group"] not in VALID_BLOOD_GROUPS:
        raise ValueError(f"Invalid blood group: {data['blood_group']}")

    donor_code = get_next_code("donors", "donor_code", "DNR")
    now_str = datetime.now().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO donors (
            donor_code, name, age, gender, blood_group, phone, email,
            address, dob, last_donation_date, donor_type, status, remarks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        donor_code,
        data["name"].strip(),
        int(data.get("age", 0)),
        data.get("gender", "Male"),
        data["blood_group"],
        data["phone"].strip(),
        data.get("email", "").strip() or None,
        data.get("address", "").strip() or None,
        data.get("dob") or None,
        data.get("last_donation_date") or None,
        data.get("donor_type", "Voluntary"),
        data.get("status", "Active"),
        data.get("remarks", "").strip() or None,
        now_str
    ))
    donor_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return donor_id, donor_code

def update_donor(donor_id, data):
    if not data.get("name") or not data.get("blood_group") or not data.get("phone"):
        raise ValueError("Name, Blood Group, and Phone are required.")
    if data["blood_group"] not in VALID_BLOOD_GROUPS:
        raise ValueError(f"Invalid blood group: {data['blood_group']}")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE donors SET
            name = ?, age = ?, gender = ?, blood_group = ?, phone = ?, email = ?,
            address = ?, dob = ?, last_donation_date = ?, donor_type = ?, status = ?, remarks = ?
        WHERE id = ?
    """, (
        data["name"].strip(),
        int(data.get("age", 0)),
        data.get("gender", "Male"),
        data["blood_group"],
        data["phone"].strip(),
        data.get("email", "").strip() or None,
        data.get("address", "").strip() or None,
        data.get("dob") or None,
        data.get("last_donation_date") or None,
        data.get("donor_type", "Voluntary"),
        data.get("status", "Active"),
        data.get("remarks", "").strip() or None,
        donor_id
    ))
    conn.commit()
    conn.close()

def delete_donor(donor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if donor has donations
    cursor.execute("SELECT COUNT(*) as count FROM donations WHERE donor_id = ?", (donor_id,))
    res = cursor.fetchone()
    if res and res["count"] > 0:
        conn.close()
        raise ValueError("Cannot delete donor who has donation records. Deactivate donor instead.")

    cursor.execute("DELETE FROM donors WHERE id = ?", (donor_id,))
    conn.commit()
    conn.close()

# ==========================================
# DONATION OPERATIONS
# ==========================================

def get_donations(search=None, blood_group=None, date_from=None, date_to=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM donations WHERE 1=1"
    params = []

    if search:
        s = f"%{search.strip()}%"
        query += " AND (donation_code LIKE ? OR donor_code LIKE ? OR donor_name LIKE ? OR bag_number LIKE ?)"
        params.extend([s, s, s, s])

    if blood_group and blood_group in VALID_BLOOD_GROUPS:
        query += " AND blood_group = ?"
        params.append(blood_group)

    if date_from:
        query += " AND donation_date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND donation_date <= ?"
        params.append(date_to)

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_donation_by_id(donation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM donations WHERE id = ? OR donation_code = ?", (donation_id, donation_id))
    row = cursor.fetchone()
    conn.close()
    return row

def create_donation(data):
    donor = get_donor_by_id(data["donor_id"])
    if not donor:
        raise ValueError("Selected donor does not exist.")

    if donor["status"] == "Deferred":
        raise ValueError("Selected donor is currently Deferred and cannot donate blood.")

    donation_code = get_next_code("donations", "donation_code", "DON")
    now_str = datetime.now().isoformat()
    donation_date = data.get("donation_date") or date.today().isoformat()
    bag_num = data.get("bag_number") or f"BAG-{donation_code}"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO donations (
            donation_code, donor_id, donor_code, donor_name, blood_group,
            donation_date, donation_type, volume_ml, bag_number, status, remarks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        donation_code,
        donor["id"],
        donor["donor_code"],
        donor["name"],
        donor["blood_group"],
        donation_date,
        data.get("donation_type", "Voluntary"),
        int(data.get("volume_ml", 450)),
        bag_num,
        data.get("status", "Collected"),
        data.get("remarks", "").strip() or None,
        now_str
    ))
    donation_id = cursor.lastrowid

    # Update donor's last donation date
    cursor.execute("""
        UPDATE donors SET last_donation_date = ? WHERE id = ?
    """, (donation_date, donor["id"]))

    conn.commit()
    conn.close()
    return donation_id, donation_code

# ==========================================
# SEROLOGY OPERATIONS
# ==========================================

def get_serology_records(search=None, result=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM serology WHERE 1=1"
    params = []

    if search:
        s = f"%{search.strip()}%"
        query += " AND (serology_code LIKE ? OR donation_code LIKE ? OR donor_code LIKE ? OR donor_name LIKE ?)"
        params.extend([s, s, s, s])

    if result and result in VALID_TEST_RESULTS:
        query += " AND overall_result = ?"
        params.append(result)

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_serology_by_id(serology_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM serology WHERE id = ? OR serology_code = ?", (serology_id, serology_id))
    row = cursor.fetchone()
    conn.close()
    return row

def get_serology_by_donation_id(donation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM serology WHERE donation_id = ?", (donation_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def record_serology(data):
    donation = get_donation_by_id(data["donation_id"])
    if not donation:
        raise ValueError("Invalid donation ID specified.")

    hiv = data.get("hiv", "Non-Reactive")
    hbsag = data.get("hbsag", "Non-Reactive")
    hcv = data.get("hcv", "Non-Reactive")
    syphilis = data.get("syphilis", "Non-Reactive")
    malaria = data.get("malaria", "Non-Reactive")

    overall = calculate_serology_result(hiv, hbsag, hcv, syphilis, malaria)
    test_date = data.get("test_date") or date.today().isoformat()
    now_str = datetime.now().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if serology record already exists for this donation
    cursor.execute("SELECT id, serology_code FROM serology WHERE donation_id = ?", (donation["id"],))
    existing = cursor.fetchone()

    if existing:
        serology_id = existing["id"]
        serology_code = existing["serology_code"]
        cursor.execute("""
            UPDATE serology SET
                hiv = ?, hbsag = ?, hcv = ?, syphilis = ?, malaria = ?,
                overall_result = ?, test_date = ?, remarks = ?
            WHERE id = ?
        """, (
            hiv, hbsag, hcv, syphilis, malaria,
            overall, test_date, data.get("remarks", "").strip() or None,
            serology_id
        ))
    else:
        serology_code = get_next_code("serology", "serology_code", "SER")
        cursor.execute("""
            INSERT INTO serology (
                serology_code, donation_id, donation_code, donor_id, donor_code,
                donor_name, blood_group, hiv, hbsag, hcv, syphilis, malaria,
                overall_result, test_date, remarks, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            serology_code,
            donation["id"],
            donation["donation_code"],
            donation["donor_id"],
            donation["donor_code"],
            donation["donor_name"],
            donation["blood_group"],
            hiv, hbsag, hcv, syphilis, malaria,
            overall, test_date, data.get("remarks", "").strip() or None,
            now_str
        ))
        serology_id = cursor.lastrowid

    # Update donation status
    new_donation_status = "Tested" if overall != "Reactive" else "Discarded"
    cursor.execute("UPDATE donations SET status = ? WHERE id = ?", (new_donation_status, donation["id"]))

    # CRITICAL: Synchronize all inventory units linked to this donation
    if overall == "Reactive":
        # Any reactive inventory unit must NOT be Available or issueable.
        # Set serology_status='Reactive' and status='Quarantined' or 'Discarded'
        cursor.execute("""
            UPDATE inventory
            SET serology_status = 'Reactive',
                status = CASE WHEN status = 'Available' THEN 'Quarantined' ELSE status END
            WHERE donation_id = ?
        """, (donation["id"],))
    else:
        cursor.execute("""
            UPDATE inventory
            SET serology_status = ?
            WHERE donation_id = ?
        """, (overall, donation["id"]))

    conn.commit()
    conn.close()
    return serology_id, serology_code, overall

# ==========================================
# INVENTORY OPERATIONS
# ==========================================

def get_inventory(search=None, component=None, blood_group=None, status=None, expiring_days=None):
    sync_expired_units()
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM inventory WHERE 1=1"
    params = []

    if search:
        s = f"%{search.strip()}%"
        query += " AND (unit_code LIKE ? OR donation_code LIKE ? OR donor_code LIKE ? OR storage_location LIKE ?)"
        params.extend([s, s, s, s])

    if component and component in VALID_COMPONENTS:
        query += " AND component_type = ?"
        params.append(component)

    if blood_group and blood_group in VALID_BLOOD_GROUPS:
        query += " AND blood_group = ?"
        params.append(blood_group)

    if status and status in VALID_INVENTORY_STATUSES:
        query += " AND status = ?"
        params.append(status)

    if expiring_days is not None:
        target_date = (date.today() + timedelta(days=int(expiring_days))).isoformat()
        today_str = date.today().isoformat()
        query += " AND status = 'Available' AND expiry_date >= ? AND expiry_date <= ?"
        params.extend([today_str, target_date])

    query += " ORDER BY expiry_date ASC, id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_unit_by_id(unit_id):
    sync_expired_units()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory WHERE id = ? OR unit_code = ?", (unit_id, unit_id))
    row = cursor.fetchone()
    conn.close()
    return row

def add_inventory_unit(data):
    component_type = data.get("component_type")
    if component_type not in VALID_COMPONENTS:
        raise ValueError(f"Invalid component type: '{component_type}'. Must be one of: {', '.join(VALID_COMPONENTS)}")

    blood_group = data.get("blood_group")
    if blood_group not in VALID_BLOOD_GROUPS:
        raise ValueError(f"Invalid blood group: '{blood_group}'")

    collection_date_str = data.get("collection_date") or date.today().isoformat()
    try:
        coll_dt = datetime.strptime(collection_date_str, "%Y-%m-%d").date()
    except ValueError:
        coll_dt = date.today()
        collection_date_str = coll_dt.isoformat()

    # Calculate default expiry if not provided
    if not data.get("expiry_date"):
        shelf_days = DEFAULT_SHELF_LIFE_DAYS.get(component_type, 35)
        expiry_date_str = (coll_dt + timedelta(days=shelf_days)).isoformat()
    else:
        expiry_date_str = data["expiry_date"]

    unit_code = get_next_code("inventory", "unit_code", "UNIT")
    now_str = datetime.now().isoformat()

    # Determine serology status and initial inventory status
    serology_status = data.get("serology_status", "Pending")
    donation_id = data.get("donation_id")
    donation_code = data.get("donation_code")
    donor_id = data.get("donor_id")
    donor_code = data.get("donor_code")

    if donation_id:
        serology = get_serology_by_donation_id(donation_id)
        if serology:
            serology_status = serology["overall_result"]

    status = data.get("status", "Available")
    # If serology is Reactive, force status to Quarantined
    if serology_status == "Reactive":
        status = "Quarantined"
    elif expiry_date_str < date.today().isoformat():
        status = "Expired"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (
            unit_code, donation_id, donation_code, donor_id, donor_code,
            blood_group, component_type, collection_date, expiry_date,
            volume_ml, status, storage_location, serology_status, remarks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        unit_code,
        donation_id,
        donation_code,
        donor_id,
        donor_code,
        blood_group,
        component_type,
        collection_date_str,
        expiry_date_str,
        int(data.get("volume_ml", 450)),
        status,
        data.get("storage_location", "Main Refrigerator 1").strip(),
        serology_status,
        data.get("remarks", "").strip() or None,
        now_str
    ))
    unit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return unit_id, unit_code

def check_unit_issueability(unit):
    """
    Validates if a blood unit is eligible for issue according to all business rules:
    - RULE 1: Reactive serology cannot be issued
    - RULE 2: Expired unit cannot be issued
    - RULE 3: Discarded unit cannot be issued
    - RULE 4: Already issued unit cannot be issued
    - Status must be 'Available'
    - Serology must be 'Non-Reactive'
    """
    if not unit:
        return False, "Blood unit not found in system."

    if unit["status"] == "Issued":
        return False, f"Blood unit {unit['unit_code']} has already been issued."

    if unit["status"] == "Discarded":
        return False, f"Blood unit {unit['unit_code']} has been discarded and cannot be issued."

    if unit["serology_status"] == "Reactive":
        return False, f"Blood unit {unit['unit_code']} has Reactive serology (Infection detected). Issue is strictly prohibited."

    if unit["serology_status"] == "Pending":
        return False, f"Blood unit {unit['unit_code']} has Pending serology test results. It must be tested Non-Reactive before issuing."

    today_str = date.today().isoformat()
    if unit["expiry_date"] < today_str or unit["status"] == "Expired":
        return False, f"Blood unit {unit['unit_code']} expired on {unit['expiry_date']}. Expired units cannot be issued."

    if unit["status"] != "Available":
        return False, f"Blood unit {unit['unit_code']} is not available (Current status: {unit['status']})."

    return True, "Unit is eligible for issue."

# ==========================================
# ISSUE OPERATIONS
# ==========================================

def get_issues(search=None, blood_group=None, component=None, hospital_id=None, date_from=None, date_to=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM issues WHERE 1=1"
    params = []

    if search:
        s = f"%{search.strip()}%"
        query += " AND (issue_code LIKE ? OR unit_code LIKE ? OR hospital_name LIKE ? OR patient_name LIKE ?)"
        params.extend([s, s, s, s])

    if blood_group and blood_group in VALID_BLOOD_GROUPS:
        query += " AND blood_group = ?"
        params.append(blood_group)

    if component and component in VALID_COMPONENTS:
        query += " AND component_type = ?"
        params.append(component)

    if hospital_id:
        query += " AND hospital_id = ?"
        params.append(hospital_id)

    if date_from:
        query += " AND issue_date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND issue_date <= ?"
        params.append(date_to)

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def issue_unit(data):
    """
    Issues a blood unit to a hospital.
    Applies strict business logic validation.
    """
    unit = get_unit_by_id(data["unit_id"])
    eligible, reason = check_unit_issueability(unit)
    if not eligible:
        raise ValueError(reason)

    hospital = get_hospital_by_id(data["hospital_id"])
    if not hospital:
        raise ValueError("Specified Hospital does not exist.")

    if not data.get("patient_name"):
        raise ValueError("Patient Name is required for issuing blood.")

    if not data.get("issued_by"):
        raise ValueError("Issued By (staff name) is required.")

    issue_code = get_next_code("issues", "issue_code", "ISS")
    issue_date = data.get("issue_date") or date.today().isoformat()
    now_str = datetime.now().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Re-verify inside transaction to prevent race conditions
    cursor.execute("SELECT status, serology_status, expiry_date FROM inventory WHERE id = ?", (unit["id"],))
    cur_unit = cursor.fetchone()
    if cur_unit["status"] != "Available" or cur_unit["serology_status"] != "Non-Reactive" or cur_unit["expiry_date"] < date.today().isoformat():
        conn.close()
        raise ValueError("Unit is no longer available or eligible for issue.")

    cursor.execute("""
        INSERT INTO issues (
            issue_code, issue_date, hospital_id, hospital_code, hospital_name,
            unit_id, unit_code, blood_group, component_type, quantity,
            patient_name, patient_id, doctor_dept, reason, issued_by, remarks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        issue_code,
        issue_date,
        hospital["id"],
        hospital["hospital_code"],
        hospital["name"],
        unit["id"],
        unit["unit_code"],
        unit["blood_group"],
        unit["component_type"],
        1,
        data["patient_name"].strip(),
        data.get("patient_id", "").strip() or None,
        data.get("doctor_dept", "").strip() or None,
        data.get("reason", "").strip() or None,
        data["issued_by"].strip(),
        data.get("remarks", "").strip() or None,
        now_str
    ))
    issue_id = cursor.lastrowid

    # Update inventory status to 'Issued'
    cursor.execute("UPDATE inventory SET status = 'Issued' WHERE id = ?", (unit["id"],))

    conn.commit()
    conn.close()
    return issue_id, issue_code

# ==========================================
# DISCARD OPERATIONS
# ==========================================

def get_discards(search=None, component=None, blood_group=None, reason=None, date_from=None, date_to=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM discard_records WHERE 1=1"
    params = []

    if search:
        s = f"%{search.strip()}%"
        query += " AND (discard_code LIKE ? OR unit_code LIKE ? OR authorized_by LIKE ?)"
        params.extend([s, s, s])

    if component and component in VALID_COMPONENTS:
        query += " AND component_type = ?"
        params.append(component)

    if blood_group and blood_group in VALID_BLOOD_GROUPS:
        query += " AND blood_group = ?"
        params.append(blood_group)

    if reason:
        query += " AND reason = ?"
        params.append(reason)

    if date_from:
        query += " AND discard_date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND discard_date <= ?"
        params.append(date_to)

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def discard_unit(data):
    unit = get_unit_by_id(data["unit_id"])
    if not unit:
        raise ValueError("Specified Unit does not exist.")

    if unit["status"] == "Issued":
        raise ValueError(f"Unit {unit['unit_code']} has already been issued to a patient and cannot be discarded.")

    if unit["status"] == "Discarded":
        raise ValueError(f"Unit {unit['unit_code']} is already marked as Discarded.")

    if not data.get("reason"):
        raise ValueError("Reason for discard is required.")

    if not data.get("authorized_by"):
        raise ValueError("Authorized By is required for discarding blood units.")

    discard_code = get_next_code("discard_records", "discard_code", "DISC")
    discard_date = data.get("discard_date") or date.today().isoformat()
    now_str = datetime.now().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO discard_records (
            discard_code, unit_id, unit_code, blood_group, component_type,
            discard_date, reason, quantity, authorized_by, remarks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        discard_code,
        unit["id"],
        unit["unit_code"],
        unit["blood_group"],
        unit["component_type"],
        discard_date,
        data["reason"].strip(),
        1,
        data["authorized_by"].strip(),
        data.get("remarks", "").strip() or None,
        now_str
    ))
    discard_id = cursor.lastrowid

    # Update inventory unit status
    cursor.execute("UPDATE inventory SET status = 'Discarded' WHERE id = ?", (unit["id"],))

    conn.commit()
    conn.close()
    return discard_id, discard_code

# ==========================================
# HOSPITAL OPERATIONS
# ==========================================

def get_hospitals(search=None, status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM hospitals WHERE 1=1"
    params = []

    if search:
        s = f"%{search.strip()}%"
        query += " AND (hospital_code LIKE ? OR name LIKE ? OR phone LIKE ? OR contact_person LIKE ?)"
        params.extend([s, s, s, s])

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_hospital_by_id(hospital_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hospitals WHERE id = ? OR hospital_code = ?", (hospital_id, hospital_id))
    row = cursor.fetchone()
    conn.close()
    return row

def create_hospital(data):
    if not data.get("name") or not data.get("phone"):
        raise ValueError("Hospital Name and Phone are required fields.")

    hospital_code = get_next_code("hospitals", "hospital_code", "HOSP")
    now_str = datetime.now().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hospitals (
            hospital_code, name, contact_person, phone, email,
            address, license_number, status, remarks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        hospital_code,
        data["name"].strip(),
        data.get("contact_person", "").strip() or None,
        data["phone"].strip(),
        data.get("email", "").strip() or None,
        data.get("address", "").strip() or None,
        data.get("license_number", "").strip() or None,
        data.get("status", "Active"),
        data.get("remarks", "").strip() or None,
        now_str
    ))
    hosp_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return hosp_id, hospital_code

def update_hospital(hospital_id, data):
    if not data.get("name") or not data.get("phone"):
        raise ValueError("Hospital Name and Phone are required.")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE hospitals SET
            name = ?, contact_person = ?, phone = ?, email = ?,
            address = ?, license_number = ?, status = ?, remarks = ?
        WHERE id = ?
    """, (
        data["name"].strip(),
        data.get("contact_person", "").strip() or None,
        data["phone"].strip(),
        data.get("email", "").strip() or None,
        data.get("address", "").strip() or None,
        data.get("license_number", "").strip() or None,
        data.get("status", "Active"),
        data.get("remarks", "").strip() or None,
        hospital_id
    ))
    conn.commit()
    conn.close()

def delete_hospital(hospital_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM issues WHERE hospital_id = ?", (hospital_id,))
    res = cursor.fetchone()
    if res and res["count"] > 0:
        conn.close()
        raise ValueError("Cannot delete hospital with associated issue records. Set status to Inactive instead.")

    cursor.execute("DELETE FROM hospitals WHERE id = ?", (hospital_id,))
    conn.commit()
    conn.close()

# ==========================================
# STOCK & DASHBOARD CALCULATIONS
# ==========================================

def get_stock_matrix(component_filter=None, blood_group_filter=None):
    """
    Computes real-time dynamic inventory counts grouped by Component and Blood Group.
    Columns: Component, Blood Group, Available, Issued, Discarded, Expired, Total
    """
    sync_expired_units()
    today_str = date.today().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            component_type,
            blood_group,
            SUM(CASE WHEN status = 'Available' AND serology_status = 'Non-Reactive' AND expiry_date >= ? THEN 1 ELSE 0 END) AS available_count,
            SUM(CASE WHEN status = 'Issued' THEN 1 ELSE 0 END) AS issued_count,
            SUM(CASE WHEN status = 'Discarded' THEN 1 ELSE 0 END) AS discarded_count,
            SUM(CASE WHEN status = 'Expired' OR (status = 'Available' AND expiry_date < ?) THEN 1 ELSE 0 END) AS expired_count,
            COUNT(*) AS total_count
        FROM inventory
        WHERE 1=1
    """
    params = [today_str, today_str]

    if component_filter and component_filter in VALID_COMPONENTS:
        query += " AND component_type = ?"
        params.append(component_filter)

    if blood_group_filter and blood_group_filter in VALID_BLOOD_GROUPS:
        query += " AND blood_group = ?"
        params.append(blood_group_filter)

    query += " GROUP BY component_type, blood_group ORDER BY component_type, blood_group"
    cursor.execute(query, params)
    raw_rows = cursor.fetchall()
    conn.close()

    # Build full matrix including 0 rows when not filtered to single group
    # Ensure all 4 components and blood groups are presented cleanly
    comps_to_show = [component_filter] if component_filter in VALID_COMPONENTS else VALID_COMPONENTS
    groups_to_show = [blood_group_filter] if blood_group_filter in VALID_BLOOD_GROUPS else VALID_BLOOD_GROUPS

    lookup = {}
    for r in raw_rows:
        lookup[(r["component_type"], r["blood_group"])] = {
            "available": r["available_count"] or 0,
            "issued": r["issued_count"] or 0,
            "discarded": r["discarded_count"] or 0,
            "expired": r["expired_count"] or 0,
            "total": r["total_count"] or 0
        }

    matrix = []
    for comp in comps_to_show:
        for bg in groups_to_show:
            counts = lookup.get((comp, bg), {"available": 0, "issued": 0, "discarded": 0, "expired": 0, "total": 0})
            matrix.append({
                "component": comp,
                "blood_group": bg,
                "available": counts["available"],
                "issued": counts["issued"],
                "discarded": counts["discarded"],
                "expired": counts["expired"],
                "total": counts["total"]
            })

    return matrix

def get_dashboard_metrics():
    sync_expired_units()
    today_str = date.today().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total Donors
    cursor.execute("SELECT COUNT(*) as count FROM donors")
    total_donors = cursor.fetchone()["count"]

    # Total Donations
    cursor.execute("SELECT COUNT(*) as count FROM donations")
    total_donations = cursor.fetchone()["count"]

    # Available Units Overall
    cursor.execute("""
        SELECT COUNT(*) as count FROM inventory
        WHERE status = 'Available' AND serology_status = 'Non-Reactive' AND expiry_date >= ?
    """, (today_str,))
    available_units = cursor.fetchone()["count"]

    # Component-wise Available Units (Whole Blood, PRBC, FFP, Platelets)
    comp_counts = {}
    for comp in VALID_COMPONENTS:
        cursor.execute("""
            SELECT COUNT(*) as count FROM inventory
            WHERE component_type = ? AND status = 'Available' AND serology_status = 'Non-Reactive' AND expiry_date >= ?
        """, (comp, today_str))
        comp_counts[comp] = cursor.fetchone()["count"]

    # Units Issued
    cursor.execute("SELECT COUNT(*) as count FROM issues")
    units_issued = cursor.fetchone()["count"]

    # Units Discarded
    cursor.execute("SELECT COUNT(*) as count FROM discard_records")
    units_discarded = cursor.fetchone()["count"]

    # Stock Settings & Low Stock Alerts
    cursor.execute("SELECT component_type, min_stock_level, expiring_days_threshold FROM stock_settings")
    settings = {
        r["component_type"]: {
            "min_stock_level": r["min_stock_level"],
            "expiring_days_threshold": r["expiring_days_threshold"]
        }
        for r in cursor.fetchall()
    }

    low_stock_alerts = []
    for comp in VALID_COMPONENTS:
        curr_stock = comp_counts.get(comp, 0)
        min_stock = settings.get(comp, {}).get("min_stock_level", 10)
        if curr_stock < min_stock:
            low_stock_alerts.append({
                "component": comp,
                "current": curr_stock,
                "min": min_stock,
                "shortfall": min_stock - curr_stock
            })

    # Expiring Soon (default threshold 7 days)
    threshold_days = settings.get("Whole Blood", {}).get("expiring_days_threshold", 7)
    target_exp_date = (date.today() + timedelta(days=threshold_days)).isoformat()
    cursor.execute("""
        SELECT COUNT(*) as count FROM inventory
        WHERE status = 'Available' AND serology_status = 'Non-Reactive'
        AND expiry_date >= ? AND expiry_date <= ?
    """, (today_str, target_exp_date))
    expiring_soon_count = cursor.fetchone()["count"]

    conn.close()

    return {
        "total_donors": total_donors,
        "total_donations": total_donations,
        "available_units": available_units,
        "whole_blood": comp_counts.get("Whole Blood", 0),
        "prbc": comp_counts.get("PRBC", 0),
        "ffp": comp_counts.get("FFP", 0),
        "platelets": comp_counts.get("Platelets", 0),
        "units_issued": units_issued,
        "units_discarded": units_discarded,
        "low_stock_items": low_stock_alerts,
        "low_stock_count": len(low_stock_alerts),
        "expiring_soon_count": expiring_soon_count
    }

def get_chart_data():
    """Returns aggregated data for offline Vanilla JS / SVG chart generation."""
    sync_expired_units()
    today = date.today()
    today_str = today.isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Component distribution of available stock
    comp_dist = {}
    for comp in VALID_COMPONENTS:
        cursor.execute("""
            SELECT COUNT(*) as count FROM inventory
            WHERE component_type = ? AND status = 'Available' AND serology_status = 'Non-Reactive' AND expiry_date >= ?
        """, (comp, today_str))
        comp_dist[comp] = cursor.fetchone()["count"]

    # 2. Blood group distribution across available stock
    bg_dist = {}
    for bg in VALID_BLOOD_GROUPS:
        cursor.execute("""
            SELECT COUNT(*) as count FROM inventory
            WHERE blood_group = ? AND status = 'Available' AND serology_status = 'Non-Reactive' AND expiry_date >= ?
        """, (bg, today_str))
        bg_dist[bg] = cursor.fetchone()["count"]

    # 3. Monthly donations for the past 6 months
    monthly_donations = []
    monthly_issues = []
    months_labels = []

    for i in range(5, -1, -1):
        # Calculate year-month
        m_date = today.replace(day=1) - timedelta(days=i*30)
        month_str = m_date.strftime("%Y-%m")
        label = m_date.strftime("%b %Y")
        months_labels.append(label)

        cursor.execute("SELECT COUNT(*) as count FROM donations WHERE donation_date LIKE ?", (f"{month_str}%",))
        monthly_donations.append(cursor.fetchone()["count"])

        cursor.execute("SELECT COUNT(*) as count FROM issues WHERE issue_date LIKE ?", (f"{month_str}%",))
        monthly_issues.append(cursor.fetchone()["count"])

    conn.close()

    return {
        "component_distribution": comp_dist,
        "blood_group_distribution": bg_dist,
        "monthly_labels": months_labels,
        "monthly_donations": monthly_donations,
        "monthly_issues": monthly_issues
    }
