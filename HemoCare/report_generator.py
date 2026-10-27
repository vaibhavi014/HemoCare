import os
import io
from datetime import datetime, date, timedelta
from database import (
    get_db_connection,
    sync_expired_units,
    VALID_COMPONENTS,
    VALID_BLOOD_GROUPS
)
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

REPORT_TYPES = {
    "donors": "Donor Report",
    "donations": "Donation Report",
    "serology": "Serology Screening Report",
    "inventory": "Component Inventory Report",
    "stock": "Component Stock Matrix Report",
    "issues": "Blood & Component Issue Report",
    "discards": "Discard & Wastage Report",
    "hospital_issues": "Hospital-wise Issue Report",
    "monthly": "Monthly Blood Bank Report",
    "low_stock": "Low Stock Alert Report",
    "expiry": "Expiry & Aging Report"
}

def fetch_report_data(report_type, filters=None):
    """Fetches headers and tabular rows based on report type and applied filters."""
    filters = filters or {}
    sync_expired_units()
    conn = get_db_connection()
    cursor = conn.cursor()
    today_str = date.today().isoformat()

    title = REPORT_TYPES.get(report_type, "Blood Bank Report")
    headers = []
    rows = []

    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    blood_group = filters.get("blood_group")
    component = filters.get("component")
    hospital_id = filters.get("hospital_id")
    status = filters.get("status")

    if report_type == "donors":
        headers = ["Donor ID", "Full Name", "Age", "Gender", "Blood Group", "Phone", "Email", "Last Donation", "Type", "Status"]
        q = "SELECT donor_code, name, age, gender, blood_group, phone, COALESCE(email, '-'), COALESCE(last_donation_date, 'Never'), donor_type, status FROM donors WHERE 1=1"
        p = []
        if blood_group and blood_group in VALID_BLOOD_GROUPS:
            q += " AND blood_group = ?"; p.append(blood_group)
        if status:
            q += " AND status = ?"; p.append(status)
        q += " ORDER BY id DESC"
        cursor.execute(q, p)
        rows = [list(r) for r in cursor.fetchall()]

    elif report_type == "donations":
        headers = ["Donation ID", "Donor ID", "Donor Name", "Blood Group", "Date", "Type", "Vol (mL)", "Bag Number", "Status"]
        q = "SELECT donation_code, donor_code, donor_name, blood_group, donation_date, donation_type, volume_ml, bag_number, status FROM donations WHERE 1=1"
        p = []
        if blood_group and blood_group in VALID_BLOOD_GROUPS:
            q += " AND blood_group = ?"; p.append(blood_group)
        if date_from:
            q += " AND donation_date >= ?"; p.append(date_from)
        if date_to:
            q += " AND donation_date <= ?"; p.append(date_to)
        q += " ORDER BY id DESC"
        cursor.execute(q, p)
        rows = [list(r) for r in cursor.fetchall()]

    elif report_type == "serology":
        headers = ["Serology ID", "Donation ID", "Donor Name", "Blood Group", "HIV", "HBsAg", "HCV", "Syphilis", "Malaria", "Overall Result", "Test Date"]
        q = "SELECT serology_code, donation_code, donor_name, blood_group, hiv, hbsag, hcv, syphilis, malaria, overall_result, test_date FROM serology WHERE 1=1"
        p = []
        if blood_group and blood_group in VALID_BLOOD_GROUPS:
            q += " AND blood_group = ?"; p.append(blood_group)
        if status: # here status can be overall_result
            q += " AND overall_result = ?"; p.append(status)
        if date_from:
            q += " AND test_date >= ?"; p.append(date_from)
        if date_to:
            q += " AND test_date <= ?"; p.append(date_to)
        q += " ORDER BY id DESC"
        cursor.execute(q, p)
        rows = [list(r) for r in cursor.fetchall()]

    elif report_type == "inventory":
        headers = ["Unit ID", "Component", "Blood Group", "Collection Date", "Expiry Date", "Vol (mL)", "Location", "Serology", "Status"]
        q = "SELECT unit_code, component_type, blood_group, collection_date, expiry_date, volume_ml, storage_location, serology_status, status FROM inventory WHERE 1=1"
        p = []
        if component and component in VALID_COMPONENTS:
            q += " AND component_type = ?"; p.append(component)
        if blood_group and blood_group in VALID_BLOOD_GROUPS:
            q += " AND blood_group = ?"; p.append(blood_group)
        if status:
            q += " AND status = ?"; p.append(status)
        q += " ORDER BY expiry_date ASC, id DESC"
        cursor.execute(q, p)
        rows = [list(r) for r in cursor.fetchall()]

    elif report_type == "stock":
        headers = ["Component", "Blood Group", "Available", "Issued", "Discarded", "Expired", "Total Units"]
        q = """
            SELECT component_type, blood_group,
                   SUM(CASE WHEN status = 'Available' AND serology_status = 'Non-Reactive' AND expiry_date >= ? THEN 1 ELSE 0 END) AS avail,
                   SUM(CASE WHEN status = 'Issued' THEN 1 ELSE 0 END) AS iss,
                   SUM(CASE WHEN status = 'Discarded' THEN 1 ELSE 0 END) AS disc,
                   SUM(CASE WHEN status = 'Expired' OR (status = 'Available' AND expiry_date < ?) THEN 1 ELSE 0 END) AS exp,
                   COUNT(*) AS tot
            FROM inventory WHERE 1=1
        """
        p = [today_str, today_str]
        if component and component in VALID_COMPONENTS:
            q += " AND component_type = ?"; p.append(component)
        if blood_group and blood_group in VALID_BLOOD_GROUPS:
            q += " AND blood_group = ?"; p.append(blood_group)
        q += " GROUP BY component_type, blood_group ORDER BY component_type, blood_group"
        cursor.execute(q, p)
        rows = [list(r) for r in cursor.fetchall()]

    elif report_type == "issues":
        headers = ["Issue ID", "Date", "Hospital", "Unit ID", "Blood Group", "Component", "Patient Name", "Department/Doctor", "Issued By"]
        q = "SELECT issue_code, issue_date, hospital_name, unit_code, blood_group, component_type, patient_name, COALESCE(doctor_dept, '-'), issued_by FROM issues WHERE 1=1"
        p = []
        if blood_group and blood_group in VALID_BLOOD_GROUPS:
            q += " AND blood_group = ?"; p.append(blood_group)
        if component and component in VALID_COMPONENTS:
            q += " AND component_type = ?"; p.append(component)
        if hospital_id:
            q += " AND hospital_id = ?"; p.append(hospital_id)
        if date_from:
            q += " AND issue_date >= ?"; p.append(date_from)
        if date_to:
            q += " AND issue_date <= ?"; p.append(date_to)
        q += " ORDER BY id DESC"
        cursor.execute(q, p)
        rows = [list(r) for r in cursor.fetchall()]

    elif report_type == "discards":
        headers = ["Discard ID", "Unit ID", "Blood Group", "Component", "Discard Date", "Reason", "Quantity", "Authorized By"]
        q = "SELECT discard_code, unit_code, blood_group, component_type, discard_date, reason, quantity, authorized_by FROM discard_records WHERE 1=1"
        p = []
        if blood_group and blood_group in VALID_BLOOD_GROUPS:
            q += " AND blood_group = ?"; p.append(blood_group)
        if component and component in VALID_COMPONENTS:
            q += " AND component_type = ?"; p.append(component)
        if date_from:
            q += " AND discard_date >= ?"; p.append(date_from)
        if date_to:
            q += " AND discard_date <= ?"; p.append(date_to)
        q += " ORDER BY id DESC"
        cursor.execute(q, p)
        rows = [list(r) for r in cursor.fetchall()]

    elif report_type == "hospital_issues":
        headers = ["Hospital Code", "Hospital Name", "Blood Group", "Component", "Units Issued", "Latest Issue Date"]
        q = """
            SELECT hospital_code, hospital_name, blood_group, component_type, COUNT(*) as units, MAX(issue_date) as latest_dt
            FROM issues WHERE 1=1
        """
        p = []
        if hospital_id:
            q += " AND hospital_id = ?"; p.append(hospital_id)
        if component and component in VALID_COMPONENTS:
            q += " AND component_type = ?"; p.append(component)
        if blood_group and blood_group in VALID_BLOOD_GROUPS:
            q += " AND blood_group = ?"; p.append(blood_group)
        q += " GROUP BY hospital_code, hospital_name, blood_group, component_type ORDER BY hospital_name, latest_dt DESC"
        cursor.execute(q, p)
        rows = [list(r) for r in cursor.fetchall()]

    elif report_type == "monthly":
        headers = ["Month", "Total Donations", "Whole Blood Added", "PRBC Added", "FFP Added", "Platelets Added", "Units Issued", "Units Discarded"]
        # Generate last 12 months
        curr = date.today()
        rows = []
        for i in range(11, -1, -1):
            m_dt = (curr.replace(day=1) - timedelta(days=i*30))
            m_str = m_dt.strftime("%Y-%m")
            m_label = m_dt.strftime("%B %Y")

            cursor.execute("SELECT COUNT(*) as c FROM donations WHERE donation_date LIKE ?", (f"{m_str}%",))
            don_c = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM inventory WHERE component_type = 'Whole Blood' AND collection_date LIKE ?", (f"{m_str}%",))
            wb_c = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM inventory WHERE component_type = 'PRBC' AND collection_date LIKE ?", (f"{m_str}%",))
            prbc_c = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM inventory WHERE component_type = 'FFP' AND collection_date LIKE ?", (f"{m_str}%",))
            ffp_c = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM inventory WHERE component_type = 'Platelets' AND collection_date LIKE ?", (f"{m_str}%",))
            plt_c = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM issues WHERE issue_date LIKE ?", (f"{m_str}%",))
            iss_c = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM discard_records WHERE discard_date LIKE ?", (f"{m_str}%",))
            disc_c = cursor.fetchone()["c"]

            rows.append([m_label, don_c, wb_c, prbc_c, ffp_c, plt_c, iss_c, disc_c])

    elif report_type == "low_stock":
        headers = ["Component", "Available Stock", "Minimum Threshold", "Status", "Shortfall"]
        cursor.execute("SELECT component_type, min_stock_level FROM stock_settings")
        settings = {r["component_type"]: r["min_stock_level"] for r in cursor.fetchall()}
        rows = []
        for comp in VALID_COMPONENTS:
            cursor.execute("""
                SELECT COUNT(*) as c FROM inventory
                WHERE component_type = ? AND status = 'Available' AND serology_status = 'Non-Reactive' AND expiry_date >= ?
            """, (comp, today_str))
            avail = cursor.fetchone()["c"]
            min_lvl = settings.get(comp, 10)
            status_lbl = "LOW STOCK" if avail < min_lvl else "ADEQUATE"
            shortfall = max(0, min_lvl - avail)
            rows.append([comp, avail, min_lvl, status_lbl, shortfall])

    elif report_type == "expiry":
        headers = ["Unit ID", "Component", "Blood Group", "Collection Date", "Expiry Date", "Aging Status", "Days Remaining", "Storage Location"]
        q = "SELECT unit_code, component_type, blood_group, collection_date, expiry_date, status, storage_location FROM inventory WHERE status IN ('Available', 'Expired') ORDER BY expiry_date ASC"
        cursor.execute(q)
        raw = cursor.fetchall()
        rows = []
        for r in raw:
            try:
                exp_dt = datetime.strptime(r["expiry_date"], "%Y-%m-%d").date()
                diff_days = (exp_dt - date.today()).days
            except Exception:
                diff_days = 0

            if diff_days < 0:
                aging_status = "EXPIRED"
            elif diff_days <= 7:
                aging_status = "EXPIRING SOON"
            else:
                aging_status = "SAFE"

            rows.append([
                r["unit_code"],
                r["component_type"],
                r["blood_group"],
                r["collection_date"],
                r["expiry_date"],
                aging_status,
                diff_days,
                r["storage_location"]
            ])

    conn.close()
    return title, headers, rows

# ==========================================
# EXCEL GENERATOR (openpyxl)
# ==========================================

def generate_excel_report(report_type, filters=None):
    title, headers, rows = fetch_report_data(report_type, filters)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:30]

    # Theme colors
    title_fill = PatternFill(start_color="8B0000", end_color="8B0000", fill_type="solid") # Deep Red
    header_fill = PatternFill(start_color="C0392B", end_color="C0392B", fill_type="solid") # Crimson Red
    zebra_fill = PatternFill(start_color="F9F9F9", end_color="F9F9F9", fill_type="solid")
    
    font_title = Font(name="Segoe UI", size=16, bold=True, color="FFFFFF")
    font_sub = Font(name="Segoe UI", size=10, italic=True, color="FFFFFF")
    font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    font_body = Font(name="Segoe UI", size=10)
    
    thin_border = Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD')
    )

    num_cols = max(len(headers), 1)

    # Title Banner (Row 1-2)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    cell_title = ws.cell(row=1, column=1, value=f"HEMOCARE - {title.upper()}")
    cell_title.font = font_title
    cell_title.fill = title_fill
    cell_title.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 35

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cell_sub = ws.cell(row=2, column=1, value=f"Offline Blood Bank Management System | Safe Blood — Healthier Tomorrow | Generated: {now_str}")
    cell_sub.font = font_sub
    cell_sub.fill = title_fill
    cell_sub.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20

    # Spacing row
    ws.row_dimensions[3].height = 10

    # Table Header (Row 4)
    ws.row_dimensions[4].height = 25
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=4, column=col_idx, value=h)
        c.font = font_header
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border

    # Table Body
    for row_idx, r_data in enumerate(rows, start=5):
        ws.row_dimensions[row_idx].height = 20
        is_even = (row_idx % 2 == 0)
        for col_idx, val in enumerate(r_data, start=1):
            c = ws.cell(row=row_idx, column=col_idx, value=val)
            c.font = font_body
            c.border = thin_border
            if is_even:
                c.fill = zebra_fill
            # Align numbers center/right, text left
            if isinstance(val, (int, float)):
                c.alignment = Alignment(horizontal="right", vertical="center")
            elif str(val) in ["Active", "Available", "SAFE", "ADEQUATE", "Non-Reactive"]:
                c.alignment = Alignment(horizontal="center", vertical="center")
            elif str(val) in ["Reactive", "Expired", "Discarded", "LOW STOCK", "EXPIRED"]:
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")

    # Freeze panes below header
    ws.freeze_panes = "A5"

    # Auto-fit column widths
    for col in ws.columns:
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            # skip merged row 1 and 2 for width calculation
            if cell.row in [1, 2, 3]:
                continue
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Save to in-memory bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# ==========================================
# PDF GENERATOR (reportlab)
# ==========================================

def generate_pdf_report(report_type, filters=None):
    title, headers, rows = fetch_report_data(report_type, filters)

    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#8B0000'),
        alignment=1, # Center
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#555555'),
        alignment=1,
        spaceAfter=12
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#222222'),
        spaceAfter=10
    )

    cell_style = ParagraphStyle(
        'DocCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#111111')
    )

    header_cell_style = ParagraphStyle(
        'DocHeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=1
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("HEMOCARE", title_style))
    story.append(Paragraph("Offline Blood Bank Management System | Safe Blood — Healthier Tomorrow", subtitle_style))
    
    # Report info
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"<b>Report:</b> {title} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Generated:</b> {now_str}", meta_style))
    story.append(Spacer(1, 8))

    # Format table data with Paragraphs to support text wrapping
    pdf_table_data = []
    
    # Headers
    header_row = [Paragraph(f"<b>{h}</b>", header_cell_style) for h in headers]
    pdf_table_data.append(header_row)

    # Rows (limit to first 100 rows for clean PDF formatting if huge)
    for r in rows[:150]:
        row_items = []
        for c in r:
            val_str = str(c) if c is not None else ""
            row_items.append(Paragraph(val_str, cell_style))
        pdf_table_data.append(row_items)

    if not rows:
        empty_msg = [Paragraph("<i>No records found matching the specified criteria.</i>", cell_style)] + ["" for _ in range(len(headers)-1)]
        pdf_table_data.append(empty_msg)

    # Build Table
    t = Table(pdf_table_data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C0392B')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
    ]))

    story.append(t)
    doc.build(story)
    output.seek(0)
    return output
