import os
import uuid
import zipfile
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from werkzeug.utils import secure_filename

# Import your generator's main function and globals
import seat_plan_generator as spg

app = Flask(__name__)
app.secret_key = '7aDRP9XYX'  # CHANGE THIS to a strong secret in production

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'zip', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# -------- Dummy User Credentials -----------
users = {
    'user1': 'password1',
    'user2': 'password2',
}
# --------------------------------------------

def allowed_file(filename, ext):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == ext

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('upload'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        if uname in users and users[uname] == pwd:
            session['username'] = uname
            return redirect(url_for('upload'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'pdf_zip' not in request.files or 'room_info' not in request.files:
            flash('Missing one or more files.')
            return redirect(request.url)
        
        pdf_zip = request.files['pdf_zip']
        room_info = request.files['room_info']
        
        if pdf_zip.filename == '' or room_info.filename == '':
            flash('No file selected.')
            return redirect(request.url)
        
        if pdf_zip and allowed_file(pdf_zip.filename, 'zip') and room_info and allowed_file(room_info.filename, 'xlsx'):
            # Create unique session folder
            session_id = str(uuid.uuid4())
            base_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
            os.makedirs(base_dir, exist_ok=True)

            # Save room_info.xlsx
            room_info_path = os.path.join(base_dir, 'room_info.xlsx')
            room_info.save(room_info_path)

            # Process PDF zip
            pdf_zip_path = os.path.join(base_dir, 'pdfs.zip')
            pdf_zip.save(pdf_zip_path)
            
            # Extract PDFs
            pdf_extract_folder = os.path.join(base_dir, 'pdfs')
            os.makedirs(pdf_extract_folder, exist_ok=True)
            with zipfile.ZipFile(pdf_zip_path, 'r') as zip_ref:
                zip_ref.extractall(pdf_extract_folder)  # Fixed indentation here

            # Configure generator paths
            spg.PDF_INPUT_FOLDER = pdf_extract_folder
            spg.MERGED_EXCEL_PATH = os.path.join(base_dir, 'merged_excel.xlsx')
            spg.PROJECT_FOLDER = base_dir
            spg.OUTPUT_FOLDER = os.path.join(base_dir, 'OUTPUT')
            spg.ROOM_INFO_PATH = room_info_path
            os.makedirs(spg.OUTPUT_FOLDER, exist_ok=True)

            # Run generator
            spg.main()

            # Create output zip
            output_zip_path = os.path.join(base_dir, 'output.zip')
            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(spg.OUTPUT_FOLDER):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, spg.OUTPUT_FOLDER)
                        zipf.write(file_path, arcname)

            return send_file(output_zip_path, as_attachment=True)
        else:
            flash('Please upload a ZIP file for PDFs and an XLSX file for room info.')
            return redirect(request.url)
    
    return render_template('upload.html')

if __name__ == "__main__":
    # Use the PORT environment variable if set, otherwise default to 8000
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
