import os
import psycopg2 # Naya database translator
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Database URL ko Render ke Environment Variable se lena
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_conn():
    # Ab hum SQLite ki jagah PostgreSQL se connect honge
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db_conn()
    cursor = conn.cursor()
    # PostgreSQL ke liye table creation code
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snippets (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            language TEXT NOT NULL,
            description TEXT NOT NULL,
            code TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("SELECT COUNT(id) FROM snippets")
    count = cursor.fetchone()[0]
    
    if count == 0:
        dummy_data = [
            ('Python Flask API', 'Python', 'A minimal Flask API.', 'from flask import Flask\napp = Flask(__name__)\n\n@app.route("/")\ndef hello():\n    return "Hello!"'),
            ('CSS Flexbox Center', 'CSS', 'Center a div with Flexbox.', '.parent{\n display: flex;\n justify-content: center;\n align-items: center;\n}')
        ]
        # PostgreSQL ke liye parameter style %s hota hai
        cursor.executemany('INSERT INTO snippets (title, language, description, code) VALUES (%s, %s, %s, %s)', dummy_data)
        print("Dummy data added.")
    
    conn.commit()
    cursor.close()
    conn.close()

# Helper function to convert DB rows to dictionaries
def row_to_dict(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# app.py mein yeh naya function add karein
# app.py mein add karein

# HEALTH CHECK ROUTE: UptimeRobot jaise services ke liye
@app.route('/')
def health_check():
    return "OK", 200
    
# SECRET ENDPOINT: Sirf ek baar database initialize karne ke liye
@app.route('/create-tables-on-render-once')
def create_tables():
    try:
        init_db()
        return "Database tables created successfully!"
    except Exception as e:
        return f"An error occurred: {e}"
        

# === PUBLIC API ===
@app.route('/api/snippets', methods=['GET'])
def get_all_snippets():
    lang_filter = request.args.get('lang')
    search_query = request.args.get('q')
    conn = get_db_conn()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM snippets'
    params = []
    conditions = []

    if lang_filter and lang_filter != 'All':
        conditions.append('language = %s')
        params.append(lang_filter)
    
    if search_query:
        conditions.append('title ILIKE %s') # ILIKE case-insensitive search ke liye
        params.append(f'%{search_query}%')

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    
    query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    snippets_list = [row_to_dict(cursor, row) for row in rows]
    cursor.close()
    conn.close()
    return jsonify(snippets_list)

@app.route('/api/snippets/<int:snippet_id>', methods=['GET'])
def get_snippet_by_id(snippet_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM snippets WHERE id = %s', (snippet_id,))
    row = cursor.fetchone()
    snippet_dict = row_to_dict(cursor, row) if row else None
    cursor.close()
    conn.close()
    if snippet_dict is None:
        return jsonify({"error": "Snippet not found"}), 404
    return jsonify(snippet_dict)

# === ADMIN API (Sab kuch same hai, bas ? ki jagah %s) ===
@app.route('/api/admin/add_snippet', methods=['POST'])
def add_snippet():
    data = request.form
    if not all([data.get('title'), data.get('language'), data.get('description'), data.get('code')]):
        return jsonify({"error": "All fields are required"}), 400
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO snippets (title, language, description, code) VALUES (%s, %s, %s, %s)',
                   (data['title'], data['language'], data['description'], data['code']))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": "Snippet added successfully!"}), 201

@app.route('/api/admin/snippets/<int:snippet_id>', methods=['PUT'])
def update_snippet(snippet_id):
    data = request.form
    # ... validation ...
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('UPDATE snippets SET title=%s, language=%s, description=%s, code=%s WHERE id=%s',
                   (data['title'], data['language'], data['description'], data['code'], snippet_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": "Snippet updated successfully!"})

@app.route('/api/admin/snippets/<int:snippet_id>', methods=['DELETE'])
def delete_snippet(snippet_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM snippets WHERE id = %s', (snippet_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": "Snippet deleted successfully!"})

if __name__ == '__main__':
    # init_db() # Yeh command ab hum Render par alag se chala sakte hain, ya first deploy par
    app.run(debug=True)
    
