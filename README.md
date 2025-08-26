
---

# Seat Plan Generator

**Automates exam seating and documentation.**
The tool processes student lists, assigns seats with adjacency rules, and generates all required seating and attendance materials.

## Key Features

* **Input Handling**

  * Reads **student lists from PDFs**.
  * Merges data into a single **Excel file**.
  * Flags **duplicate Student IDs** (highlighted in red).
* **Seating Algorithm**

  * Automatic **seat assignment**.
  * Ensures **no same-batch students sit adjacent** using a 4-color tiling method.
* **Output Generation**

  * **Seat Plan PDFs** – Per room (A4 landscape).
  * **Attendance Sheet PDFs** – Per course × batch × section (A4 portrait).
  * **Envelope PDFs**:

    * **Room-wise** – Combination details per room.
    * **Teacher-wise** – Summarized counts by teacher/course/batch/section.
  * **Summary PDF** – Room vs batch totals table (A3 landscape).
* **Customization**

  * Supports custom headers (department name, exam details, etc.).
* **State Saving**

  * Remembers your last `room_info.xlsx` path for convenience.

## Output Structure

When you run the script, an `output/` directory is created (or cleared if it exists). Inside:

```
output/
├─ SeatPlan_PDFs/        # Per-room seating plans
├─ Attendance_Sheets/    # Per course × batch × section
├─ Envelopes.pdf         # Room-wise + teacher-wise envelopes
├─ Summary.pdf           # Room vs batch totals
├─ merged_excel.xlsx     # Combined student data
└─ room_info_path.txt    # Stores last room_info.xlsx path
```

---

Would you like me to also write a **short README.md version with installation and usage instructions**?
