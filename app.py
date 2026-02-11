import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---

# DB_URL="postgresql://postgres:Adrean112233445@db.udylqxfeowvlfoqzkgcs.supabase.co:5432/postgres"

user="postgres.udylqxfeowvlfoqzkgcs"
password="Adrean112233445"
host="aws-1-eu-west-1.pooler.supabase.com"
port="6543"
dbname="postgres"

SUPABASE_URL = "https://udylqxfeowvlfoqzkgcs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVkeWxxeGZlb3d2bGZvcXprZ2NzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA4NDEzMzYsImV4cCI6MjA4NjQxNzMzNn0.UTjq0coklzsBEE-sGFa3JFqn2e3vit5B-DvjYsAXTVs"



supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_db_connection():
    return psycopg2.connect(
        user=user,
        password=password,
        host=host,
        port=port,
        dbname=dbname
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM gallery ORDER BY created_at DESC")
    gallery = cur.fetchall()
    cur.execute("SELECT * FROM pdfs ORDER BY created_at DESC")
    pdfs = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({'gallery': gallery, 'pdfs': pdfs})

@app.route('/api/upload/gallery', methods=['POST'])
def upload_gallery():
    file = request.files['file']
    title_en = request.form.get('title_en')
    title_de = request.form.get('title_de')
    desc_en = request.form.get('desc_en')
    desc_de = request.form.get('desc_de')


    
    try:
        # filename = f"gallery/{file.filename}"
        # supabase.storage.from_('media').upload(filename, file)
        # image_url = f"{SUPABASE_URL}/storage/v1/object/public/media/{filename}"
        filename = f"gallery/{file.filename}"
        file_bytes = file.read()

        supabase.storage.from_('media').upload(
            filename,
            file_bytes,
            {"content-type": file.content_type}
        )

        image_url = f"{SUPABASE_URL}/storage/v1/object/public/media/{filename}"


        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO gallery (title_en, title_de, desc_en, desc_de, image_url) VALUES (%s, %s, %s, %s, %s)",
            (title_en, title_de, desc_en, desc_de, image_url)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload/pdf', methods=['POST'])
def upload_pdf():
    file = request.files['file']
    title_en = request.form.get('title_en')
    title_de = request.form.get('title_de')
    is_protected = request.form.get('is_protected') == 'true'
    password = request.form.get('password', '')

    try:
        filename = f"pdfs/{file.filename}"
        supabase.storage.from_('media').upload(filename, file)
        file_url = f"{SUPABASE_URL}/storage/v1/object/public/media/{filename}"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO pdfs (title_en, title_de, file_name, file_url, is_protected, password) VALUES (%s, %s, %s, %s, %s, %s)",
            (title_en, title_de, file.filename, file_url, is_protected, password)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete/<string:item_type>/<int:item_id>', methods=['DELETE'])
def delete_item(item_type, item_id):
    conn = get_db_connection()
    cur = conn.cursor()
    if item_type == 'gallery':
        cur.execute("DELETE FROM gallery WHERE id = %s", (item_id,))
    elif item_type == 'pdf':
        cur.execute("DELETE FROM pdfs WHERE id = %s", (item_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
