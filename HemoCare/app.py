import os
import functools
from datetime import datetime, date, timedelta
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, send_file
)
from werkzeug.security import check_password_hash, generate_password_hash
from database import (
    init_db,
    get_db_connection,
    get_stock_settings,
    VALID_COMPONENTS,
    VALID_BLOOD_GROUPS,
    VALID_TEST_RESULTS,
    VALID_INVENTORY_STATUSES
)
import models
import report_generator

app = Flask(__name__)
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is not configured")
app.secret_key = secret_key

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ==========================================
# AUTHENTICATION & SESSION MANAGEMENT
# ==========================================

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please sign in to access HemoCare.", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view

@app.context_processor
def inject_global_data():
    """Provides common data to all templates (user, alerts count, etc.)."""
    if "user_id" in session:
        metrics = models.get_dashboard_metrics()
        return {
            "current_user": session.get("username"),
            "current_full_name": session.get("full_name"),
            "low_stock_count": metrics.get("low_stock_count", 0),
            "expiring_soon_count": metrics.get("expiring_soon_count", 0),
            "valid_components": VALID_COMPONENTS,
            "valid_blood_groups": VALID_BLOOD_GROUPS,
            "today_date": date.today().isoformat()
        }
    return {
        "valid_components": VALID_COMPONENTS,
        "valid_blood_groups": VALID_BLOOD_GROUPS,
        "today_date": date.today().isoformat()
    }

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password. Please try again.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("login"))

# ==========================================
# MAIN DASHBOARD
# ==========================================

@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    metrics = models.get_dashboard_metrics()
    chart_data = models.get_chart_data()
    return render_template("dashboard.html", metrics=metrics, chart_data=chart_data)

@app.route("/api/chart-data")
@login_required
def api_chart_data():
    return jsonify(models.get_chart_data())

# ==========================================
# DONOR MASTER
# ==========================================

@app.route("/donors")
@login_required
def donors():
    search = request.args.get("search", "")
    blood_group = request.args.get("blood_group", "")
    status = request.args.get("status", "")
    donor_list = models.get_donors(search=search, blood_group=blood_group, status=status)
    return render_template("donors.html", donors=donor_list, search=search, blood_group=blood_group, status=status)

@app.route("/donors/add", methods=["GET", "POST"])
@login_required
def donor_add():
    if request.method == "POST":
        try:
            donor_id, donor_code = models.create_donor(request.form)
            flash(f"Donor {donor_code} ({request.form.get('name')}) registered successfully!", "success")
            return redirect(url_for("donors"))
        except Exception as e:
            flash(f"Unable to save record: {str(e)}", "danger")
            return render_template("donor_form.html", donor=request.form, action="Add")
    return render_template("donor_form.html", donor={}, action="Add")

@app.route("/donors/edit/<int:donor_id>", methods=["GET", "POST"])
@login_required
def donor_edit(donor_id):
    donor = models.get_donor_by_id(donor_id)
    if not donor:
        flash("Donor record not found.", "danger")
        return redirect(url_for("donors"))

    if request.method == "POST":
        try:
            models.update_donor(donor_id, request.form)
            flash(f"Donor {donor['donor_code']} details updated successfully!", "success")
            return redirect(url_for("donors"))
        except Exception as e:
            flash(f"Unable to save record: {str(e)}", "danger")
            return render_template("donor_form.html", donor=request.form, action="Edit", donor_id=donor_id)

    return render_template("donor_form.html", donor=donor, action="Edit", donor_id=donor_id)

@app.route("/donors/delete/<int:donor_id>", methods=["POST"])
@login_required
def donor_delete(donor_id):
    try:
        models.delete_donor(donor_id)
        flash("Donor record removed successfully.", "success")
    except Exception as e:
        flash(f"Unable to delete donor: {str(e)}", "danger")
    return redirect(url_for("donors"))

@app.route("/donors/view/<int:donor_id>")
@login_required
def donor_view(donor_id):
    donor = models.get_donor_by_id(donor_id)
    if not donor:
        flash("Donor not found.", "danger")
        return redirect(url_for("donors"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM donations WHERE donor_id = ? ORDER BY id DESC", (donor_id,))
    history = cursor.fetchall()
    conn.close()
    return render_template("donor_view.html", donor=donor, history=history)

@app.route("/api/donors/<int:donor_id>")
@login_required
def api_donor_info(donor_id):
    donor = models.get_donor_by_id(donor_id)
    if not donor:
        return jsonify({"error": "Donor not found"}), 404
    return jsonify({
        "id": donor["id"],
        "donor_code": donor["donor_code"],
        "name": donor["name"],
        "age": donor["age"],
        "gender": donor["gender"],
        "blood_group": donor["blood_group"],
        "status": donor["status"]
    })

# ==========================================
# DONATION REGISTER
# ==========================================

@app.route("/donations")
@login_required
def donations():
    search = request.args.get("search", "")
    blood_group = request.args.get("blood_group", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    donation_list = models.get_donations(search=search, blood_group=blood_group, date_from=date_from, date_to=date_to)
    return render_template("donations.html", donations=donation_list, search=search, blood_group=blood_group, date_from=date_from, date_to=date_to)

@app.route("/donations/add", methods=["GET", "POST"])
@login_required
def donation_add():
    if request.method == "POST":
        try:
            donation_id, donation_code = models.create_donation(request.form)
            # If user checked 'add_to_inventory_immediately'
            comp_type = request.form.get("component_to_create")
            if comp_type and comp_type in VALID_COMPONENTS:
                donation = models.get_donation_by_id(donation_id)
                unit_data = {
                    "component_type": comp_type,
                    "blood_group": donation["blood_group"],
                    "donation_id": donation["id"],
                    "donation_code": donation["donation_code"],
                    "donor_id": donation["donor_id"],
                    "donor_code": donation["donor_code"],
                    "collection_date": donation["donation_date"],
                    "volume_ml": donation["volume_ml"],
                    "storage_location": request.form.get("storage_location", "Blood Bank Main Storage"),
                    "status": "Available",
                    "serology_status": "Pending"
                }
                _, unit_code = models.add_inventory_unit(unit_data)
                flash(f"Donation {donation_code} recorded and initial unit {unit_code} ({comp_type}) registered in inventory (Pending Serology).", "success")
            else:
                flash(f"Donation {donation_code} recorded successfully! Proceed to Serology screening.", "success")
            return redirect(url_for("donations"))
        except Exception as e:
            flash(f"Unable to record donation: {str(e)}", "danger")

    # Fetch active donors for selection dropdown
    donors_available = models.get_donors(status="Active")
    return render_template("donation_form.html", donors=donors_available, today=date.today().isoformat())

# ==========================================
# SEROLOGY REGISTER
# ==========================================

@app.route("/serology")
@login_required
def serology():
    search = request.args.get("search", "")
    result = request.args.get("result", "")
    records = models.get_serology_records(search=search, result=result)
    return render_template("serology.html", records=records, search=search, result=result)

@app.route("/serology/record", methods=["GET", "POST"])
@app.route("/serology/record/<int:donation_id>", methods=["GET", "POST"])
@login_required
def serology_record(donation_id=None):
    if request.method == "POST":
        try:
            serology_id, serology_code, overall = models.record_serology(request.form)
            if overall == "Reactive":
                flash(f"Serology {serology_code} marked as REACTIVE. Associated units have been quarantined/restricted from issue.", "warning")
            else:
                flash(f"Serology {serology_code} recorded successfully. Result: {overall}.", "success")
            return redirect(url_for("serology"))
        except Exception as e:
            flash(f"Unable to save serology record: {str(e)}", "danger")

    selected_donation = None
    if donation_id:
        selected_donation = models.get_donation_by_id(donation_id)
        existing_serology = models.get_serology_by_donation_id(donation_id)
    else:
        existing_serology = None

    # Fetch donations that need serology or recently collected
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, s.overall_result
        FROM donations d
        LEFT JOIN serology s ON d.id = s.donation_id
        ORDER BY d.id DESC
    """)
    all_donations = cursor.fetchall()
    conn.close()

    return render_template(
        "serology_form.html",
        donation=selected_donation,
        serology=existing_serology,
        all_donations=all_donations,
        today=date.today().isoformat()
    )

# ==========================================
# COMPONENT INVENTORY
# ==========================================

@app.route("/inventory")
@login_required
def inventory():
    search = request.args.get("search", "")
    component = request.args.get("component", "")
    blood_group = request.args.get("blood_group", "")
    status = request.args.get("status", "")
    expiring_days = request.args.get("expiring_days")
    units = models.get_inventory(
        search=search,
        component=component,
        blood_group=blood_group,
        status=status,
        expiring_days=expiring_days
    )
    return render_template(
        "inventory.html",
        units=units,
        search=search,
        component=component,
        blood_group=blood_group,
        status=status,
        expiring_days=expiring_days
    )

@app.route("/inventory/add", methods=["GET", "POST"])
@login_required
def inventory_add():
    if request.method == "POST":
        try:
            unit_id, unit_code = models.add_inventory_unit(request.form)
            flash(f"Component Unit {unit_code} ({request.form.get('component_type')}) added to inventory!", "success")
            return redirect(url_for("inventory"))
        except Exception as e:
            flash(f"Unable to add inventory unit: {str(e)}", "danger")

    donations_list = models.get_donations()
    return render_template("inventory_form.html", donations=donations_list, today=date.today().isoformat())

@app.route("/inventory/view/<int:unit_id>")
@login_required
def inventory_view(unit_id):
    unit = models.get_unit_by_id(unit_id)
    if not unit:
        flash("Unit record not found.", "danger")
        return redirect(url_for("inventory"))
    is_eligible, eligibility_msg = models.check_unit_issueability(unit)
    return render_template("inventory_view.html", unit=unit, is_eligible=is_eligible, eligibility_msg=eligibility_msg)

@app.route("/api/inventory/unit/<unit_identifier>")
@login_required
def api_unit_info(unit_identifier):
    unit = models.get_unit_by_id(unit_identifier)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404
    is_eligible, msg = models.check_unit_issueability(unit)
    return jsonify({
        "id": unit["id"],
        "unit_code": unit["unit_code"],
        "blood_group": unit["blood_group"],
        "component_type": unit["component_type"],
        "expiry_date": unit["expiry_date"],
        "status": unit["status"],
        "serology_status": unit["serology_status"],
        "is_eligible": is_eligible,
        "eligibility_message": msg
    })

# ==========================================
# ISSUE REGISTER
# ==========================================

@app.route("/issues")
@login_required
def issues():
    search = request.args.get("search", "")
    blood_group = request.args.get("blood_group", "")
    component = request.args.get("component", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    issue_list = models.get_issues(
        search=search,
        blood_group=blood_group,
        component=component,
        date_from=date_from,
        date_to=date_to
    )
    return render_template(
        "issue.html",
        issues=issue_list,
        search=search,
        blood_group=blood_group,
        component=component,
        date_from=date_from,
        date_to=date_to
    )

@app.route("/issues/new", methods=["GET", "POST"])
@login_required
def issue_new():
    if request.method == "POST":
        try:
            issue_id, issue_code = models.issue_unit(request.form)
            flash(f"Unit successfully issued with Issue Slip ID: {issue_code}!", "success")
            return redirect(url_for("issues"))
        except Exception as e:
            flash(f"Unable to issue unit: {str(e)}", "danger")

    # Fetch available and serologically non-reactive units that have not expired
    available_units = models.get_inventory(status="Available")
    eligible_units = [u for u in available_units if u["serology_status"] == "Non-Reactive" and u["expiry_date"] >= date.today().isoformat()]
    hospitals_list = models.get_hospitals(status="Active")

    return render_template(
        "issue_form.html",
        units=eligible_units,
        hospitals=hospitals_list,
        today=date.today().isoformat()
    )

# ==========================================
# DISCARD / WASTAGE REGISTER
# ==========================================

@app.route("/discards")
@login_required
def discards():
    search = request.args.get("search", "")
    component = request.args.get("component", "")
    blood_group = request.args.get("blood_group", "")
    reason = request.args.get("reason", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    discard_list = models.get_discards(
        search=search,
        component=component,
        blood_group=blood_group,
        reason=reason,
        date_from=date_from,
        date_to=date_to
    )
    return render_template(
        "discard.html",
        discards=discard_list,
        search=search,
        component=component,
        blood_group=blood_group,
        reason=reason,
        date_from=date_from,
        date_to=date_to
    )

@app.route("/discards/new", methods=["GET", "POST"])
@login_required
def discard_new():
    if request.method == "POST":
        try:
            discard_id, discard_code = models.discard_unit(request.form)
            flash(f"Unit logged as discarded with Discard ID: {discard_code}.", "warning")
            return redirect(url_for("discards"))
        except Exception as e:
            flash(f"Unable to discard unit: {str(e)}", "danger")

    # Fetch all units that are NOT yet issued and NOT already discarded
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM inventory
        WHERE status NOT IN ('Issued', 'Discarded')
        ORDER BY expiry_date ASC, id DESC
    """)
    candidate_units = cursor.fetchall()
    conn.close()

    return render_template("discard_form.html", units=candidate_units, today=date.today().isoformat())

# ==========================================
# HOSPITAL MASTER
# ==========================================

@app.route("/hospitals")
@login_required
def hospitals():
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    hospital_list = models.get_hospitals(search=search, status=status)
    return render_template("hospitals.html", hospitals=hospital_list, search=search, status=status)

@app.route("/hospitals/add", methods=["GET", "POST"])
@login_required
def hospital_add():
    if request.method == "POST":
        try:
            hosp_id, hosp_code = models.create_hospital(request.form)
            flash(f"Hospital {hosp_code} ({request.form.get('name')}) registered successfully!", "success")
            return redirect(url_for("hospitals"))
        except Exception as e:
            flash(f"Unable to save hospital record: {str(e)}", "danger")
            return render_template("hospital_form.html", hospital=request.form, action="Add")
    return render_template("hospital_form.html", hospital={}, action="Add")

@app.route("/hospitals/edit/<int:hosp_id>", methods=["GET", "POST"])
@login_required
def hospital_edit(hosp_id):
    hosp = models.get_hospital_by_id(hosp_id)
    if not hosp:
        flash("Hospital record not found.", "danger")
        return redirect(url_for("hospitals"))

    if request.method == "POST":
        try:
            models.update_hospital(hosp_id, request.form)
            flash(f"Hospital {hosp['hospital_code']} updated successfully!", "success")
            return redirect(url_for("hospitals"))
        except Exception as e:
            flash(f"Unable to save record: {str(e)}", "danger")
            return render_template("hospital_form.html", hospital=request.form, action="Edit", hosp_id=hosp_id)

    return render_template("hospital_form.html", hospital=hosp, action="Edit", hosp_id=hosp_id)

@app.route("/hospitals/delete/<int:hosp_id>", methods=["POST"])
@login_required
def hospital_delete(hosp_id):
    try:
        models.delete_hospital(hosp_id)
        flash("Hospital record removed successfully.", "success")
    except Exception as e:
        flash(f"Unable to remove hospital: {str(e)}", "danger")
    return redirect(url_for("hospitals"))

@app.route("/hospitals/view/<int:hosp_id>")
@login_required
def hospital_view(hosp_id):
    hosp = models.get_hospital_by_id(hosp_id)
    if not hosp:
        flash("Hospital not found.", "danger")
        return redirect(url_for("hospitals"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues WHERE hospital_id = ? ORDER BY id DESC", (hosp_id,))
    issue_history = cursor.fetchall()
    conn.close()
    return render_template("hospital_view.html", hospital=hosp, issues=issue_history)

# ==========================================
# DETAILED STOCK PAGE & SETTINGS
# ==========================================

@app.route("/stock")
@login_required
def stock():
    comp_filter = request.args.get("component", "")
    bg_filter = request.args.get("blood_group", "")
    matrix = models.get_stock_matrix(component_filter=comp_filter, blood_group_filter=bg_filter)
    settings = get_stock_settings()
    metrics = models.get_dashboard_metrics()
    return render_template(
        "stock.html",
        matrix=matrix,
        settings=settings,
        metrics=metrics,
        selected_component=comp_filter,
        selected_bg=bg_filter
    )

@app.route("/stock/settings", methods=["GET", "POST"])
@login_required
def stock_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == "POST":
        try:
            for comp in VALID_COMPONENTS:
                min_lvl = int(request.form.get(f"min_stock_{comp}", 10))
                exp_days = int(request.form.get(f"exp_days_{comp}", 7))
                cursor.execute("""
                    INSERT INTO stock_settings (component_type, min_stock_level, expiring_days_threshold)
                    VALUES (?, ?, ?)
                    ON CONFLICT(component_type) DO UPDATE SET
                        min_stock_level = excluded.min_stock_level,
                        expiring_days_threshold = excluded.expiring_days_threshold
                """, (comp, min_lvl, exp_days))
            conn.commit()
            flash("Stock alert thresholds and expiry rules updated successfully.", "success")
            return redirect(url_for("stock"))
        except Exception as e:
            flash(f"Failed to update settings: {str(e)}", "danger")

    cursor.execute("SELECT * FROM stock_settings")
    settings_rows = {r["component_type"]: r for r in cursor.fetchall()}
    conn.close()
    return render_template("stock_settings.html", settings=settings_rows)

# ==========================================
# REPORTS & EXPORTS
# ==========================================

@app.route("/reports")
@login_required
def reports():
    report_type = request.args.get("type", "stock")
    filters = {
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", ""),
        "blood_group": request.args.get("blood_group", ""),
        "component": request.args.get("component", ""),
        "hospital_id": request.args.get("hospital_id", ""),
        "status": request.args.get("status", "")
    }
    title, headers, rows = report_generator.fetch_report_data(report_type, filters)
    hospitals_list = models.get_hospitals()
    return render_template(
        "reports.html",
        report_types=report_generator.REPORT_TYPES,
        active_type=report_type,
        title=title,
        headers=headers,
        rows=rows,
        filters=filters,
        hospitals=hospitals_list
    )

@app.route("/reports/export/excel")
@login_required
def export_excel():
    report_type = request.args.get("type", "stock")
    filters = {
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", ""),
        "blood_group": request.args.get("blood_group", ""),
        "component": request.args.get("component", ""),
        "hospital_id": request.args.get("hospital_id", ""),
        "status": request.args.get("status", "")
    }
    xlsx_bytes = report_generator.generate_excel_report(report_type, filters)
    filename = f"hemocare_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        xlsx_bytes,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/reports/export/pdf")
@login_required
def export_pdf():
    report_type = request.args.get("type", "stock")
    filters = {
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", ""),
        "blood_group": request.args.get("blood_group", ""),
        "component": request.args.get("component", ""),
        "hospital_id": request.args.get("hospital_id", ""),
        "status": request.args.get("status", "")
    }
    pdf_bytes = report_generator.generate_pdf_report(report_type, filters)
    filename = f"hemocare_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        pdf_bytes,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

# ==========================================
# USER INSTRUCTIONS & MANUAL
# ==========================================

@app.route("/instructions")
@login_required
def instructions():
    return render_template("instructions.html")

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500

# ==========================================
# STARTUP ENTRYPOINT
# ==========================================

if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("HEMOCARE: Offline Blood Bank Management System")
    print("Safe Blood — Healthier Tomorrow")
    print("Running completely offline at: http://127.0.0.1:5000")
    print("Default Login: admin / admin123")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False)
