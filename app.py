import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE = 'snippets.db'

def get_db_conn():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snippets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, language TEXT NOT NULL,
            description TEXT NOT NULL, code TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    if conn.execute("SELECT COUNT(id) FROM snippets").fetchone()[0] == 0:
        dummy_data = [
            ('Python Flask API', 'Python', 'A minimal Flask API.', 'from flask import Flask\napp = Flask(__name__)\n\n@app.route("/")\ndef hello():\n    return "Hello!"'),
            ('CSS Flexbox Center', 'CSS', 'Center a div with Flexbox.', '.parent{\n display: flex;\n justify-content: center;\n align-items: center;\n}')
        ]
        conn.executemany('INSERT INTO snippets (title, language, description, code) VALUES (?, ?, ?, ?)', dummy_data)
        print("Dummy data added.")
    conn.commit()
    conn.close()

# === PUBLIC API (FOR USERS) ===
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
        conditions.append('language = ?')
        params.append(lang_filter)
    
    if search_query:
        conditions.append('title LIKE ?')
        params.append(f'%{search_query}%')

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    
    query += ' ORDER BY created_at DESC'
    
    rows = cursor.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/snippets/<int:snippet_id>', methods=['GET'])
def get_snippet_by_id(snippet_id):
    conn = get_db_conn()
    row = conn.execute('SELECT * FROM snippets WHERE id = ?', (snippet_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Snippet not found"}), 404
    return jsonify(dict(row))

# === ADMIN API ===
@app.route('/api/admin/add_snippet', methods=['POST'])
def add_snippet():
    data = request.form
    if not all([data.get('title'), data.get('language'), data.get('description'), data.get('code')]):
        return jsonify({"error": "All fields are required"}), 400
    conn = get_db_conn()
    conn.execute('INSERT INTO snippets (title, language, description, code) VALUES (?, ?, ?, ?)',
                   (data['title'], data['language'], data['description'], data['code']))
    conn.commit()
    conn.close()
    return jsonify({"success": "Snippet added successfully!"}), 201

@app.route('/api/admin/snippets/<int:snippet_id>', methods=['PUT'])
def update_snippet(snippet_id):
    data = request.form
    if not all([data.get('title'), data.get('language'), data.get('description'), data.get('code')]):
        return jsonify({"error": "All fields are required"}), 400
    conn = get_db_conn()
    conn.execute('UPDATE snippets SET title=?, language=?, description=?, code=? WHERE id=?',
                   (data['title'], data['language'], data['description'], data['code'], snippet_id))
    conn.commit()
    conn.close()
    return jsonify({"success": "Snippet updated successfully!"})

@app.route('/api/admin/snippets/<int:snippet_id>', methods=['DELETE'])
def delete_snippet(snippet_id):
    conn = get_db_conn()
    conn.execute('DELETE FROM snippets WHERE id = ?', (snippet_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": "Snippet deleted successfully!"})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
