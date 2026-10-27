# HEMOCARE: Offline Blood Bank Management System

> **Safe Blood — Healthier Tomorrow**

**HEMOCARE** is a complete, free, standalone, 100% offline Blood Bank Management System engineered with Python 3, Flask, and SQLite. It provides hospital transfusion centers, mobile blood drives, and regional storage facilities with mission-critical blood inventory tracking, donor records management, serology infection screening (TTI), hospital blood dispatch slips, biohazard discard documentation, low-stock safety alerts, and comprehensive Excel and PDF reporting—all running without an active internet connection or external cloud dependencies.

---

## Key Features

1. **100% Offline Architecture (Zero-CDN, Zero-Cloud)**:
   - Self-contained local CSS and vanilla JavaScript.
   - Built-in HTML5 Canvas charts for real-time visualization of stock, monthly donations, hospital issues, and component distribution.
   - Operates flawlessly in air-gapped facilities and disaster recovery setups.

2. **Strict Component Lifecycle & Zero-Cryo Enforcement**:
   - Manages exactly four approved therapeutic blood components:
     1. **Whole Blood** (Shelf Life: 35 days)
     2. **PRBC** - Packed Red Blood Cells (Shelf Life: 42 days)
     3. **FFP** - Fresh Frozen Plasma (Shelf Life: 365 days)
     4. **Platelets** - Random Donor Platelets / Apheresis (Shelf Life: 5 days)
   - *Only the four approved components are supported across all data models, UI dropdowns, database schemas, and reports.*

3. **Donor Master Module**:
   - Sequential Donor ID generation (`DNR0001`, `DNR0002`, ...).
   - Validated ABO/Rh blood groups (`A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-`).
   - Donor demographics, eligibility status (`Active`, `Inactive`, `Deferred`), donation intervals, and medical notes.

4. **Donation Register**:
   - Automated sequential collection codes (`DON0001`, `DON0002`, ...).
   - Auto-population of donor details (name, blood group, age) upon donor selection.
   - Volume tracking (350 mL, 450 mL), barcode/bag logging, and instant inventory unit registration.

5. **Serology Screening Register (Transfusion-Transmissible Infections - TTI)**:
   - Mandatory 5-panel screening: **HIV 1 & 2**, **HBsAg (Hepatitis B)**, **HCV (Hepatitis C)**, **Syphilis (VDRL)**, and **Malaria**.
   - Automated Overall Result logic:
     - **Reactive** if ANY single test is positive &rarr; *Automated quarantine; issue strictly prohibited*.
     - **Non-Reactive** if ALL five tests are negative &rarr; *Released to available stock*.
     - **Pending** if testing is incomplete.

6. **Component Inventory & Issueability Verification**:
   - Sequential unit tracking (`UNIT0001`, `UNIT0002`, ...).
   - Real-time enforcement of five core safety rules:
     - **RULE 1**: Reactive serology &rarr; Unit cannot be issued.
     - **RULE 2**: Expired unit (Expiry Date < Current Date) &rarr; Unit cannot be issued.
     - **RULE 3**: Discarded unit &rarr; Unit cannot be issued.
     - **RULE 4**: Issued unit &rarr; Unit cannot be issued again (no duplicate issues).
     - **RULE 5**: Only Non-Reactive, unexpired, and available units contribute to available stock.

7. **Issue Register (Hospital Dispatches)**:
   - Automated dispatch slip codes (`ISS0001`, `ISS0002`, ...).
   - Live eligibility check on unit selection with real-time UI banners.
   - Hospital allocation, patient identifier, department/doctor, and clinical indication logging.

8. **Discard & Wastage Register**:
   - Sequential discard codes (`DISC0001`, `DISC0002`, ...).
   - Reasons: Expired, Reactive Serology, Damaged Bag, Leakage, Storage Issue, Other.
   - Authorized officer sign-off and permanent quarantine from stock.

9. **Dynamic Stock Matrix & Configurable Alerts**:
   - Real-time stock matrix calculated dynamically across all 4 components and 8 blood groups.
   - Configurable minimum stock thresholds per component (triggers **LOW STOCK** alerts).
   - Configurable aging thresholds (flags units **EXPIRING SOON** within 7 days).

10. **Reports & Exports**:
    - 11 built-in reports: Donor Report, Donation Report, Serology Report, Inventory Report, Component Stock Report, Issue Report, Discard/Wastage Report, Hospital-wise Issue Report, Monthly Blood Bank Report, Low Stock Report, and Expiry Report.
    - **Excel (.xlsx)**: Generated using `openpyxl` with styled headers, zebra striping, auto-fit columns, and freeze panes.
    - **PDF (.pdf)**: Generated using `reportlab` with standard offline fonts, metadata headers, and bordered tables.

---

## Technology Stack

- **Backend**: Python 3.12, Flask 3.1
- **Database**: SQLite 3 (with foreign key enforcement and row factory)
- **Security**: Werkzeug password hashing (`generate_password_hash`, `check_password_hash`), Flask encrypted session authentication
- **Spreadsheets**: `openpyxl`
- **PDF Generation**: `reportlab`, `Pillow`
- **Frontend**: HTML5, Vanilla JavaScript, CSS3 (zero external CDNs, zero Google Fonts, zero npm dependencies)

---

## Folder Structure

```
HemoCare/
│
├── app.py                  # Main Flask application, routing, auth, controllers
├── database.py             # SQLite setup, schema tables, connection helpers
├── models.py               # Domain business logic & validation rules
├── report_generator.py     # 11 dynamic reports, openpyxl Excel & reportlab PDF exports
├── seed_data.py            # Realistic demo data populator
├── test_app.py             # Complete test suite covering 20 requirement test cases
├── requirements.txt        # Python dependency manifest
├── README.md               # Complete documentation
│
├── bloodbank.db            # Embedded SQLite database (auto-generated)
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Master layout with sidebar and alerts
│   ├── login.html          # Authentication view
│   ├── dashboard.html      # 11 metric cards, alert tables, canvas charts
│   ├── donors.html         # Donor Master list & filters
│   ├── donor_form.html     # Add/edit donor
│   ├── donor_view.html     # Donor profile & donation history
│   ├── donations.html      # Donation Register & filters
│   ├── donation_form.html  # Phlebotomy record & auto-fill
│   ├── serology.html       # TTI screening logs
│   ├── serology_form.html  # 5-test screening form & auto calculation
│   ├── inventory.html      # Component inventory table
│   ├── inventory_form.html # Manual/direct unit registration
│   ├── inventory_view.html # Unit inspection & issueability banner
│   ├── issue.html          # Issue slip register
│   ├── issue_form.html     # Issue blood to hospital with live validation
│   ├── discard.html        # Discard & wastage logs
│   ├── discard_form.html   # Biohazard discard logger
│   ├── hospitals.html      # Hospital Master list
│   ├── hospital_form.html  # Add/edit hospital
│   ├── hospital_view.html  # Hospital profile & issue slips
│   ├── stock.html          # Dynamic stock matrix (4 components x 8 blood groups)
│   ├── stock_settings.html # Thresholds configuration
│   ├── reports.html        # Interactive report viewer & export triggers
│   ├── instructions.html   # Standard Operating Procedures & manual
│   ├── 404.html            # Offline friendly 404 error page
│   └── 500.html            # Offline friendly 500 error page
│
├── static/
│   ├── css/
│   │   └── style.css       # Clean medical red theme (100% local CSS)
│   ├── js/
│   │   └── app.js          # Auto-fill, calculation, and Canvas charts
│   └── charts/             # Local charts directory
│
└── reports/                # Local export storage directory
```

---

## Installation & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Windows / macOS / Linux

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Populate Seed Data
To populate realistic demonstration donors, donations, screened inventory, and hospitals:
```bash
python seed_data.py
```

### 3. Start HemoCare
```bash
python app.py
```

### 4. Access the Application
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## Default Login Credentials

| Role | Username | Password |
|---|---|---|
| System Administrator | `admin` | `admin123` |

*Passwords are securely hashed in SQLite using PBKDF2/SHA256 via Werkzeug.*

---

## Running the Automated Test Suite

HemoCare includes a comprehensive test suite validating all 20 business rules and system features:

```bash
python test_app.py
```

### Verified Test Cases:
1. `test_01_login_success`: Validates session authentication and dashboard redirect.
2. `test_02_add_donor`: Tests donor creation with age and blood group validation.
3. `test_03_add_donation`: Verifies collection recording and donor date synchronization.
4. `test_04_add_serology`: Tests 5-panel TTI screening and overall result determination.
5. `test_05_create_inventory`: Validates sequential unit ID generation.
6. `test_06_add_whole_blood`: Verifies Whole Blood component support and 35-day shelf life.
7. `test_07_add_prbc`: Verifies Packed Red Blood Cells support and 42-day shelf life.
8. `test_08_add_ffp`: Verifies Fresh Frozen Plasma support and 365-day shelf life.
9. `test_09_add_platelets`: Verifies Platelet concentrate support and 5-day shelf life.
10. `test_10_issue_eligible_unit`: Confirms successful issuance of screened, unexpired units.
11. `test_11_prevent_duplicate_issue`: Strictly blocks issuing an already issued unit.
12. `test_12_prevent_reactive_unit_issue`: Strictly blocks issuing units with reactive serology.
13. `test_13_prevent_expired_unit_issue`: Strictly blocks issuing units past their expiry date.
14. `test_14_discard_unit`: Logs biohazard discard and updates inventory status.
15. `test_15_prevent_discarded_unit_issue`: Strictly blocks issuing a discarded unit.
16. `test_16_stock_calculation`: Verifies dynamic matrix aggregation.
17. `test_17_low_stock_alert`: Verifies threshold detection and alert generation.
18. `test_18_excel_export`: Verifies generated `.xlsx` binary integrity via `openpyxl`.
19. `test_19_pdf_export`: Verifies generated `.pdf` binary integrity via `reportlab`.
20. `test_20_logout`: Tests session destruction and protected route redirection.

---

## Business Logic & Safety Guarantees

- **No Stale or Phantom Stock**: Available stock counts are never manually keyed in. They are dynamically aggregated from records where `status = 'Available' AND serology_status = 'Non-Reactive' AND expiry_date >= Current Date`.
- **Automatic Expiry Transition**: Units whose expiry date has passed are automatically synchronized to `Expired` and locked from issuance.
- **Race Condition Prevention**: Unit availability is verified both before displaying the issue form and within the database commit transaction.

---

## Limitations & Future Scope

### Limitations
- Single-instance local SQLite database (optimized for desktop workstations and localized LAN intranets).
- Manual backup required by copying `bloodbank.db`.

### Future Scope
- Barcode scanner hardware integration via WebHID / USB keyboard emulation.
- Temperature logging sensor integration for automated cold chain monitoring.
- Role-based multi-user permissions (Phlebotomist, Laboratory Tech, Medical Director).

---

## License

Free, open-source software for community health clinics, hospitals, and educational blood bank management.
