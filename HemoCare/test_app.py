import os
import unittest
from datetime import datetime, date, timedelta
from app import app
from database import (
    init_db, get_db_connection,
    VALID_COMPONENTS, VALID_BLOOD_GROUPS
)
import models
import report_generator
from seed_data import seed_database

class HemoCareTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        seed_database()

    def setUp(self):
        self.client = app.test_client()

    def login_admin(self):
        return self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)

    # 1. Login
    def test_01_login_success(self):
        response = self.login_admin()
        self.assertIn(b"Dashboard", response.data)
        self.assertIn(b"Operational Overview", response.data)

    # 2. Add donor
    def test_02_add_donor(self):
        self.login_admin()
        response = self.client.post("/donors/add", data={
            "name": "Sarah Connor",
            "blood_group": "O+",
            "age": "29",
            "gender": "Female",
            "phone": "+1 555-099-8877",
            "email": "sarah.c@example.com",
            "donor_type": "Voluntary",
            "status": "Active"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sarah Connor", response.data)

        donor = models.get_donors(search="Sarah Connor")[0]
        self.assertEqual(donor["blood_group"], "O+")

    # 3. Add donation
    def test_03_add_donation(self):
        self.login_admin()
        donor = models.get_donors(search="Sarah Connor")[0]
        response = self.client.post("/donations/add", data={
            "donor_id": donor["id"],
            "donation_date": date.today().isoformat(),
            "donation_type": "Voluntary",
            "volume_ml": "450",
            "bag_number": "BAG-TEST-001",
            "component_to_create": "Whole Blood",
            "storage_location": "Quarantine Fridge"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"BAG-TEST-001", response.data)

    # 4. Add serology
    def test_04_add_serology(self):
        self.login_admin()
        donations = models.get_donations(search="BAG-TEST-001")
        self.assertTrue(len(donations) > 0)
        don = donations[0]

        response = self.client.post("/serology/record", data={
            "donation_id": don["id"],
            "test_date": date.today().isoformat(),
            "hiv": "Non-Reactive",
            "hbsag": "Non-Reactive",
            "hcv": "Non-Reactive",
            "syphilis": "Non-Reactive",
            "malaria": "Non-Reactive",
            "overall_result": "Non-Reactive",
            "remarks": "All negative"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        serology = models.get_serology_by_donation_id(don["id"])
        self.assertEqual(serology["overall_result"], "Non-Reactive")

    # 5. Create inventory
    def test_05_create_inventory(self):
        unit_data = {
            "component_type": "Whole Blood",
            "blood_group": "O+",
            "collection_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=35)).isoformat(),
            "volume_ml": 450,
            "status": "Available",
            "storage_location": "Main Fridge Shelf A",
            "serology_status": "Non-Reactive"
        }
        unit_id, unit_code = models.add_inventory_unit(unit_data)
        self.assertIsNotNone(unit_id)
        self.assertTrue(unit_code.startswith("UNIT"))

    # 6. Add Whole Blood
    def test_06_add_whole_blood(self):
        unit_id, unit_code = models.add_inventory_unit({
            "component_type": "Whole Blood",
            "blood_group": "A+",
            "collection_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=35)).isoformat(),
            "volume_ml": 450,
            "status": "Available",
            "storage_location": "Main Storage WB-1",
            "serology_status": "Non-Reactive"
        })
        unit = models.get_unit_by_id(unit_id)
        self.assertEqual(unit["component_type"], "Whole Blood")

    # 7. Add PRBC
    def test_07_add_prbc(self):
        unit_id, unit_code = models.add_inventory_unit({
            "component_type": "PRBC",
            "blood_group": "B+",
            "collection_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=42)).isoformat(),
            "volume_ml": 280,
            "status": "Available",
            "storage_location": "Main Storage PRBC-1",
            "serology_status": "Non-Reactive"
        })
        unit = models.get_unit_by_id(unit_id)
        self.assertEqual(unit["component_type"], "PRBC")

    # 8. Add FFP
    def test_08_add_ffp(self):
        unit_id, unit_code = models.add_inventory_unit({
            "component_type": "FFP",
            "blood_group": "AB+",
            "collection_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=365)).isoformat(),
            "volume_ml": 200,
            "status": "Available",
            "storage_location": "Freezer -20C FFP-1",
            "serology_status": "Non-Reactive"
        })
        unit = models.get_unit_by_id(unit_id)
        self.assertEqual(unit["component_type"], "FFP")

    # 9. Add Platelets
    def test_09_add_platelets(self):
        unit_id, unit_code = models.add_inventory_unit({
            "component_type": "Platelets",
            "blood_group": "O-",
            "collection_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=5)).isoformat(),
            "volume_ml": 60,
            "status": "Available",
            "storage_location": "Agitator PLT-1",
            "serology_status": "Non-Reactive"
        })
        unit = models.get_unit_by_id(unit_id)
        self.assertEqual(unit["component_type"], "Platelets")

    # 10. Issue eligible unit
    def test_10_issue_eligible_unit(self):
        # Create fresh eligible unit
        unit_id, unit_code = models.add_inventory_unit({
            "component_type": "Whole Blood",
            "blood_group": "O+",
            "collection_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=35)).isoformat(),
            "volume_ml": 450,
            "status": "Available",
            "storage_location": "Fridge 1",
            "serology_status": "Non-Reactive"
        })
        issue_id, issue_code = models.issue_unit({
            "unit_id": unit_id,
            "hospital_id": 1,
            "patient_name": "John Smith",
            "issued_by": "Dr. Davis",
            "issue_date": date.today().isoformat()
        })
        self.assertIsNotNone(issue_id)

        # Check unit status transitioned to 'Issued'
        unit = models.get_unit_by_id(unit_id)
        self.assertEqual(unit["status"], "Issued")

    # 11. Prevent duplicate issue
    def test_11_prevent_duplicate_issue(self):
        # Create and issue unit
        unit_id, _ = models.add_inventory_unit({
            "component_type": "PRBC",
            "blood_group": "A+",
            "collection_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=42)).isoformat(),
            "volume_ml": 280,
            "status": "Available",
            "storage_location": "Fridge 2",
            "serology_status": "Non-Reactive"
        })
        models.issue_unit({
            "unit_id": unit_id,
            "hospital_id": 1,
            "patient_name": "Patient A",
            "issued_by": "Officer A"
        })

        # Attempting second issue must fail
        with self.assertRaises(ValueError) as ctx:
            models.issue_unit({
                "unit_id": unit_id,
                "hospital_id": 2,
                "patient_name": "Patient B",
                "issued_by": "Officer B"
            })
        self.assertIn("already been issued", str(ctx.exception))

    # 12. Prevent reactive unit issue
    def test_12_prevent_reactive_unit_issue(self):
        unit_id, _ = models.add_inventory_unit({
            "component_type": "Whole Blood",
            "blood_group": "B+",
            "collection_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=35)).isoformat(),
            "volume_ml": 450,
            "status": "Quarantined",
            "storage_location": "Quarantine Fridge",
            "serology_status": "Reactive"
        })
        with self.assertRaises(ValueError) as ctx:
            models.issue_unit({
                "unit_id": unit_id,
                "hospital_id": 1,
                "patient_name": "Emergency Patient",
                "issued_by": "Officer"
            })
        self.assertIn("Reactive", str(ctx.exception))

    # 13. Prevent expired unit issue
    def test_13_prevent_expired_unit_issue(self):
        past_date = (date.today() - timedelta(days=5)).isoformat()
        unit_id, _ = models.add_inventory_unit({
            "component_type": "Whole Blood",
            "blood_group": "O-",
            "collection_date": (date.today() - timedelta(days=40)).isoformat(),
            "expiry_date": past_date,
            "volume_ml": 450,
            "status": "Available",
            "storage_location": "Fridge 1",
            "serology_status": "Non-Reactive"
        })
        with self.assertRaises(ValueError) as ctx:
            models.issue_unit({
                "unit_id": unit_id,
                "hospital_id": 1,
                "patient_name": "Trauma Patient",
                "issued_by": "Officer"
            })
        self.assertIn("expired", str(ctx.exception).lower())

    # 14. Discard unit
    def test_14_discard_unit(self):
        unit_id, _ = models.add_inventory_unit({
            "component_type": "Platelets",
            "blood_group": "A-",
            "collection_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=5)).isoformat(),
            "volume_ml": 50,
            "status": "Available",
            "storage_location": "Agitator",
            "serology_status": "Non-Reactive"
        })
        discard_id, discard_code = models.discard_unit({
            "unit_id": unit_id,
            "reason": "Damaged Bag",
            "authorized_by": "Medical Director"
        })
        self.assertIsNotNone(discard_id)
        unit = models.get_unit_by_id(unit_id)
        self.assertEqual(unit["status"], "Discarded")

    # 15. Prevent discarded unit issue
    def test_15_prevent_discarded_unit_issue(self):
        unit_id, _ = models.add_inventory_unit({
            "component_type": "FFP",
            "blood_group": "O+",
            "collection_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=365)).isoformat(),
            "volume_ml": 200,
            "status": "Available",
            "storage_location": "Freezer",
            "serology_status": "Non-Reactive"
        })
        models.discard_unit({
            "unit_id": unit_id,
            "reason": "Storage Issue",
            "authorized_by": "Chief Tech"
        })
        with self.assertRaises(ValueError) as ctx:
            models.issue_unit({
                "unit_id": unit_id,
                "hospital_id": 1,
                "patient_name": "Patient X",
                "issued_by": "Officer"
            })
        self.assertIn("discarded", str(ctx.exception).lower())

    # 16. Stock calculation
    def test_16_stock_calculation(self):
        matrix = models.get_stock_matrix()
        self.assertTrue(len(matrix) > 0)
        for row in matrix:
            self.assertIn(row["component"], VALID_COMPONENTS)
            self.assertIn(row["blood_group"], VALID_BLOOD_GROUPS)
            self.assertGreaterEqual(row["available"], 0)
            self.assertGreaterEqual(row["total"], 0)

    # 17. Low stock alert
    def test_17_low_stock_alert(self):
        metrics = models.get_dashboard_metrics()
        self.assertIn("low_stock_items", metrics)
        self.assertIn("low_stock_count", metrics)
        self.assertIsInstance(metrics["low_stock_items"], list)

    # 18. Excel export
    def test_18_excel_export(self):
        for rep in ["stock", "donors", "donations", "inventory", "issues", "discards"]:
            excel_io = report_generator.generate_excel_report(rep)
            self.assertIsNotNone(excel_io)
            excel_bytes = excel_io.getvalue()
            self.assertTrue(len(excel_bytes) > 100)
            # Excel files start with PK zip header
            self.assertEqual(excel_bytes[:2], b"PK")

    # 19. PDF export
    def test_19_pdf_export(self):
        for rep in ["stock", "donors", "inventory", "issues"]:
            pdf_io = report_generator.generate_pdf_report(rep)
            self.assertIsNotNone(pdf_io)
            pdf_bytes = pdf_io.getvalue()
            self.assertTrue(len(pdf_bytes) > 100)
            # PDF starts with %PDF
            self.assertEqual(pdf_bytes[:4], b"%PDF")

    # 20. Logout
    def test_20_logout(self):
        self.login_admin()
        response = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"logged out", response.data)

        # Confirm dashboard is now inaccessible without login
        dash_response = self.client.get("/dashboard")
        self.assertEqual(dash_response.status_code, 302)

if __name__ == "__main__":
    unittest.main()
