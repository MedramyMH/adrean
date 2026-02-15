import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
# Use environment variables for security. 
# The values below are your current ones, but it's better to move them to a .env file.

DB_USER = os.getenv("DB_USER", "postgres.udylqxfeowvlfoqzkgcs")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Medramy260690")
DB_HOST = os.getenv("DB_HOST", "aws-1-eu-west-1.pooler.supabase.com")
DB_PORT = os.getenv("DB_PORT", "6543")
DB_NAME = os.getenv("DB_NAME", "postgres")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://udylqxfeowvlfoqzkgcs.supabase.co")
# Ensure this is the 'anon' or 'service_role' key from your Supabase Dashboard
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVkeWxxeGZlb3d2bGZvcXprZ2NzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA4NDEzMzYsImV4cCI6MjA4NjQxNzMzNn0.UTjq0coklzsBEE-sGFa3JFqn2e3vit5B-DvjYsAXTVs")

# Initialize Supabase Client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    return psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    """Fetches all gallery items and PDFs from the database."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM gallery ORDER BY created_at DESC")
        gallery = cur.fetchall()
        
        cur.execute("SELECT * FROM pdfs ORDER BY created_at DESC")
        pdfs = cur.fetchall()
        
        cur.close()
        return jsonify({'gallery': gallery, 'pdfs': pdfs})
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Failed to fetch data'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/upload/gallery', methods=['POST'])
def upload_gallery():
    """Handles image upload to Supabase Storage and saves metadata to DB."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    title_en = request.form.get('title_en', '')
    title_de = request.form.get('title_de', '')
    desc_en = request.form.get('desc_en', '')
    desc_de = request.form.get('desc_de', '')

    try:
        # 1. Upload to Supabase Storage
        # Ensure the bucket 'media' exists and has 'Public' access enabled in Supabase Dashboard
        filename = f"gallery/{file.filename}"
        file_content = file.read()
        
        # Using x-upsert: true to allow overwriting files with the same name
        storage_response = supabase.storage.from_('media').upload(
            path=filename,
            file=file_content,
            file_options={"content-type": file.content_type, "x-upsert": "true"}
        )
        
        # 2. Generate Public URL
        image_url = f"{SUPABASE_URL}/storage/v1/object/public/media/{filename}"

        # 3. Save to Database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO gallery (title_en, title_de, desc_en, desc_de, image_url) VALUES (%s, %s, %s, %s, %s)",
            (title_en, title_de, desc_en, desc_de, image_url)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'url': image_url})
    except Exception as e:
        # If you see 'signature verification failed', your SUPABASE_KEY is likely incorrect.
        # If you see 'new row violates row-level security policy', you need to add Storage Policies.
        print(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload/pdf', methods=['POST'])
def upload_pdf():
    """Handles PDF upload to Supabase Storage and saves metadata to DB."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    title_en = request.form.get('title_en', '')
    title_de = request.form.get('title_de', '')
    is_protected = request.form.get('is_protected') == 'true'
    password = request.form.get('password', '')

    try:
        # 1. Upload to Supabase Storage
        filename = f"pdfs/{file.filename}"
        file_content = file.read()
        
        supabase.storage.from_('media').upload(
            path=filename,
            file=file_content,
            file_options={"content-type": "application/pdf", "x-upsert": "true"}
        )
        
        # 2. Generate Public URL
        file_url = f"{SUPABASE_URL}/storage/v1/object/public/media/{filename}"

        # 3. Save to Database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO pdfs (title_en, title_de, file_name, file_url, is_protected, password) VALUES (%s, %s, %s, %s, %s, %s)",
            (title_en, title_de, file.filename, file_url, is_protected, password)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'url': file_url})
    except Exception as e:
        print(f"PDF Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete/<string:item_type>/<int:item_id>', methods=['DELETE'])
def delete_item(item_type, item_id):
    """Deletes an item from the database."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if item_type == 'gallery':
            cur.execute("DELETE FROM gallery WHERE id = %s", (item_id,))
        elif item_type == 'pdf':
            cur.execute("DELETE FROM pdfs WHERE id = %s", (item_id,))
        else:
            return jsonify({'error': 'Invalid item type'}), 400
            
        conn.commit()
        cur.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Delete error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
