import re
import psycopg2
from pdf2image import convert_from_path
import pytesseract
import pdfplumber

# Database connection parameters
DB_PARAMS = {
    "dbname": "student_marks",
    "user": "postgres",
    "password": "1234",
    "host": "localhost",
    "port": "5432"
}

# Connect to PostgreSQL
def connect_db():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        print("✅ Successfully connected to the database!")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return None

# Create the required tables if they don't exist
def create_tables(conn):
    try:
        cur = conn.cursor()
        # Create student_details table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS student_details (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                roll_no VARCHAR(20) NOT NULL,
                mother_name VARCHAR(100),
                father_guardian_name VARCHAR(100),
                school_name VARCHAR(200)
            );
        """)
        # Create student_subjects table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS student_subjects (
                id SERIAL PRIMARY KEY,
                student_id INTEGER REFERENCES student_details(id),
                subject_code VARCHAR(10),
                subject_name VARCHAR(100),
                theory_marks INTEGER,
                practical_marks INTEGER,
                total_marks INTEGER,
                total_in_words VARCHAR(50),
                positional_grade VARCHAR(10)
            );
        """)
        conn.commit()
        print("✅ Tables created successfully (if they didn't exist)!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
    finally:
        cur.close()

# Insert student details into student_details table and return the student_id
def insert_student_details(conn, name, roll_no, mother_name, father_guardian_name, school_name):
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO student_details (name, roll_no, mother_name, father_guardian_name, school_name)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (name, roll_no, mother_name, father_guardian_name, school_name))
        
        student_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ Successfully inserted student details for: {name}, Roll Number: {roll_no}")
        return student_id
    except Exception as e:
        print(f"❌ Error inserting student details: {e}")
        return None
    finally:
        cur.close()

# Insert subject data into student_subjects table
def insert_subject_data(conn, student_id, subjects_data):
    try:
        cur = conn.cursor()
        for subject in subjects_data:
            subject_code = subject["subject_code"]
            subject_name = subject["subject_name"]
            theory_marks = subject["theory_marks"]
            practical_marks = subject["practical_marks"]
            total_marks = subject["total_marks"]
            total_in_words = subject["total_in_words"]
            positional_grade = subject["positional_grade"]

            print(f"Inserting subject: student_id={student_id}, subject_code={subject_code}, subject_name={subject_name}, total_marks={total_marks}")

            cur.execute("""
                INSERT INTO student_subjects (student_id, subject_code, subject_name, theory_marks, practical_marks, 
                                             total_marks, total_in_words, positional_grade)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (student_id, subject_code, subject_name, theory_marks, practical_marks, 
                  total_marks, total_in_words, positional_grade))

        conn.commit()
        print(f"✅ Successfully inserted subject data for student_id: {student_id}")
    except Exception as e:
        print(f"❌ Error inserting subject data: {e}")
    finally:
        cur.close()

# Extract name, roll number, and subject data from the PDF
def extract_details(text):
    # Extract student details
    name = re.search(r"Name of Candidate\s*([\w\s]+)", text)
    roll_no = re.search(r"Roll No.\s*(\d+)", text)
    mother_name = re.search(r"Mother's Name\s*([\w\s]+)", text)
    father_guardian_name = re.search(r"Father's/Guardian's Name\s*([\w\s]+)", text)
    school_name = re.search(r"School\s*([\w\s]+)", text)

    name = name.group(1).strip() if name else "Unknown"
    roll_no = roll_no.group(1).strip() if roll_no else "Unknown"
    mother_name = mother_name.group(1).strip() if mother_name else "Unknown"
    father_guardian_name = father_guardian_name.group(1).strip() if father_guardian_name else "Unknown"
    school_name = school_name.group(1).strip() if school_name else "Unknown"

    subjects_data = []

    # Extract subjects and marks
    subject_pattern = r"(\d{3})\s+([A-Za-z\s\(\)]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z1-9]+)"
    matches = re.findall(subject_pattern, text)

    for match in matches:
        subject_name = match[1].strip().upper()  # Convert to uppercase for consistent comparison
        # Skip subjects like Hindi
        if "HINDI" in subject_name:
            continue

        subject_code = match[0]
        theory_marks = int(match[2]) if match[2].isdigit() else 0
        practical_marks = int(match[3]) if match[3].isdigit() else 0
        total_marks = int(match[4]) if match[4].isdigit() else 0
        total_in_words = match[5].strip()
        positional_grade = match[6].strip()

        subjects_data.append({
            "subject_code": subject_code,
            "subject_name": subject_name,
            "theory_marks": theory_marks,
            "practical_marks": practical_marks,
            "total_marks": total_marks,
            "total_in_words": total_in_words,
            "positional_grade": positional_grade
        })

    return name, roll_no, mother_name, father_guardian_name, school_name, subjects_data

# Main execution function
def main():
    pdf_path = "C:/Users/ccuse/OneDrive/Desktop/athulplustwo.pdf"  # Ensure this path is correct
    conn = connect_db()

    if conn:
        # Create tables if they don't exist
        create_tables(conn)

        # Extract text from the PDF
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        if text:
            name, roll_no, mother_name, father_guardian_name, school_name, subjects_data = extract_details(text)
            print(f"🔹 Extracted Name: {name}")
            print(f"🔹 Extracted Roll No: {roll_no}")
            print(f"🔹 Extracted Mother Name: {mother_name}")
            print(f"🔹 Extracted Father/Guardian Name: {father_guardian_name}")
            print(f"🔹 Extracted School Name: {school_name}")
            print(f"🔹 Extracted Subjects Data: {subjects_data}")

            # Insert student details and get the student_id
            student_id = insert_student_details(conn, name, roll_no, mother_name, father_guardian_name, school_name)
            
            if student_id and subjects_data:
                # Insert subject data linked to the student_id
                insert_subject_data(conn, student_id, subjects_data)
            else:
                print("❌ No subjects data to insert or failed to insert student details!")
        else:
            print("❌ No text extracted from the PDF!")

        conn.close()

if __name__ == "__main__":
    main()