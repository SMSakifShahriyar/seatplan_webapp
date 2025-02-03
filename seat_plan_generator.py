# seatplan.py
import os
import re
import pdfplumber
import pandas as pd
from datetime import datetime
from dateutil import parser
from fpdf import FPDF

# ============================================================
# GLOBAL VARIABLES (These will be overwritten by the web app)
# ============================================================
PDF_INPUT_FOLDER = r"C:\Path\To\Default\PDFs"   # Will be replaced by the web app
MERGED_EXCEL_PATH = os.path.join(os.getcwd(), "merged_excel.xlsx")
ROOM_INFO_PATH = r"C:\Path\To\Default\room_info.xlsx"  # Will be replaced by the web app
OUTPUT_FOLDER = os.path.join(os.getcwd(), "output")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ============================================================
# HELPER FUNCTIONS FOR TEXT WRAPPING & VERTICAL CENTERING
# ============================================================
def wrap_long_word_with_hyphen(pdf, word, cell_width, indent="     "):
    parts = word.split('-')
    lines = []
    current_line = parts[0]
    for part in parts[1:]:
        candidate = current_line + '-' + part
        if pdf.get_string_width(candidate) <= cell_width:
            current_line = candidate
        else:
            lines.append(current_line + '-')
            current_line = indent + part
    lines.append(current_line)
    return lines

def wrap_text(pdf, text, cell_width):
    indent = "     "  # fixed indent for lines after a break in a long word
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        candidate = word if current_line == "" else current_line + " " + word
        if pdf.get_string_width(candidate) <= cell_width:
            current_line = candidate
        else:
            if current_line:
                lines.append(current_line)
                current_line = ""
                if pdf.get_string_width(word) <= cell_width:
                    current_line = word
                else:
                    if '-' in word:
                        hyphen_lines = wrap_long_word_with_hyphen(pdf, word, cell_width, indent)
                        lines.extend(hyphen_lines[:-1])
                        current_line = hyphen_lines[-1]
                    else:
                        char_line = ""
                        for ch in word:
                            if pdf.get_string_width(char_line + ch) <= cell_width:
                                char_line += ch
                            else:
                                lines.append(char_line)
                                char_line = ch
                        current_line = char_line
            else:
                if pdf.get_string_width(word) <= cell_width:
                    current_line = word
                else:
                    if '-' in word:
                        hyphen_lines = wrap_long_word_with_hyphen(pdf, word, cell_width, indent)
                        lines.extend(hyphen_lines)
                        current_line = ""
                    else:
                        char_line = ""
                        for ch in word:
                            if pdf.get_string_width(char_line + ch) <= cell_width:
                                char_line += ch
                            else:
                                lines.append(char_line)
                                char_line = ch
                        current_line = char_line
    if current_line:
        lines.append(current_line)
    return "\n".join(lines)

def ensure_space(pdf, height_needed):
    if pdf.get_y() + height_needed > pdf.h - pdf.b_margin:
        pdf.add_page()

def vertical_centered_row(pdf, data, widths, line_height, alignments=None, cell_padding=2):
    if alignments is None:
        alignments = ["C"] * len(data)
    cell_lines = []
    max_lines = 0
    for i, cell in enumerate(data):
        effective_width = widths[i] - 2 * cell_padding
        wrapped = wrap_text(pdf, cell, effective_width)
        lines = wrapped.split("\n")
        cell_lines.append(lines)
        max_lines = max(max_lines, len(lines))
    row_height = max_lines * line_height

    ensure_space(pdf, row_height)
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    x_current = x_start

    for i, lines in enumerate(cell_lines):
        cell_width = widths[i]
        if len(lines) < max_lines:
            lines += [""] * (max_lines - len(lines))
        text_height = len(lines) * line_height
        vertical_offset = (row_height - text_height) / 2
        y_current = y_start + vertical_offset
        for line in lines:
            text_width = pdf.get_string_width(line)
            if alignments[i] == "C":
                x_text = x_current + cell_padding + ((cell_width - 2*cell_padding) - text_width) / 2
            elif alignments[i] == "L":
                x_text = x_current + cell_padding
            elif alignments[i] == "R":
                x_text = x_current + cell_width - text_width - cell_padding
            else:
                x_text = x_current + cell_padding + ((cell_width - 2*cell_padding) - text_width) / 2
            pdf.text(x_text, y_current + line_height/2, line)
            y_current += line_height
        pdf.rect(x_current, y_start, cell_width, row_height)
        x_current += cell_width
    pdf.set_xy(x_start, y_start + row_height)

def print_top_info_table(pdf, group_info, metadata):
    left_labels = ["Faculty ID", "Program", "Course Code", "Credits", "Exam Date"]
    right_labels = ["Faculty Name", "Batch Number", "Course Title", "Section", "Exam Time"]
    left_values = [
        group_info.get("Faculty ID", ""),
        metadata.get("Program", ""),
        group_info.get("Course Code", ""),
        group_info.get("Credits", ""),
        ""
    ]
    right_values = [
        group_info.get("Faculty Name", ""),
        group_info.get("Batch Number", ""),
        group_info.get("Course Title", ""),
        group_info.get("Section", ""),
        ""
    ]
    cell_widths = [95, 95]
    line_height = 8
    pdf.set_font("Arial", "", 10)
    for i in range(5):
        left_text = f"{left_labels[i]}: {left_values[i]}"
        right_text = f"{right_labels[i]}: {right_values[i]}"
        vertical_centered_row(pdf, [left_text, right_text], cell_widths, line_height, alignments=["L", "L"])

# ============================================================
# PDF DATA EXTRACTION FUNCTIONS
# ============================================================
def extract_program_from_lines(lines):
    program_lines = []
    capturing = False
    for line in lines:
        if "Program" in line:
            capturing = True
            after = line.split("Program", 1)[1].strip()
            program_lines.append(after)
        elif capturing:
            if "Batch Number" in line:
                part = line.split("Batch Number", 1)[0].strip()
                if part:
                    program_lines.append(part)
                break
            elif "Course Code" in line:
                part = line.split("Course Code", 1)[0].strip()
                if part:
                    program_lines.append(part)
                break
            else:
                program_lines.append(line.strip())
    return " ".join(program_lines).replace('"', '').strip()

def extract_metadata_from_text(text):
    metadata = {}
    lines = text.split("\n")
    metadata["Program"] = extract_program_from_lines(lines)
    faculty_match = re.search(r'Faculty ID\s+(\S+)\s+Faculty Name\s+([^\n]+)', text, re.IGNORECASE)
    if faculty_match:
        metadata["Faculty ID"] = faculty_match.group(1).strip()
        metadata["Faculty Name"] = faculty_match.group(2).strip()
    else:
        metadata["Faculty ID"] = ""
        metadata["Faculty Name"] = ""
    batch_match = re.search(r'Batch Number\s+(\S+)', text, re.IGNORECASE)
    metadata["Batch Number"] = batch_match.group(1).strip() if batch_match else ""
    course_code_match = re.search(r'Course Code\s+(\S+)', text, re.IGNORECASE)
    metadata["Course Code"] = course_code_match.group(1).strip() if course_code_match else ""
    course_title_match = re.search(r'Course Title\s+([\s\S]+?)\s+Credits', text, re.IGNORECASE)
    metadata["Course Title"] = course_title_match.group(1).replace("\n", " ").strip() if course_title_match else ""
    credits_match = re.search(r'Credits\s+(\S+)', text, re.IGNORECASE)
    metadata["Credits"] = credits_match.group(1).strip() if credits_match else ""
    section_match = re.search(r'Section\s+(\S+)', text, re.IGNORECASE)
    metadata["Section"] = section_match.group(1).strip() if section_match else ""
    return metadata

def extract_data_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        full_text = first_page.extract_text()
        print(f"Processing {os.path.basename(pdf_path)}...")
        metadata = extract_metadata_from_text(full_text)
        table_data = []
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and row[0] and row[0].strip().isdigit():
                        table_data.append(row)
        extracted_data = []
        for row in table_data:
            extracted_data.append({
                "Student ID": row[1].strip() if row[1] else "",
                "Student Name": row[2].strip() if row[2] else "",
                "M Batch": row[3].strip() if row[3] else "",
                "Credits": metadata.get("Credits", ""),
                "Program": metadata.get("Program", ""),
                "Faculty ID": metadata.get("Faculty ID", ""),
                "Faculty Name": metadata.get("Faculty Name", ""),
                "Section": metadata.get("Section", ""),
                "Batch Number": metadata.get("Batch Number", ""),
                "Course Code": metadata.get("Course Code", ""),
                "Course Title": metadata.get("Course Title", "")
            })
        return extracted_data

def merge_pdf_data_to_excel():
    columns = [
        "Student ID", "Student Name", "M Batch", "Credits", "Program",
        "Faculty ID", "Faculty Name", "Section", "Batch Number",
        "Course Code", "Course Title"
    ]
    all_data = []
    for file_name in os.listdir(PDF_INPUT_FOLDER):
        if file_name.lower().endswith(".pdf"):
            pdf_path = os.path.join(PDF_INPUT_FOLDER, file_name)
            data = extract_data_from_pdf(pdf_path)
            all_data.extend(data)
    df = pd.DataFrame(all_data, columns=columns)
    df = df.drop_duplicates(subset=["Student ID"])
    df["MID"] = df["Student ID"].astype(str).str[4:6].astype(int, errors="ignore")
    df["M Batch"] = pd.to_numeric(df["M Batch"], errors="coerce")
    df.sort_values(by=["Batch Number", "M Batch", "MID"], ascending=[True, False, False], inplace=True)
    df.drop(columns=["MID"], inplace=True)
    df.to_excel(MERGED_EXCEL_PATH, index=False)
    print(f"✅ Merged Excel file saved at: {MERGED_EXCEL_PATH}")

# ============================================================
# SEAT ASSIGNMENT FUNCTIONS
# ============================================================
def is_blocked_seat(room, row, column):
    blocked_seats = {
        'A002': [(1, 1), (1, 5), (6, 1), (6, 5)],
        'A008': [(1, 1), (1, 5), (6, 1), (6, 5)],
    }
    return (room in blocked_seats) and ((row, column) in blocked_seats[room])

def get_primary_secondary_columns(num_cols):
    col_indices = list(range(num_cols))
    primary_0based = [c for c in reversed(col_indices) if c % 2 == (num_cols-1) % 2]
    secondary_0based = [c for c in reversed(col_indices) if c not in primary_0based]
    primary_cols = [x+1 for x in primary_0based]
    secondary_cols = [x+1 for x in secondary_0based]
    return primary_cols, secondary_cols

def try_seat_two_batches_in_room(room, df_rooms, batch_students, seat_assignments):
    if room not in df_rooms['Room'].values:
        print(f"Warning: Room {room} not found in room data. Skipping this room.")
        return False
    room_data = df_rooms[df_rooms['Room'] == room].iloc[0]
    rows, cols = room_data['Row'], room_data['Column']
    primary_cols, secondary_cols = get_primary_secondary_columns(cols)
    available_primary_seats = []
    for col in primary_cols:
        for r in range(1, rows + 1):
            if not is_blocked_seat(room, r, col):
                available_primary_seats.append((r, col))
    primary_capacity = len(available_primary_seats)
    available_secondary_seats = []
    for col in secondary_cols:
        for r in range(1, rows + 1):
            if not is_blocked_seat(room, r, col):
                available_secondary_seats.append((r, col))
    secondary_capacity = len(available_secondary_seats)
    sorted_batches = sorted(batch_students.keys(), key=lambda b: len(batch_students[b]), reverse=True)
    primary_batch = None
    for b in sorted_batches:
        if len(batch_students[b]) >= primary_capacity:
            primary_batch = b
            break
    if primary_batch is None:
        return False
    secondary_batch = None
    for b in sorted_batches:
        if b == primary_batch:
            continue
        if len(batch_students[b]) >= secondary_capacity:
            secondary_batch = b
            break
    if secondary_batch is None:
        return False
    primary_students = batch_students[primary_batch][:primary_capacity]
    secondary_students = batch_students[secondary_batch][:secondary_capacity]
    batch_students[primary_batch] = batch_students[primary_batch][primary_capacity:]
    batch_students[secondary_batch] = batch_students[secondary_batch][secondary_capacity:]
    for i, (r, col) in enumerate(available_primary_seats):
        seat_assignments.append({
            'Room': room,
            'Row': r,
            'Column': col,
            'Student ID': primary_students[i],
            'Batch': primary_batch
        })
    for i, (r, col) in enumerate(available_secondary_seats):
        seat_assignments.append({
            'Room': room,
            'Row': r,
            'Column': col,
            'Student ID': secondary_students[i],
            'Batch': secondary_batch
        })
    return True

def seat_leftover_in_room_min_batches(room, df_rooms, batch_students, seat_assignments):
    if room not in df_rooms['Room'].values:
        print(f"Warning: Room {room} not found in room data. Skipping this room.")
        return
    room_data = df_rooms[df_rooms['Room'] == room].iloc[0]
    rows, cols = room_data['Row'], room_data['Column']
    col_order = list(range(cols, 0, -1))
    sorted_batches = sorted(batch_students.keys(), key=lambda b: len(batch_students[b]), reverse=True)
    column_assignments = []
    prev_batch_per_row = {}
    for col in col_order:
        for row in range(1, rows + 1):
            chosen_batch = None
            for b in sorted_batches:
                if len(batch_students[b]) > 0 and prev_batch_per_row.get(row) != b:
                    chosen_batch = b
                    break
            if chosen_batch is None:
                chosen_batch = next((b for b in sorted_batches if len(batch_students[b]) > 0), None)
            if chosen_batch is None:
                continue
            sid = batch_students[chosen_batch].pop(0)
            column_assignments.append({
                'Room': room,
                'Row': row,
                'Column': col,
                'Student ID': sid,
                'Batch': chosen_batch
            })
            prev_batch_per_row[row] = chosen_batch
            if len(batch_students[chosen_batch]) == 0:
                sorted_batches.remove(chosen_batch)
    seat_assignments.extend(column_assignments)

def generate_seating_plan_pdf(room, rows, cols, seat_assignments, metadata, output_dir, student_info_lookup):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)
    pdf.set_font("Arial", "B", 9)
    total_cols = cols + 2
    col_width = 280 / total_cols

    exam_date_raw = metadata.get("Exam date", "")
    try:
        dt = parser.parse(str(exam_date_raw), dayfirst=True)
        formatted_date = dt.strftime("%d-%m-%Y")
    except Exception:
        formatted_date = exam_date_raw
    exam_info = f"Exam Date: {formatted_date}    Time: {metadata.get('Time', '')}"
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, f"Seat Plan ({metadata.get('Semester', '')})_{metadata.get('Shift', '')}", ln=True, align="C")
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 8, exam_info, ln=True, align="C")
    blocked_seats_count = sum(1 for r in range(1, rows + 1) for c in range(1, cols + 1) if is_blocked_seat(room, r, c))
    adjusted_capacity = (rows * cols) - blocked_seats_count
    pdf.cell(0, 8, f"Room #{room}    Capacity = {adjusted_capacity}", ln=True, align="C")
    
    pdf.cell(col_width, 8, "", border=1, align="C")
    for i in range(cols, 0, -1):
        pdf.cell(col_width, 8, f"C{i}", border=1, align="C")
    pdf.cell(col_width, 8, "", border=1, ln=True, align="C")
    
    pdf.cell(col_width, 8, "Batch/Sl. No.", border=1, align="C")
    for i in range(cols):
        batches_in_col = [seat['Batch'] for seat in seat_assignments if seat['Column'] == i + 1]
        unique_batches = "+".join(sorted(map(str, set(batches_in_col))))
        pdf.cell(col_width, 8, unique_batches, border=1, align="C")
    pdf.cell(col_width, 8, "Batch/Sl. No.", border=1, ln=True, align="C")
    
    pdf.set_font("Arial", "", 8)
    for row in range(1, rows + 1):
        pdf.cell(col_width, 8, str(row), border=1, align="C")
        for col in range(1, cols + 1):
            if is_blocked_seat(room, row, col):
                student_info = "X"
            else:
                seat = next((seat for seat in seat_assignments if seat['Row'] == row and seat['Column'] == col), None)
                if seat:
                    stud_id = str(seat['Student ID']).strip()
                    info = student_info_lookup.get(stud_id, {})
                    m_batch = info.get("M Batch", "")
                    batch_num = info.get("Batch Number", "")
                    section = info.get("Section", "")
                    if str(m_batch) != str(batch_num):
                        student_info = f"{stud_id} ({m_batch} {section})"
                    else:
                        student_info = f"{stud_id} ({section})"
                else:
                    student_info = ""
            text_width = pdf.get_string_width(student_info)
            if text_width > col_width - 2:
                current_font_size = pdf.font_size_pt
                pdf.set_font("Arial", "", max(6, current_font_size - 2))
                pdf.cell(col_width, 8, student_info, border=1, align="C")
                pdf.set_font("Arial", "", current_font_size)
            else:
                pdf.cell(col_width, 8, student_info, border=1, align="C")
        pdf.cell(col_width, 8, str(row), border=1, ln=True, align="C")
    
    for _ in range(2):
        pdf.cell(col_width, 8, "", border=1)
        pdf.cell(cols * col_width, 8, "", border=1)
        pdf.cell(col_width, 8, "", border=1, ln=True)
    
    pdf.set_font("Arial", "B", 8)
    room_batches = set(seat['Batch'] for seat in seat_assignments)
    for batch in sorted(room_batches):
        students = [seat['Student ID'] for seat in seat_assignments if seat['Batch'] == batch]
        if students:
            batch_summary = f"{batch}th {metadata.get('Shift', '')} = {len(students)} = ({students[0]}-{students[-1]})"
        else:
            batch_summary = ""
        pdf.cell(col_width, 8, "", border=1)
        pdf.cell(cols * col_width, 8, batch_summary, border=1, align="C")
        pdf.cell(col_width, 8, "", border=1, ln=True)
    
    pdf_output_path = os.path.join(output_dir, f"Seating_Plan_Room_{room}.pdf")
    pdf.output(pdf_output_path)
    print(f"PDF generated for Room {room} at {pdf_output_path}")
    return pdf_output_path

def generate_seating_plan_display(df_students, df_rooms, metadata, output_dir):
    df_students["Student ID"] = df_students["Student ID"].astype(str).str.strip()
    df_students["M Batch"] = df_students["M Batch"].fillna("").astype(str).str.replace(".0", "", regex=False).str.strip()
    df_students["Batch Number"] = df_students["Batch Number"].fillna("").astype(str).str.strip()
    df_students["Section"] = df_students["Section"].fillna("").astype(str).str.strip()
    student_info_lookup = df_students.set_index("Student ID").to_dict("index")
    
    batch_students = {}
    for batch, grp in df_students.groupby('Batch Number'):
        batch_students[batch] = list(grp['Student ID'])
    df_rooms['Room'] = df_rooms['Room'].astype(str)
    all_rooms = df_rooms['Room'].unique().tolist()
    seat_assignments = []
    two_batch_phase = True
    for room in all_rooms:
        print(f"Seating students in Room {room} ...")
        total_left = sum(len(v) for v in batch_students.values())
        if total_left == 0:
            print(f"No students left for Room {room}.")
            continue
        if two_batch_phase:
            success = try_seat_two_batches_in_room(room, df_rooms, batch_students, seat_assignments)
            if not success:
                print(f"Cannot fill Room {room} with exactly 2 batches. Switching to leftover mode.")
                seat_leftover_in_room_min_batches(room, df_rooms, batch_students, seat_assignments)
                two_batch_phase = False
        else:
            seat_leftover_in_room_min_batches(room, df_rooms, batch_students, seat_assignments)
        current_room_seats = [s for s in seat_assignments if s['Room'] == room]
        if current_room_seats:
            room_data = df_rooms[df_rooms['Room'] == room].iloc[0]
            rows, cols = room_data['Row'], room_data['Column']
            generate_seating_plan_pdf(room, rows, cols, current_room_seats, metadata, output_dir, student_info_lookup)
        else:
            print(f"Room {room} has no seated students.")
        if sum(len(v) for v in batch_students.values()) == 0:
            print("All students have been seated.")
            break
    return seat_assignments

# ============================================================
# SUMMARY FUNCTIONS
# ============================================================
def get_summary_data(df_students, seating_assignments):
    df_students["Student ID"] = df_students["Student ID"].astype(str).str.strip()
    df_students["M Batch"] = df_students["M Batch"].astype(str).str.strip()
    df_students["Batch Number"] = df_students["Batch Number"].astype(str).str.strip()
    df_students["Section"] = df_students["Section"].astype(str).str.strip()
    seat_order = {}
    for i, s in enumerate(seating_assignments):
        sid = str(s["Student ID"]).strip()
        seat_order[sid] = i
    sa_df = pd.DataFrame(seating_assignments)
    sa_df["Student ID"] = sa_df["Student ID"].astype(str).str.strip()
    merged = pd.merge(sa_df, df_students[["Student ID", "Section", "M Batch", "Batch Number"]], on="Student ID", how="left")
    merged["Batch"] = merged["Batch"].astype(str).str.strip()
    merged["MID"] = merged["Student ID"].str[4:6]
    if "Room" in merged.columns:
        merged["Room"] = merged["Room"].astype(str).str.strip()
    elif "Room No" in merged.columns:
        merged["Room"] = merged["Room No"].astype(str).str.strip()
    else:
        merged["Room"] = ""
    merged = merged.drop_duplicates(subset=["Student ID", "Room", "Row", "Column"])
    
    summary_data = {}
    row_totals = {}
    col_totals = {}
    grand_total = 0
    for room, group_room in merged.groupby("Room", sort=False):
        summary_data[room] = {}
        room_total = 0
        for batch, group_batch in group_room.groupby("Batch", sort=False):
            group_batch = group_batch.copy()
            group_batch["special"] = group_batch["MID"].apply(lambda x: "DAY" if str(x) == "38" else "")
            group_batch["subgroup_key"] = group_batch.apply(
                lambda row: (
                    "SAME" if str(row["Batch Number"]).strip() == str(row["M Batch"]).strip() else "DIFF",
                    row["special"],
                    str(row["M Batch"]).strip(),
                    str(row["Section"]).strip()
                ),
                axis=1
            )
            group_batch = group_batch.sort_values("Student ID", key=lambda col: col.map(lambda sid: seat_order.get(str(sid).strip(), 9999999)))
            subgroup_total = 0
            subgroup_lines = []
            for key, subgroup in group_batch.groupby("subgroup_key", sort=False):
                ids = subgroup["Student ID"].tolist()
                count = len(ids)
                subgroup_total += count
                if key[0] == "DIFF":
                    if count > 1:
                        line = f"({ids[0]}-{ids[-1]}) ({key[2]} {key[3]})"
                    else:
                        line = f"{ids[0]} ({key[2]} {key[3]})"
                else:
                    if count > 1:
                        line = f"({ids[0]}-{ids[-1]}) ({key[3]})"
                    else:
                        line = f"{ids[0]} ({key[3]})"
                if key[1] == "DAY":
                    line += " (Day)"
                subgroup_lines.append(line)
            cell_content = "\n".join(subgroup_lines) + f"\nTotal={subgroup_total}"
            summary_data[room][batch] = cell_content
            col_totals[batch] = col_totals.get(batch, 0) + subgroup_total
            room_total += subgroup_total
            grand_total += subgroup_total
        row_totals[room] = room_total
    return summary_data, row_totals, col_totals, grand_total

def generate_summary_pdf(df_students, seating_assignments, summary_header, output_file):
    summary_data, row_totals, col_totals, grand_total = get_summary_data(df_students, seating_assignments)
    rooms = list(summary_data.keys())
    try:
        rooms.sort(key=lambda x: int(x))
    except:
        rooms.sort()
    batches = list(col_totals.keys())
    try:
        batches.sort(key=lambda x: int(''.join(filter(str.isdigit, x))) if any(ch.isdigit() for ch in x) else x)
    except:
        batches.sort()
    pdf = FPDF(orientation="L", unit="mm", format="A3")
    pdf.add_page()
    margin = 10
    available_width = 420 - 2 * margin
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.set_font("Arial", "B", 16)
    title_line = f"{summary_header.get('Term', '')} Term Exam {summary_header.get('Semester', '')} ({summary_header.get('Shift', '')} Batch)"
    pdf.cell(0, 10, title_line, ln=True, align="C")
    pdf.set_font("Arial", "B", 14)
    dept_line = "Department of Civil Engineering, Uttara University"
    pdf.cell(0, 8, dept_line, ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    exam_date_raw = summary_header.get("Exam date", "")
    try:
        dt = parser.parse(str(exam_date_raw), dayfirst=True)
        formatted_date = dt.strftime("%d-%m-%Y")
    except Exception as e:
        formatted_date = str(exam_date_raw)
    exam_day = str(summary_header.get("Day", "")).strip() or "Unknown Day"
    date_time_line = f"Date: {formatted_date} ({summary_header.get('Time', '').strip()})_{exam_day}"
    pdf.cell(0, 8, date_time_line, ln=True, align="C")
    pdf.ln(5)
    total_columns = 2 + len(batches)
    cell_width = available_width / total_columns
    pdf.set_font("Arial", "B", 10)
    header_row = ["Room No./Batch"] + batches + ["Room Total"]
    vertical_centered_row(pdf, header_row, [cell_width] * total_columns, line_height=8, alignments=["C"] * total_columns)
    pdf.set_font("Arial", "", 10)
    for room in rooms:
        row = [room]
        for batch in batches:
            cell = summary_data.get(room, {}).get(batch, "")
            row.append(cell)
        row.append(str(row_totals.get(room, "")))
        vertical_centered_row(pdf, row, [cell_width] * total_columns, line_height=8, alignments=["C"] * total_columns)
    footer_row = ["Batch Totals"]
    for batch in batches:
        footer_row.append(str(col_totals.get(batch, 0)))
    footer_row.append(str(grand_total))
    pdf.set_font("Arial", "B", 10)
    vertical_centered_row(pdf, footer_row, [cell_width] * total_columns, line_height=8, alignments=["C"] * total_columns)
    pdf.output(output_file)
    print(f"Summary PDF generated: {output_file}")

# ============================================================
# ENVELOPE & ATTENDANCE FUNCTIONS
# ============================================================
def generate_envelope_data(df_courses):
    envelope_list = []
    groups = df_courses.groupby(["Faculty Name", "Course Code", "Course Title"])
    for (faculty, course_code, course_title), group in groups:
        teacher = group.iloc[0].get("Name of Course Teacher", faculty)
        envelope_list.append({
            "Faculty Name": faculty,
            "Course Code": course_code,
            "Course Title": course_title,
            "Name of Course Teacher": teacher
        })
    return envelope_list

def draw_envelope(pdf, envelope, exam_details, x, y, w, h):
    pdf.rect(x, y, w, h)
    inner_margin = 5
    x_in = x + inner_margin
    y_in = y + inner_margin
    available_width = w - 2 * inner_margin
    pdf.set_font("Arial", "B", 16)
    line_height = 8
    pdf.set_xy(x_in, y_in)
    pdf.cell(available_width, line_height, "DEPARTMENT OF CIVIL ENGINEERING", border=0, ln=1, align="C")
    pdf.cell(available_width, line_height, "UTTARA UNIVERSITY", border=0, ln=1, align="C")
    y_cursor = pdf.get_y() + 3
    pdf.set_font("Arial", "B", 12)
    exam_line1 = exam_details.get("Exam Line1", "MAKEUP SEMESTER FINAL EXAM")
    exam_line2 = exam_details.get("Exam Line2", "FALL 2024 SEMESTER")
    pdf.set_xy(x_in, y_cursor)
    pdf.cell(available_width, line_height, exam_line1, border=0, ln=1, align="C")
    pdf.cell(available_width, line_height, exam_line2, border=0, ln=1, align="C")
    y_cursor = pdf.get_y() + 5
    pdf.set_font("Arial", "", 11)
    details = [
        ("Course Code:", envelope.get("Course Code", "")),
        ("Course Title:", envelope.get("Course Title", "")),
        ("Name of Course Teacher:", envelope.get("Name of Course Teacher", envelope.get("Faculty Name", ""))),
        ("No. of Copies:", "")
    ]
    for label, value in details:
        pdf.set_xy(x_in, y_cursor)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(pdf.get_string_width(label) + 2, line_height, label, border=0, align="L")
        pdf.set_font("Arial", "", 11)
        pdf.cell(available_width - pdf.get_string_width(label) - 2, line_height, value, border=0, align="L")
        y_cursor = pdf.get_y() + 8
    signature_x = x + (w * 0.6)
    pdf.set_xy(signature_x, y_cursor)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(available_width * 0.4, line_height, "Signature of Invigilator:", border=0, align="L")
    y_cursor = pdf.get_y() + 10

def generate_envelopes_pdf(envelope_list, exam_details, output_file):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    margin = 10
    page_width = 210
    page_height = 297
    envelope_width = page_width - 2 * margin
    gap_between = 45
    fixed_envelope_height = 100
    envelope_height = min(fixed_envelope_height, (page_height - 2 * margin - gap_between) / 2)
    count = 0
    for env in envelope_list:
        if count % 2 == 0:
            if count != 0:
                pdf.add_page()
            x = margin
            y = margin + 20
        else:
            x = margin
            y = margin + envelope_height + gap_between
        draw_envelope(pdf, env, exam_details, x, y, envelope_width, envelope_height)
        count += 1
    pdf.output(output_file)
    print(f"Envelopes PDF generated: {output_file}")

def generate_attendance_sheet_pdf(group_info, student_list, metadata, room_no, group_room_counts, output_dir):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=10)
    pdf.add_page()
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(BASE_DIR, "assets", "uu.png")
    logo_width = 30
    logo_x = (210 - logo_width) / 2
    try:
        pdf.image(logo_path, x=logo_x, y=10, w=logo_width)
    except Exception as e:
        print(f"Logo not found: {e}")
    pdf.ln(16)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "UTTARA UNIVERSITY", ln=True, align="C")
    pdf.ln(1)
    pdf.set_font("Arial", "B", 14)
    exam_title = f"{metadata.get('Semester', 'Unknown Semester')} - {metadata.get('Term', 'Unknown Term')} Term Exam Attendance"
    pdf.cell(0, 10, exam_title, ln=True, align="C")
    pdf.ln(5)
    
    print_top_info_table(pdf, group_info, metadata)
    pdf.ln(5)
    
    student_col_widths = [10, 30, 55, 15, 20, 20, 20, 20]
    student_headers = ["SL", "Student ID", "Student Name", "M Batch", "Room No", "Answer Script No", "Student Sign", "Remarks"]
    pdf.set_font("Arial", "B", 10)
    vertical_centered_row(pdf, student_headers, student_col_widths, line_height=8)
    
    pdf.set_font("Arial", "", 10)
    for idx, student in enumerate(student_list, 1):
        row_data = [
            str(idx),
            str(student.get("Student ID", "")),
            student.get("Student Name", ""),
            str(student.get("M Batch", "")),
            room_no,
            "",
            "",
            ""
        ]
        vertical_centered_row(pdf, row_data, student_col_widths, line_height=8,
                              alignments=["C", "C", "L", "C", "C", "C", "C", "C"])
    
    blank_row = ["" for _ in student_col_widths]
    for _ in range(3):
        vertical_centered_row(pdf, blank_row, student_col_widths, line_height=8, alignments=["C"] * len(student_col_widths))
    
    pdf.ln(5)
    
    invigilator_col_widths = [20, 20, 50, 50, 50]
    invigilator_headers = ["", "No of Students", "Invigilator's Name & Sign", "Invigilator's Name & Sign", "Invigilator's Name & Sign"]
    pdf.set_font("Arial", "B", 10)
    vertical_centered_row(pdf, invigilator_headers, invigilator_col_widths, line_height=8)
    
    pdf.set_font("Arial", "", 10)
    for _ in range(4):
        vertical_centered_row(pdf, ["" for _ in invigilator_col_widths], invigilator_col_widths, line_height=8)
    
    ensure_space(pdf, 15)
    pdf.ln(5)
    pdf.cell(0, 8, "Total Number of Students: ", ln=True, align="L")
    
    filename = f"Attendance_{group_info.get('Faculty Name','')}_{group_info.get('Batch Number','')}_{group_info.get('Section','')}_Room_{room_no}.pdf"
    pdf_output_path = os.path.join(output_dir, filename)
    pdf.output(pdf_output_path)
    print(f"Generated attendance sheet: {pdf_output_path}")
    return pdf_output_path

def generate_attendance_sheets(df_students, metadata, seating_assignments, output_dir):
    attendance_output_dir = os.path.join(output_dir, "Attendance_Sheets")
    os.makedirs(attendance_output_dir, exist_ok=True)
    
    unique_assignments = {}
    for s in seating_assignments:
        sid = str(s.get("Student ID", "")).strip()
        room = (s.get("Room") or s.get("Room No") or "").strip()
        key = (sid, room)
        unique_assignments[key] = s
    seating_assignments = list(unique_assignments.values())
    
    grouped = df_students.groupby(["Faculty Name", "Batch Number", "Section"])
    for group_keys, group_df in grouped:
        group_df = group_df.drop_duplicates(subset=["Student ID"])
        faculty_name, batch_number, section = group_keys
        first_row = group_df.iloc[0]
        group_info = {
            "Faculty ID": first_row.get("Faculty ID", ""),
            "Faculty Name": faculty_name,
            "Program": first_row.get("Program", ""),
            "Batch Number": batch_number,
            "Course Code": first_row.get("Course Code", ""),
            "Course Title": first_row.get("Course Title", ""),
            "Credits": first_row.get("Credits", ""),
            "Section": section,
        }
        group_student_ids = set(group_df["Student ID"].astype(str).str.strip())
        group_seat_assignments = [s for s in seating_assignments if str(s.get("Student ID", "")).strip() in group_student_ids]
        seating_assignments = [s for s in seating_assignments if str(s.get("Student ID", "")).strip() not in group_student_ids]
        assignments_by_room = {}
        for s in group_seat_assignments:
            room = s.get("Room") or s.get("Room No")
            if room and room.strip() != "":
                room = room.strip()
                assignments_by_room.setdefault(room, []).append(s)
        for room, seat_list in assignments_by_room.items():
            room_student_ids = set(str(s.get("Student ID", "")).strip() for s in seat_list)
            room_students_df = group_df[group_df["Student ID"].astype(str).isin(room_student_ids)]
            room_students_df = room_students_df.drop_duplicates(subset=["Student ID"])
            room_student_list = []
            for _, row in room_students_df.iterrows():
                room_student_list.append({
                    "Student ID": str(row.get("Student ID", "")).strip(),
                    "Student Name": row.get("Student Name", ""),
                    "M Batch": row.get("M Batch", "")
                })
            room_counts = {room: len(room_student_list)}
            generate_attendance_sheet_pdf(group_info, room_student_list, metadata, room, room_counts, attendance_output_dir)
    
    return seating_assignments

# ============================================================
# MAIN FUNCTION
# ============================================================
def main():
    merge_pdf_data_to_excel()
    try:
        df_students = pd.read_excel(MERGED_EXCEL_PATH)
        print("Student data loaded successfully!")
    except Exception as e:
        print(f"Error loading student data: {e}")
        return
    try:
        df_rooms = pd.read_excel(ROOM_INFO_PATH, sheet_name=0)
        metadata = pd.read_excel(ROOM_INFO_PATH, sheet_name=1).iloc[0].to_dict()
        print("Room data and metadata loaded successfully!")
    except Exception as e:
        print(f"Error loading room data or metadata: {e}")
        return
    seating_assignments = generate_seating_plan_display(df_students, df_rooms, metadata, OUTPUT_FOLDER)
    unique_assignments = {}
    for s in seating_assignments:
        sid = str(s.get("Student ID", "")).strip()
        room = (s.get("Room") or s.get("Room No") or "").strip()
        key = (sid, room)
        unique_assignments[key] = s
    seating_assignments = list(unique_assignments.values())
    
    generate_attendance_sheets(df_students, metadata, seating_assignments, OUTPUT_FOLDER)
    try:
        df_courses = pd.read_excel(MERGED_EXCEL_PATH)
        print("Courses data loaded successfully!")
    except Exception as e:
        print(f"Error loading courses data: {e}")
        return
    try:
        df_exam = pd.read_excel(ROOM_INFO_PATH, sheet_name=2)
        exam_details = df_exam.iloc[0].to_dict()
        print("Exam details loaded successfully!")
    except Exception as e:
        print(f"Error loading exam details: {e}")
        exam_details = {"Exam Line1": "MAKEUP SEMESTER FINAL EXAM", "Exam Line2": "FALL 2024 SEMESTER"}
    envelope_list = generate_envelope_data(df_courses)
    envelopes_output_file = os.path.join(OUTPUT_FOLDER, "Envelopes.pdf")
    generate_envelopes_pdf(envelope_list, exam_details, envelopes_output_file)
    try:
        df_summary_metadata = pd.read_excel(ROOM_INFO_PATH, sheet_name=1)
        summary_header = df_summary_metadata.iloc[0].to_dict()
        print("Summary header details loaded successfully!")
    except Exception as e:
        print(f"Error loading summary header details: {e}")
        summary_header = {
            "Term": "Final",
            "Semester": "Fall 2024",
            "Shift": "Evening",
            "Exam date": "12/4/2024",
            "Time": "6:30PM-8:30PM",
            "Day": "Wednesday"
        }
    summary_output_file = os.path.join(OUTPUT_FOLDER, "Summary.pdf")
    generate_summary_pdf(df_students, seating_assignments, summary_header, summary_output_file)

if __name__ == "__main__":
    main()
