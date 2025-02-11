import os
import json
import shutil
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import zipfile
import pandas as pd
import seat_plan_generator as spg  # This module contains the PDF-generation code

app = Flask(__name__)
app.secret_key = "my-fixed-secret-key-please-change"

# Default user credentials (can be overridden by the environment)
default_users = {
    "isakha": "iloveuu2024",
    "munna":  "munna54321",
    "mdzakariahabib":"zakaria123"
}
USERS = json.loads(os.environ.get("USERS_CREDENTIALS", json.dumps(default_users)))

def get_session_folder():
    username = session.get("username", "default")
    folder = os.path.join(os.getcwd(), "uploads", username)
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    return folder

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to access this page.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in USERS and USERS[username] == password:
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.")
            return render_template("login.html")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

def clear_output_folder():
    output = spg.OUTPUT_FOLDER  # defined in spg module
    persistent_file = os.path.join(output, "room_info_path.txt")
    if os.path.exists(output):
        for root, dirs, files in os.walk(output):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.abspath(file_path) == os.path.abspath(persistent_file):
                    continue
                try:
                    os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        print(f"Cleared files (except room_info_path.txt) in the output folder: {output}")
    else:
        os.makedirs(output, exist_ok=True)
    os.makedirs(spg.SEAT_PLAN_OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(spg.ATTENDANCE_OUTPUT_FOLDER, exist_ok=True)

@app.route("/upload_files", methods=["GET", "POST"])
@login_required
def upload_files():
    if request.method == "POST":
        base_dir = get_session_folder()
        for filename in os.listdir(base_dir):
            file_path = os.path.join(base_dir, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        pdf_files = request.files.getlist("pdf_input")
        for pdf in pdf_files:
            if pdf and pdf.filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(base_dir, pdf.filename)
                pdf.save(pdf_path)
                print("Saved PDF:", pdf_path)
        excel_file = request.files.get("room_info")
        excel_path = None
        if excel_file and excel_file.filename.lower().endswith((".xls", ".xlsx")):
            excel_path = os.path.join(base_dir, excel_file.filename)
            excel_file.save(excel_path)
            print("Saved room info Excel file as:", excel_path)
        else:
            print("No room info Excel file uploaded.")
        spg.PDF_INPUT_FOLDER = base_dir
        if excel_path:
            room_info_file = os.path.join(spg.OUTPUT_FOLDER, "room_info_path.txt")
            with open(room_info_file, "w") as f:
                f.write(excel_path)
            print("Updated persistent ROOM_INFO_PATH to:", excel_path)
        else:
            print("ROOM_INFO_PATH not updated, using default:", spg.ROOM_INFO_PATH)
        spg.merge_pdf_data_to_excel()
        flash("PDFs merged into Excel successfully! Now you can generate any PDF.")
        return redirect(url_for("upload_files"))
    return render_template("upload_files.html")

@app.route("/generate_seat_plan", methods=["GET", "POST"])
@login_required
def generate_seat_plan_pdf():
    if request.method == "POST":
        clear_output_folder()
        base_dir = get_session_folder()
        spg.PDF_INPUT_FOLDER = base_dir
        line1 = request.form.get("line1")
        line2 = request.form.get("line2")
        spg.set_custom_seatplan_headers(line1, line2)
        spg.generate_seat_plan_only()
        output_zip_path = os.path.join(base_dir, "seat_plan_output.zip")
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(spg.SEAT_PLAN_OUTPUT_FOLDER):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, spg.SEAT_PLAN_OUTPUT_FOLDER)
                    zipf.write(file_path, arcname)
        print("Created zip file:", output_zip_path)
        return send_file(output_zip_path, as_attachment=True)
    return render_template("seat_plan_form.html")

@app.route("/generate_attendance", methods=["GET", "POST"])
@login_required
def generate_attendance_pdf():
    if request.method == "POST":
        clear_output_folder()
        base_dir = get_session_folder()
        spg.PDF_INPUT_FOLDER = base_dir
        line1 = request.form.get("line1")
        line2 = request.form.get("line2")
        program = request.form.get("program")  # New attendance program field
        spg.set_custom_attendance_headers(line1, line2)
        spg.set_custom_attendance_program(program)
        spg.generate_attendance_only()
        output_zip_path = os.path.join(base_dir, "attendance_output.zip")
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            attendance_folder = os.path.join(spg.OUTPUT_FOLDER, "Attendance_Sheets")
            for root, dirs, files in os.walk(attendance_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, spg.OUTPUT_FOLDER)
                    zipf.write(file_path, arcname)
        print("Created attendance zip file:", output_zip_path)
        return send_file(output_zip_path, as_attachment=True)
    return render_template("attendance_form.html")

@app.route("/generate_summary", methods=["GET", "POST"])
@login_required
def generate_summary_pdf_route():
    if request.method == "POST":
        clear_output_folder()
        base_dir = get_session_folder()
        spg.PDF_INPUT_FOLDER = base_dir
        line1 = request.form.get("line1")
        line2 = request.form.get("line2")
        line3 = request.form.get("line3")
        spg.set_custom_summary_headers(line1, line2, line3)
        spg.generate_summary_only()
        output_zip_path = os.path.join(base_dir, "summary_output.zip")
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(spg.OUTPUT_FOLDER):
                for file in files:
                    if "Summary" in file:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, spg.OUTPUT_FOLDER)
                        zipf.write(file_path, arcname)
        print("Created summary zip file:", output_zip_path)
        return send_file(output_zip_path, as_attachment=True)
    return render_template("summary_form.html")

@app.route("/generate_envelopes", methods=["GET", "POST"])
@login_required
def generate_envelopes_pdf_route():
    if request.method == "POST":
        clear_output_folder()
        base_dir = get_session_folder()
        spg.PDF_INPUT_FOLDER = base_dir
        line1 = request.form.get("line1")
        line2 = request.form.get("line2")
        line3 = request.form.get("line3")
        line4 = request.form.get("line4")
        spg.set_custom_envelopes_headers(line1, line2, line3, line4)
        spg.generate_envelopes_only()
        output_zip_path = os.path.join(base_dir, "envelopes_output.zip")
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(spg.OUTPUT_FOLDER):
                for file in files:
                    if "Envelopes" in file:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, spg.OUTPUT_FOLDER)
                        zipf.write(file_path, arcname)
        print("Created envelopes zip file:", output_zip_path)
        return send_file(output_zip_path, as_attachment=True)
    return render_template("envelopes_form.html")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
