# app.py
import os
import json
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import zipfile
import seat_plan_generator as spg  # This module must contain your PDF-generation functions

app = Flask(__name__)

# Use a fixed secret key for session persistence. Change this value for production.
app.secret_key = "my-fixed-secret-key-please-change"

# Load user credentials from an environment variable, falling back to defaults.
default_users = {
    "user1": "password1",
    "user2": "password2"
}
USERS = json.loads(os.environ.get("USERS_CREDENTIALS", json.dumps(default_users)))

def get_session_folder():
    """
    Returns a folder path based on the logged-in username.
    Creates the folder if it does not exist.
    """
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

# -----------------------------
# Routes
# -----------------------------

# Default route always redirects to login.
@app.route("/")
def index():
    return redirect(url_for("login"))

# Login route.
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in USERS and USERS[username] == password:
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password. Please try again.")
            return render_template("login.html")
    return render_template("login.html")

# Logout route.
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))

# Dashboard route (protected).
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

# Upload files route (protected).
@app.route("/upload_files", methods=["GET", "POST"])
@login_required
def upload_files():
    # (Insert your file-upload logic here if needed.)
    return render_template("upload_files.html")

# -----------------------------
# PDF Generation Routes
# -----------------------------

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
