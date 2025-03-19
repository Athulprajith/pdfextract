import pdfplumber
import psycopg2
import re
import pytesseract
from pdf2image import convert_from_path

# Database connection parameters
DB_PARAMS = {
    "dbname": "student_marks",
    "user": "postgres",  # Replace with your PostgreSQL username
    "password": "1234",  # Replace with your PostgreSQL password
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

# Insert data into the database
def insert_data(conn, name, register_number, marks_dict):
    try:
        cur = conn.cursor()
        for subject, total in marks_dict.items():
            print(f"Inserting: name={name}, register_number={register_number}, subject={subject}, total={total}")
            if total is None:
                print(f"⚠️ Skipping {subject}: total is None")
                continue
            total = int(total)  # Ensure total is an integer
            # Use parameterized query with proper tuple
            cur.execute(
                "INSERT INTO marksheet (name, register_number, total_mark) VALUES (%s,  %s, %s)",
                (name, register_number, subject, total)
            )
        conn.commit()
        print(f"✅ Inserted data for: {name}, Register Number: {register_number}")
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
    finally:
        cur.close()

# Extract text from PDF using pdfplumber
def extract_text_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            print("📄 Extracted Text:\n", text)
            return text
    except Exception as e:
        print(f"❌ Error extracting from PDF: {e}")
        return None

# Extract text from scanned PDFs using OCR
def extract_text_ocr(pdf_path):
    try:
        images = convert_from_path(pdf_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        print("🖼️ OCR Extracted Text:\n", text)
        return text
    except Exception as e:
        print(f"❌ Error in OCR extraction: {e}")
        return None

# Extract name, register number, and marks from the certificate
def extract_name_and_marks(text):
    # Extract Register Number
    register_match = re.search(r"Register\s+Number\s+(\d+)", text, re.IGNORECASE)
    register_number = register_match.group(1) if register_match else "Unknown"

    # Extract Name (more flexible pattern)
    name_match = re.search(r"(?:Mr|Ms|Mr\.|Ms\.)\s*([A-Z\s.]+)", text, re.IGNORECASE)
    if not name_match:
        name_match = re.search(r"certify\s+that\s+([A-Z\s.]+)\s+appeared", text, re.IGNORECASE)
    name = name_match.group(1).strip() if name_match else "Unknown"

    # Dictionary to store subject totals
    marks_dict = {}

    # Subjects and their total score patterns
    subjects = [
        "ENGLISH", "HINDI", "PHYSICS", "CHEMISTRY", 
        "COMPUTER SCIENCE", "MATHEMATICS-SCI"
    ]
    
    for subject in subjects:
        pattern = rf"{subject}.*?(\d+)\s+[A-Z+]"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            total_score = int(match.group(1))
            marks_dict[subject] = total_score

    return name, register_number, marks_dict

# Main execution
def main():
    pdf_path = "C:/Users/ccuse/OneDrive/Desktop/Sreerag-2.pdf"  # Ensure this is correct
    conn = connect_db()

    if conn:
        text = extract_text_pdf(pdf_path) or extract_text_ocr(pdf_path)

        if text:
            name, register_number, marks_dict = extract_name_and_marks(text)
            print(f"🔹 Extracted Name: {name}")
            print(f"🔹 Extracted Register Number: {register_number}")
            print(f"🔹 Extracted Marks: {marks_dict}")

            if marks_dict:
                insert_data(conn, name, register_number, marks_dict)
            else:
                print("⚠️ No valid marks data found in PDF.")
        else:
            print("⚠️ No text extracted from PDF.")
        
        conn.close()

if __name__ == "__main__":
    main()