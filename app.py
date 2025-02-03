# app.py
import os
import uuid
import zipfile
from functools import wraps
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
import seat_plan_generator as spg  # Our PDF generator module


app = Flask(__name__)
app.secret_key = os.urandom(24)


# ------------------------------------------------------------------
# Simple User Database (In production, use a proper database and hashed passwords)
# ------------------------------------------------------------------
USERS = {
    "user1": "password1",
    "user2": "password2"
}

# ------------------------------------------------------------------
# Login Required Decorator
# ------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to access this page.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ------------------------------------------------------------------
# Helper functions to manage upload folder per session
# ------------------------------------------------------------------
def create_session_folder():
    session_id = str(uuid.uuid4())
    base_dir = os.path.join("uploads", session_id)
    os.makedirs(base_dir, exist_ok=True)
    session["session_folder"] = base_dir
    return base_dir

def get_session_folder():
    folder = session.get("session_folder")
    if folder and os.path.exists(folder):
        return folder
    else:
        return None

# ------------------------------------------------------------------
# Login Routes
# ------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in USERS and USERS[username] == password:
            session["username"] = username
            # Removed flash message here
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password. Please try again.")
            return render_template("login.html")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))

# ------------------------------------------------------------------
# Route: Upload Files (only once per session)
# ------------------------------------------------------------------
@app.route("/upload_files", methods=["GET", "POST"])
@login_required
def upload_files():
    if request.method == "POST":
        pdf_zip = request.files.get("pdf_zip")
        room_info = request.files.get("room_info")
        if not pdf_zip or not room_info:
            flash("Please upload both the PDF ZIP and the room_info.xlsx file.")
            return redirect(url_for("upload_files"))
        base_dir = create_session_folder()
        pdf_zip_path = os.path.join(base_dir, "pdfs.zip")
        room_info_path = os.path.join(base_dir, "room_info.xlsx")
        pdf_zip.save(pdf_zip_path)
        room_info.save(room_info_path)
        # Extract PDFs ZIP
        pdf_extract_folder = os.path.join(base_dir, "pdfs")
        os.makedirs(pdf_extract_folder, exist_ok=True)
        with zipfile.ZipFile(pdf_zip_path, "r") as zip_ref:
            zip_ref.extractall(pdf_extract_folder)
        # Update module globals
        spg.PDF_INPUT_FOLDER = pdf_extract_folder
        spg.MERGED_EXCEL_PATH = os.path.join(base_dir, "merged_excel.xlsx")
        spg.ROOM_INFO_PATH = room_info_path
        spg.OUTPUT_FOLDER = os.path.join(base_dir, "output")
        os.makedirs(spg.OUTPUT_FOLDER, exist_ok=True)
        flash("Files uploaded successfully!")
        return redirect(url_for("dashboard"))
    return render_template("upload_files.html")

# ------------------------------------------------------------------
# Dashboard Route
# ------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    if not get_session_folder():
        return redirect(url_for("upload_files"))
    return render_template("dashboard.html")

# ------------------------------------------------------------------
# PDF Generation Routes
# ------------------------------------------------------------------
@app.route("/generate_seat_plan", methods=["GET", "POST"])
@login_required
def generate_seat_plan_pdf():
    if request.method == "POST":
        base_dir = get_session_folder()
        custom_line1 = request.form.get("line1")
        custom_line2 = request.form.get("line2")
        spg.set_custom_seatplan_headers(custom_line1, custom_line2)
        spg.generate_seat_plan_only()
        output_zip_path = os.path.join(base_dir, "seat_plan_output.zip")
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(spg.OUTPUT_FOLDER):
                for file in files:
                    if "Seating_Plan" in file:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, spg.OUTPUT_FOLDER)
                        zipf.write(file_path, arcname)
        return send_file(output_zip_path, as_attachment=True)
    return render_template("seat_plan_form.html")

@app.route("/generate_attendance", methods=["GET", "POST"])
@login_required
def generate_attendance_pdf():
    if request.method == "POST":
        base_dir = get_session_folder()
        custom_line1 = request.form.get("line1")
        custom_line2 = request.form.get("line2")
        spg.set_custom_attendance_headers(custom_line1, custom_line2)
        spg.generate_attendance_only()
        output_zip_path = os.path.join(base_dir, "attendance_output.zip")
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(spg.OUTPUT_FOLDER):
                for file in files:
                    if "Attendance_" in file:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, spg.OUTPUT_FOLDER)
                        zipf.write(file_path, arcname)
        return send_file(output_zip_path, as_attachment=True)
    return render_template("attendance_form.html")

@app.route("/generate_summary", methods=["GET", "POST"])
@login_required
def generate_summary_pdf_route():
    if request.method == "POST":
        base_dir = get_session_folder()
        custom_line1 = request.form.get("line1")
        custom_line2 = request.form.get("line2")
        custom_line3 = request.form.get("line3")
        spg.set_custom_summary_headers(custom_line1, custom_line2, custom_line3)
        spg.generate_summary_only()
        output_zip_path = os.path.join(base_dir, "summary_output.zip")
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(spg.OUTPUT_FOLDER):
                for file in files:
                    if "Summary" in file:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, spg.OUTPUT_FOLDER)
                        zipf.write(file_path, arcname)
        return send_file(output_zip_path, as_attachment=True)
    return render_template("summary_form.html")

@app.route("/generate_envelopes", methods=["GET", "POST"])
@login_required
def generate_envelopes_pdf_route():
    if request.method == "POST":
        base_dir = get_session_folder()
        custom_line1 = request.form.get("line1")
        custom_line2 = request.form.get("line2")
        custom_line3 = request.form.get("line3")
        custom_line4 = request.form.get("line4")
        spg.set_custom_envelopes_headers(custom_line1, custom_line2, custom_line3, custom_line4)
        spg.generate_envelopes_only()
        output_zip_path = os.path.join(base_dir, "envelopes_output.zip")
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(spg.OUTPUT_FOLDER):
                for file in files:
                    if "Envelopes" in file:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, spg.OUTPUT_FOLDER)
                        zipf.write(file_path, arcname)
        return send_file(output_zip_path, as_attachment=True)
    return render_template("envelopes_form.html")

if __name__ == "__main__":
    app.run(debug=True)

