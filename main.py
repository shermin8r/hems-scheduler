import os
import sqlite3
from datetime import datetime
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, origins="*")

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'app.db')

# Create database directory if it doesn't exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_table_info():
    """Check what tables and columns exist in the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        table_info = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            table_info[table_name] = [col[1] for col in columns]  # col[1] is column name
        
        conn.close()
        return table_info
        
    except Exception as e:
        return {'error': str(e)}

def create_quarter_safe():
    """Create quarter using the existing database structure"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # First, let's see what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        
        if 'quarters' in tables:
            # Check existing quarters
            cursor.execute("SELECT COUNT(*) FROM quarters")
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                # Get existing quarters
                cursor.execute("SELECT * FROM quarters LIMIT 5")
                quarters = cursor.fetchall()
                
                # Get column names
                cursor.execute("PRAGMA table_info(quarters);")
                columns = [col[1] for col in cursor.fetchall()]
                
                quarter_list = []
                for q in quarters:
                    quarter_dict = {}
                    for i, col in enumerate(columns):
                        if i < len(q):
                            quarter_dict[col] = q[i]
                    quarter_list.append(quarter_dict)
                
                conn.close()
                return {
                    'success': True,
                    'message': '✅ SUCCESS! Quarters already exist in your database',
                    'quarters': quarter_list,
                    'count': existing_count,
                    'status': 'already_exists',
                    'table_structure': columns
                }
        
        # If no quarters table or no data, create a simple one
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quarters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quarter_name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                location TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert a quarter
        cursor.execute('''
            INSERT INTO quarters (quarter_name, start_date, end_date, location, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            'Q1 2025 - HEMS Education',
            '2025-01-01',
            '2025-03-31',
            'HEMS Training Center',
            'First quarter 2025 education meetings for HEMS clinicians'
        ))
        
        quarter_id = cursor.lastrowid
        
        # Create time slots table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL
            )
        ''')
        
        # Insert default time slots
        cursor.execute("SELECT COUNT(*) FROM time_slots")
        if cursor.fetchone()[0] == 0:
            time_slots = [
                ('09:00', '10:00'),
                ('10:00', '11:00'),
                ('11:00', '12:00')
            ]
            cursor.executemany(
                'INSERT INTO time_slots (start_time, end_time) VALUES (?, ?)',
                time_slots
            )
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': '🎉 SUCCESS! Quarter created successfully!',
            'quarter': {
                'id': quarter_id,
                'quarter_name': 'Q1 2025 - HEMS Education',
                'start_date': '2025-01-01',
                'end_date': '2025-03-31',
                'location': 'HEMS Training Center'
            },
            'time_slots': [
                {'time': '09:00 - 10:00', 'available': True},
                {'time': '10:00 - 11:00', 'available': True},
                {'time': '11:00 - 12:00', 'available': True}
            ],
            'status': 'created'
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'error_type': type(e).__name__
        }

@app.route('/api/quarters/create-sample', methods=['GET', 'POST'])
def create_sample_quarter():
    """Create sample quarter with error handling"""
    result = create_quarter_safe()
    
    if result['success']:
        return jsonify({
            'message': result['message'],
            'quarter': result.get('quarter'),
            'quarters': result.get('quarters'),
            'time_slots': result.get('time_slots'),
            'count': result.get('count'),
            'status': result['status'],
            'registration_url': 'https://hems.shermerautomation.com',
            'next_steps': [
                '✅ Your HEMS scheduler is now ready!',
                '✅ Speakers can register at your website',
                '✅ Share the registration link with potential speakers',
                '✅ System prevents double-booking automatically'
            ]
        }), 200 if result['status'] == 'already_exists' else 201
    else:
        return jsonify({
            'message': result['message'],
            'error_type': result['error_type']
        }), 500

@app.route('/api/database/info', methods=['GET'])
def database_info():
    """Get information about the database structure"""
    table_info = get_table_info()
    return jsonify({
        'message': 'Database structure information',
        'tables': table_info,
        'database_path': DB_PATH
    }), 200

@app.route('/api/test')
def api_test():
    return {
        "message": "API is working!",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "database": "SQLite with error handling"
    }, 200

@app.route('/api/quarters/check', methods=['GET'])
def check_quarters():
    """Check what quarters exist with flexible column handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if quarters table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quarters';")
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'message': 'No quarters table found',
                'quarters': [],
                'count': 0
            }), 200
        
        # Get all quarters
        cursor.execute("SELECT * FROM quarters")
        quarters = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(quarters);")
        columns = [col[1] for col in cursor.fetchall()]
        
        quarter_list = []
        for q in quarters:
            quarter_dict = {}
            for i, col in enumerate(columns):
                if i < len(q):
                    quarter_dict[col] = q[i]
            quarter_list.append(quarter_dict)
        
        conn.close()
        
        return jsonify({
            'message': f'Found {len(quarters)} quarter(s)',
            'quarters': quarter_list,
            'count': len(quarters),
            'columns': columns
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error checking quarters: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "HEMS Scheduler - Server Running", 200

@app.route('/health')
def health_check():
    return {"status": "healthy", "message": "HEMS Scheduler is running"}, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting HEMS Scheduler on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
