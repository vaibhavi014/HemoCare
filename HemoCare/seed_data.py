import os
from datetime import datetime, date, timedelta
from database import init_db, get_db_connection, VALID_COMPONENTS, VALID_BLOOD_GROUPS
from werkzeug.security import generate_password_hash

def seed_database():
    """Populates realistic demonstration data for HemoCare offline blood bank."""
    print("Initializing database schema...")
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing operational data for clean seed
    cursor.execute("DELETE FROM issues")
    cursor.execute("DELETE FROM discard_records")
    cursor.execute("DELETE FROM inventory")
    cursor.execute("DELETE FROM serology")
    cursor.execute("DELETE FROM donations")
    cursor.execute("DELETE FROM donors")
    cursor.execute("DELETE FROM hospitals")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('issues', 'discard_records', 'inventory', 'serology', 'donations', 'donors', 'hospitals')")

    today = date.today()
    today_str = today.isoformat()

    print("Seeding hospitals...")
    hospitals_data = [
        ("HOSP0001", "City General Medical Center", "Dr. Sarah Jenkins", "+1 555-010-1001", "transfusion@citygeneral.org", "100 Hospital Way, Metro City", "LIC-HOSP-2021-001", "Active", "Level 1 Trauma Center, 24/7 emergency reserve quota."),
        ("HOSP0002", "St. Jude Children's Hospital", "Dr. Marcus Vance", "+1 555-010-2002", "bloodbank@stjude.org", "45 Pediatrics Boulevard, Metro City", "LIC-HOSP-2022-045", "Active", "Specialized pediatric hematology & oncology."),
        ("HOSP0003", "Metro Emergency Specialty Clinic", "Nurse Elena Rostova", "+1 555-010-3003", "er@metroemergency.org", "12 Fast-Track Avenue, North Suburb", "LIC-HOSP-2023-112", "Active", "Surgical trauma care."),
        ("HOSP0004", "Valley Memorial Care Center", "Dr. Raymond Shaw", "+1 555-010-4004", "rshaw@valleymemorial.com", "88 River Valley Road, Valley Town", "LIC-HOSP-2020-089", "Active", "Orthopedic & cardiovascular surgery."),
        ("HOSP0005", "Highland Regional Clinic", "Admin Grace Lee", "+1 555-010-5005", "contact@highlandclinic.org", "300 Mountain View Rd, Highland", "LIC-HOSP-2024-004", "Inactive", "Routine elective surgery facility (currently on maintenance).")
    ]
    cursor.executemany("""
        INSERT INTO hospitals (hospital_code, name, contact_person, phone, email, address, license_number, status, remarks, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], h[8], today_str) for h in hospitals_data])

    print("Seeding donors...")
    donors_data = [
        ("DNR0001", "Alexander Wright", 29, "Male", "O+", "+1 555-019-1001", "alex.w@example.com", "14 Oak Street, Metro City", "1997-04-12", (today - timedelta(days=20)).isoformat(), "Voluntary", "Active", "Regular voluntary donor; high platelet count."),
        ("DNR0002", "Beatrice Montgomery", 34, "Female", "A+", "+1 555-019-1002", "beatrice.m@example.com", "22 Maple Ave, Metro City", "1992-08-23", (today - timedelta(days=15)).isoformat(), "Voluntary", "Active", "Universal plasma provider (A+)."),
        ("DNR0003", "Christopher Nolan", 41, "Male", "B+", "+1 555-019-1003", "cnolan@example.com", "77 Pine Road, Metro City", "1985-02-18", (today - timedelta(days=10)).isoformat(), "Replacement", "Active", "Donated for surgical relative."),
        ("DNR0004", "Diana Prince", 27, "Female", "O-", "+1 555-019-1004", "diana.p@example.com", "90 Elm Boulevard, Metro City", "1999-11-05", (today - timedelta(days=5)).isoformat(), "Voluntary", "Active", "Universal RBC donor (O negative)."),
        ("DNR0005", "Evan Campbell", 38, "Male", "AB+", "+1 555-019-1005", "evan.c@example.com", "5 Cedar Lane, Valley Town", "1988-06-30", (today - timedelta(days=2)).isoformat(), "Voluntary", "Active", "Universal plasma recipient donor."),
        ("DNR0006", "Fiona Gallagher", 24, "Female", "A-", "+1 555-019-1006", "fiona.g@example.com", "12 Birch Ct, North Suburb", "2002-01-14", (today - timedelta(days=25)).isoformat(), "Voluntary", "Active", "Rare A negative subgroup verified."),
        ("DNR0007", "Gregory House", 52, "Male", "B-", "+1 555-019-1007", "ghouse@example.com", "34 Clinic Road, Metro City", "1974-09-15", (today - timedelta(days=40)).isoformat(), "Voluntary", "Active", "Frequent whole blood donor."),
        ("DNR0008", "Hannah Abbott", 31, "Female", "AB-", "+1 555-019-1008", "hannah.a@example.com", "18 Willow Way, Valley Town", "1995-12-01", (today - timedelta(days=18)).isoformat(), "Voluntary", "Active", "Extremely rare AB- blood donor."),
        ("DNR0009", "Ian Malcolm", 45, "Male", "O+", "+1 555-019-1009", "ian.m@example.com", "404 Island Dr, Metro City", "1981-03-21", (today - timedelta(days=12)).isoformat(), "Replacement", "Active", "Donor for trauma victim."),
        ("DNR0010", "Julia Roberts", 30, "Female", "A+", "+1 555-019-1010", "julia.r@example.com", "75 Broadway, Metro City", "1996-07-09", (today - timedelta(days=8)).isoformat(), "Voluntary", "Active", "Clean health profile."),
        ("DNR0011", "Kevin Bacon", 28, "Male", "B+", "+1 555-019-1011", "kevin.b@example.com", "6 Degrees St, Metro City", "1998-05-19", (today - timedelta(days=35)).isoformat(), "Voluntary", "Deferred", "Deferred for 6 months due to recent international travel."),
        ("DNR0012", "Laura Croft", 33, "Female", "O-", "+1 555-019-1012", "laura.c@example.com", "100 Explorer Way, Metro City", "1993-10-10", (today - timedelta(days=3)).isoformat(), "Voluntary", "Active", "Routine apheresis donor.")
    ]

    cursor.executemany("""
        INSERT INTO donors (donor_code, name, age, gender, blood_group, phone, email, address, dob, last_donation_date, donor_type, status, remarks, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], d[10], d[11], d[12], today_str) for d in donors_data])

    print("Seeding donations & serology...")
    # Donations: 12 donations across the 12 donors
    donations_data = [
        ("DON0001", 1, "DNR0001", "Alexander Wright", "O+", (today - timedelta(days=20)).isoformat(), "Voluntary", 450, "BAG-2026-0001", "Tested", "Normal phlebotomy."),
        ("DON0002", 2, "DNR0002", "Beatrice Montgomery", "A+", (today - timedelta(days=15)).isoformat(), "Voluntary", 450, "BAG-2026-0002", "Tested", "Smooth collection."),
        ("DON0003", 3, "DNR0003", "Christopher Nolan", "B+", (today - timedelta(days=10)).isoformat(), "Replacement", 450, "BAG-2026-0003", "Tested", "Good recovery."),
        ("DON0004", 4, "DNR0004", "Diana Prince", "O-", (today - timedelta(days=5)).isoformat(), "Voluntary", 450, "BAG-2026-0004", "Tested", "Universal donor blood."),
        ("DON0005", 5, "DNR0005", "Evan Campbell", "AB+", (today - timedelta(days=2)).isoformat(), "Voluntary", 450, "BAG-2026-0005", "Tested", "Plasma collection."),
        ("DON0006", 6, "DNR0006", "Fiona Gallagher", "A-", (today - timedelta(days=25)).isoformat(), "Voluntary", 450, "BAG-2026-0006", "Tested", "Rare negative subgroup."),
        ("DON0007", 7, "DNR0007", "Gregory House", "B-", (today - timedelta(days=40)).isoformat(), "Voluntary", 450, "BAG-2026-0007", "Tested", "Whole blood."),
        ("DON0008", 8, "DNR0008", "Hannah Abbott", "AB-", (today - timedelta(days=18)).isoformat(), "Voluntary", 450, "BAG-2026-0008", "Tested", "Whole blood."),
        ("DON0009", 9, "DNR0009", "Ian Malcolm", "O+", (today - timedelta(days=12)).isoformat(), "Replacement", 450, "BAG-2026-0009", "Tested", "Replacement donation."),
        ("DON0010", 10, "DNR0010", "Julia Roberts", "A+", (today - timedelta(days=8)).isoformat(), "Voluntary", 450, "BAG-2026-0010", "Tested", "Clean collection."),
        ("DON0011", 11, "DNR0011", "Kevin Bacon", "B+", (today - timedelta(days=35)).isoformat(), "Voluntary", 450, "BAG-2026-0011", "Discarded", "Tested REACTIVE for HBsAg - Discarded!"),
        ("DON0012", 12, "DNR0012", "Laura Croft", "O-", (today - timedelta(days=3)).isoformat(), "Voluntary", 450, "BAG-2026-0012", "Collected", "Pending laboratory screening.")
    ]

    cursor.executemany("""
        INSERT INTO donations (donation_code, donor_id, donor_code, donor_name, blood_group, donation_date, donation_type, volume_ml, bag_number, status, remarks, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(dn[0], dn[1], dn[2], dn[3], dn[4], dn[5], dn[6], dn[7], dn[8], dn[9], dn[10], today_str) for dn in donations_data])

    # Serology records for DON0001 - DON0011 (DON0012 is pending)
    # Note: DON0011 is REACTIVE for HBsAg!
    serology_data = [
        ("SER0001", 1, "DON0001", 1, "DNR0001", "Alexander Wright", "O+", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", (today - timedelta(days=19)).isoformat(), "ELISA test negative across all panels."),
        ("SER0002", 2, "DON0002", 2, "DNR0002", "Beatrice Montgomery", "A+", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", (today - timedelta(days=14)).isoformat(), "Screened negative."),
        ("SER0003", 3, "DON0003", 3, "DNR0003", "Christopher Nolan", "B+", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", (today - timedelta(days=9)).isoformat(), "Screened negative."),
        ("SER0004", 4, "DON0004", 4, "DNR0004", "Diana Prince", "O-", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", (today - timedelta(days=4)).isoformat(), "Screened negative."),
        ("SER0005", 5, "DON0005", 5, "DNR0005", "Evan Campbell", "AB+", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", (today - timedelta(days=1)).isoformat(), "Screened negative."),
        ("SER0006", 6, "DON0006", 6, "DNR0006", "Fiona Gallagher", "A-", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", (today - timedelta(days=24)).isoformat(), "Screened negative."),
        ("SER0007", 7, "DON0007", 7, "DNR0007", "Gregory House", "B-", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", (today - timedelta(days=39)).isoformat(), "Screened negative."),
        ("SER0008", 8, "DON0008", 8, "DNR0008", "Hannah Abbott", "AB-", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", (today - timedelta(days=17)).isoformat(), "Screened negative."),
        ("SER0009", 9, "DON0009", 9, "DNR0009", "Ian Malcolm", "O+", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", (today - timedelta(days=11)).isoformat(), "Screened negative."),
        ("SER0010", 10, "DON0010", 10, "DNR0010", "Julia Roberts", "A+", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", (today - timedelta(days=7)).isoformat(), "Screened negative."),
        ("SER0011", 11, "DON0011", 11, "DNR0011", "Kevin Bacon", "B+", "Non-Reactive", "Reactive", "Non-Reactive", "Non-Reactive", "Non-Reactive", "Reactive", (today - timedelta(days=34)).isoformat(), "POSITIVE for Hepatitis B Surface Antigen (HBsAg). Unit Quarantined and Discarded.")
    ]

    cursor.executemany("""
        INSERT INTO serology (serology_code, donation_id, donation_code, donor_id, donor_code, donor_name, blood_group, hiv, hbsag, hcv, syphilis, malaria, overall_result, test_date, remarks, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9], s[10], s[11], s[12], s[13], s[14], today_str) for s in serology_data])

    print("Seeding inventory units (Whole Blood, PRBC, FFP, Platelets)...")
    # Demonstrating all conditions:
    # - Available units for all 4 components
    # - Issued units
    # - Discarded units
    # - Expired units
    # - Expiring soon units (within 7 days)
    # - Reactive serology unit (quarantined)

    # Shelf lives: Whole Blood: 35d, PRBC: 42d, FFP: 365d, Platelets: 5d
    inventory_data = [
        # Unit 1: Whole Blood (Available) - O+
        ("UNIT0001", 1, "DON0001", 1, "DNR0001", "O+", "Whole Blood", (today - timedelta(days=20)).isoformat(), (today + timedelta(days=15)).isoformat(), 450, "Available", "Main Refrigerator 1 (Shelf A)", "Non-Reactive", "Standard whole blood available."),
        
        # Unit 2: PRBC (Issued) - A+
        ("UNIT0002", 2, "DON0002", 2, "DNR0002", "A+", "PRBC", (today - timedelta(days=15)).isoformat(), (today + timedelta(days=27)).isoformat(), 280, "Issued", "Main Refrigerator 2", "Non-Reactive", "Issued to City General Hospital for surgery."),

        # Unit 3: FFP (Available) - B+
        ("UNIT0003", 3, "DON0003", 3, "DNR0003", "B+", "FFP", (today - timedelta(days=10)).isoformat(), (today + timedelta(days=355)).isoformat(), 200, "Available", "Deep Freezer -25C (Shelf 1)", "Non-Reactive", "Fresh Frozen Plasma in reserve."),

        # Unit 4: Platelets (Expiring soon! 2 days left) - O-
        ("UNIT0004", 4, "DON0004", 4, "DNR0004", "O-", "Platelets", (today - timedelta(days=3)).isoformat(), (today + timedelta(days=2)).isoformat(), 60, "Available", "Platelet Agitator 1", "Non-Reactive", "Expiring soon; priority for emergency trauma issue."),

        # Unit 5: Whole Blood (Available) - AB+
        ("UNIT0005", 5, "DON0005", 5, "DNR0005", "AB+", "Whole Blood", (today - timedelta(days=2)).isoformat(), (today + timedelta(days=33)).isoformat(), 450, "Available", "Main Refrigerator 1 (Shelf B)", "Non-Reactive", "Freshly tested whole blood."),

        # Unit 6: PRBC (Available) - A-
        ("UNIT0006", 6, "DON0006", 6, "DNR0006", "A-", "PRBC", (today - timedelta(days=25)).isoformat(), (today + timedelta(days=17)).isoformat(), 280, "Available", "Main Refrigerator 2 (Shelf A)", "Non-Reactive", "Rare A negative packed red cells."),

        # Unit 7: Whole Blood (Expired!) - B-
        ("UNIT0007", 7, "DON0007", 7, "DNR0007", "B-", "Whole Blood", (today - timedelta(days=40)).isoformat(), (today - timedelta(days=5)).isoformat(), 450, "Expired", "Quarantine Fridge (Discard Section)", "Non-Reactive", "Shelf life exceeded 35 days; marked expired."),

        # Unit 8: FFP (Available) - AB-
        ("UNIT0008", 8, "DON0008", 8, "DNR0008", "AB-", "FFP", (today - timedelta(days=18)).isoformat(), (today + timedelta(days=347)).isoformat(), 200, "Available", "Deep Freezer -25C (Shelf 2)", "Non-Reactive", "Plasma unit available."),

        # Unit 9: PRBC (Available) - O+
        ("UNIT0009", 9, "DON0009", 9, "DNR0009", "O+", "PRBC", (today - timedelta(days=12)).isoformat(), (today + timedelta(days=30)).isoformat(), 280, "Available", "Main Refrigerator 2 (Shelf B)", "Non-Reactive", "High demand O+ PRBC."),

        # Unit 10: Platelets (Discarded due to damaged port) - A+
        ("UNIT0010", 10, "DON0010", 10, "DNR0010", "A+", "Platelets", (today - timedelta(days=8)).isoformat(), (today - timedelta(days=3)).isoformat(), 55, "Discarded", "Biohazard Waste Area", "Non-Reactive", "Discarded due to bag puncture and leakage."),

        # Unit 11: Whole Blood (REACTIVE Serology - Quarantined / Ineligible!) - B+
        ("UNIT0011", 11, "DON0011", 11, "DNR0011", "B+", "Whole Blood", (today - timedelta(days=35)).isoformat(), (today + timedelta(days=0)).isoformat(), 450, "Quarantined", "Infectious Waste Refrigerator", "Reactive", "POSITIVE HBsAg. Strictly prohibited from issue."),

        # Unit 12: Whole Blood (Pending Serology) - O-
        ("UNIT0012", 12, "DON0012", 12, "DNR0012", "O-", "Whole Blood", (today - timedelta(days=3)).isoformat(), (today + timedelta(days=32)).isoformat(), 450, "Available", "Quarantine Cold Room", "Pending", "Awaiting confirmation of TTI screening results."),

        # Unit 13: Whole Blood (Available) - A+
        ("UNIT0013", 2, "DON0002", 2, "DNR0002", "A+", "Whole Blood", (today - timedelta(days=15)).isoformat(), (today + timedelta(days=20)).isoformat(), 450, "Available", "Main Refrigerator 1 (Shelf A)", "Non-Reactive", "Ready for issue."),

        # Unit 14: PRBC (Available) - O-
        ("UNIT0014", 4, "DON0004", 4, "DNR0004", "O-", "PRBC", (today - timedelta(days=5)).isoformat(), (today + timedelta(days=37)).isoformat(), 290, "Available", "Main Refrigerator 2 (Shelf C)", "Non-Reactive", "Emergency universal packed red cells."),

        # Unit 15: Platelets (Available, 4 days left) - B+
        ("UNIT0015", 3, "DON0003", 3, "DNR0003", "B+", "Platelets", (today - timedelta(days=1)).isoformat(), (today + timedelta(days=4)).isoformat(), 65, "Available", "Platelet Agitator 1", "Non-Reactive", "Fresh single-donor platelet unit.")
    ]

    cursor.executemany("""
        INSERT INTO inventory (unit_code, donation_id, donation_code, donor_id, donor_code, blood_group, component_type, collection_date, expiry_date, volume_ml, status, storage_location, serology_status, remarks, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(u[0], u[1], u[2], u[3], u[4], u[5], u[6], u[7], u[8], u[9], u[10], u[11], u[12], u[13], today_str) for u in inventory_data])

    print("Seeding issues...")
    issues_data = [
        ("ISS0001", (today - timedelta(days=10)).isoformat(), 1, "HOSP0001", "City General Medical Center", 2, "UNIT0002", "A+", "PRBC", 1, "Robert Downey", "MRN-9021", "Dr. Vance / Emergency Surgery", "Acute blood loss following motor vehicle trauma.", "Dr. Michael Chen", "Crossmatch compatible, issue approved.")
    ]
    cursor.executemany("""
        INSERT INTO issues (issue_code, issue_date, hospital_id, hospital_code, hospital_name, unit_id, unit_code, blood_group, component_type, quantity, patient_name, patient_id, doctor_dept, reason, issued_by, remarks, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7], i[8], i[9], i[10], i[11], i[12], i[13], i[14], i[15], today_str) for i in issues_data])

    print("Seeding discard records...")
    discard_data = [
        ("DISC0001", 10, "UNIT0010", "A+", "Platelets", (today - timedelta(days=3)).isoformat(), "Damaged Bag", 1, "Chief Technologist Adams", "Bag port cracked during agitation; condemned immediately.")
    ]
    cursor.executemany("""
        INSERT INTO discard_records (discard_code, unit_id, unit_code, blood_group, component_type, discard_date, reason, quantity, authorized_by, remarks, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(ds[0], ds[1], ds[2], ds[3], ds[4], ds[5], ds[6], ds[7], ds[8], ds[9], today_str) for ds in discard_data])

    conn.commit()
    conn.close()
    print("Seed data successfully created! All 4 components (Whole Blood, PRBC, FFP, Platelets) populated.")

if __name__ == "__main__":
    seed_database()
