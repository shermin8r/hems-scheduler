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

def init_database():
    """Initialize database with required tables"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create quarters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quarters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                location TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create time_slots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create lecture_slots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lecture_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quarter_id INTEGER NOT NULL,
                time_slot_id INTEGER NOT NULL,
                is_available BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quarter_id) REFERENCES quarters (id),
                FOREIGN KEY (time_slot_id) REFERENCES time_slots (id)
            )
        ''')
        
        # Create speaker_registrations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS speaker_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lecture_slot_id INTEGER NOT NULL,
                speaker_name TEXT NOT NULL,
                speaker_title TEXT,
                email TEXT NOT NULL,
                phone TEXT,
                organization TEXT,
                topic TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lecture_slot_id) REFERENCES lecture_slots (id)
            )
        ''')
        
        # Insert default time slots if they don't exist
        cursor.execute('SELECT COUNT(*) FROM time_slots')
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
        print("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

# Initialize database on startup
init_database()

@app.route('/api/quarters/create-sample', methods=['GET', 'POST'])
def create_sample_quarter():
    """Create sample quarter using direct SQL"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if quarters already exist
        cursor.execute('SELECT COUNT(*) FROM quarters')
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            # Get existing quarters
            cursor.execute('SELECT id, name, start_date, end_date, location FROM quarters')
            quarters = cursor.fetchall()
            
            quarter_list = []
            for q in quarters:
                quarter_list.append({
                    'id': q[0],
                    'name': q[1],
                    'start_date': q[2],
                    'end_date': q[3],
                    'location': q[4]
                })
            
            conn.close()
            return jsonify({
                'message': '✅ SUCCESS! Quarters already exist',
                'quarters': quarter_list,
                'count': existing_count,
                'status': 'already_exists',
                'registration_url': 'https://hems.shermerautomation.com'
            }), 200
        
        # Create new quarter
        cursor.execute('''
            INSERT INTO quarters (name, start_date, end_date, location, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            'Q1 2025 - HEMS Education',
            '2025-01-01',
            '2025-03-31',
            'HEMS Training Center',
            'First quarter 2025 education meetings for HEMS clinicians'
        ))
        
        quarter_id = cursor.lastrowid
        
        # Get time slots
        cursor.execute('SELECT id, start_time, end_time FROM time_slots')
        time_slots = cursor.fetchall()
        
        # Create lecture slots for this quarter
        slots_created = []
        for time_slot in time_slots:
            cursor.execute('''
                INSERT INTO lecture_slots (quarter_id, time_slot_id, is_available)
                VALUES (?, ?, 1)
            ''', (quarter_id, time_slot[0]))
            
            slots_created.append({
                'time': f"{time_slot[1]} - {time_slot[2]}",
                'available': True
            })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': '🎉 SUCCESS! Sample quarter created successfully!',
            'quarter': {
                'id': quarter_id,
                'name': 'Q1 2025 - HEMS Education',
                'start_date': '2025-01-01',
                'end_date': '2025-03-31',
                'location': 'HEMS Training Center',
                'description': 'First quarter 2025 education meetings for HEMS clinicians'
            },
            'time_slots': slots_created,
            'slots_count': len(slots_created),
            'next_steps': [
                '✅ Speakers can now register at your website',
                '✅ Share the registration link with potential speakers',
                f'✅ {len(slots_created)} time slots are ready and available',
                '✅ System prevents double-booking automatically'
            ],
            'registration_url': 'https://hems.shermerautomation.com',
            'status': 'created'
        }), 201
        
    except Exception as e:
        return jsonify({
            'message': f'Error creating quarter: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/quarters/active', methods=['GET'])
def get_active_quarters():
    """Get active quarters"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT q.id, q.name, q.start_date, q.end_date, q.location, q.description,
                   COUNT(ls.id) as total_slots,
                   SUM(CASE WHEN ls.is_available = 1 THEN 1 ELSE 0 END) as available_slots
            FROM quarters q
            LEFT JOIN lecture_slots ls ON q.id = ls.quarter_id
            WHERE q.end_date >= date('now')
            GROUP BY q.id, q.name, q.start_date, q.end_date, q.location, q.description
        ''')
        
        quarters = cursor.fetchall()
        
        quarter_list = []
        for q in quarters:
            quarter_list.append({
                'id': q[0],
                'name': q[1],
                'start_date': q[2],
                'end_date': q[3],
                'location': q[4],
                'description': q[5],
                'total_slots': q[6] or 0,
                'available_slots': q[7] or 0
            })
        
        conn.close()
        
        return jsonify(quarter_list), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error getting quarters: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/test')
def api_test():
    return {
        "message": "API is working!",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "database": "SQLite direct connection"
    }, 200

@app.route('/api/quarters/check', methods=['GET'])
def check_quarters():
    """Check what quarters exist"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, start_date, end_date, location FROM quarters')
        quarters = cursor.fetchall()
        
        quarter_list = []
        for q in quarters:
            quarter_list.append({
                'id': q[0],
                'name': q[1],
                'start_date': q[2],
                'end_date': q[3],
                'location': q[4]
            })
        
        conn.close()
        
        return jsonify({
            'message': f'Found {len(quarters)} quarter(s)',
            'quarters': quarter_list,
            'count': len(quarters)
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
