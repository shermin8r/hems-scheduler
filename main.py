import os
import sqlite3
from datetime import datetime
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, origins="*")

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'app.db')

def ensure_database_and_data():
    """Ensure database exists with proper structure and 2026 MCES data"""
    try:
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create quarters table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quarters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                quarter_number INTEGER NOT NULL,
                meeting_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Create time_slots table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                slot_name TEXT
            )
        ''')
        
        # Create lecture_slots table if it doesn't exist
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
        
        # Create speaker_registrations table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS speaker_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lecture_slot_id INTEGER NOT NULL,
                speaker_name TEXT NOT NULL,
                speaker_email TEXT NOT NULL,
                speaker_phone TEXT,
                specialty TEXT,
                topic_title TEXT NOT NULL,
                topic_description TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'confirmed',
                FOREIGN KEY (lecture_slot_id) REFERENCES lecture_slots (id)
            )
        ''')
        
        # Check if we have any active quarters for 2026
        cursor.execute('SELECT COUNT(*) FROM quarters WHERE year = 2026 AND is_active = 1')
        quarter_count = cursor.fetchone()[0]
        
        if quarter_count == 0:
            # Create 2026 MCES quarters (February, May, August, November)
            # Using placeholder dates - user will update these later
            quarters_2026 = [
                (2026, 1, '2026-02-15'),  # February meeting
                (2026, 2, '2026-05-15'),  # May meeting  
                (2026, 3, '2026-08-15'),  # August meeting
                (2026, 4, '2026-11-15'),  # November meeting
            ]
            
            for year, quarter_num, meeting_date in quarters_2026:
                cursor.execute('''
                    INSERT INTO quarters (year, quarter_number, meeting_date, is_active)
                    VALUES (?, ?, ?, ?)
                ''', (year, quarter_num, meeting_date, 1))
                
                quarter_id = cursor.lastrowid
                
                # Create lecture slots for this quarter
                cursor.execute('SELECT id FROM time_slots')
                time_slot_ids = [row[0] for row in cursor.fetchall()]
                
                for time_slot_id in time_slot_ids:
                    cursor.execute('''
                        INSERT INTO lecture_slots (quarter_id, time_slot_id, is_available)
                        VALUES (?, ?, ?)
                    ''', (quarter_id, time_slot_id, 1))
        
        # Ensure we have the standard time slots with clean formatting
        cursor.execute('SELECT COUNT(*) FROM time_slots')
        slot_count = cursor.fetchone()[0]
        
        if slot_count == 0:
            # Insert clean time slots
            time_slots = [
                ('09:00', '10:00', 'Morning Session'),
                ('10:00', '11:00', 'Mid-Morning Session'),
                ('11:00', '12:00', 'Late Morning Session')
            ]
            
            cursor.executemany('''
                INSERT INTO time_slots (start_time, end_time, slot_name)
                VALUES (?, ?, ?)
            ''', time_slots)
        else:
            # Update existing time slots to clean format if needed
            cursor.execute('''
                UPDATE time_slots 
                SET start_time = CASE 
                    WHEN start_time LIKE '%09:00%' THEN '09:00'
                    WHEN start_time LIKE '%10:00%' THEN '10:00'
                    WHEN start_time LIKE '%11:00%' THEN '11:00'
                    ELSE start_time
                END,
                end_time = CASE 
                    WHEN end_time LIKE '%10:00%' THEN '10:00'
                    WHEN end_time LIKE '%11:00%' THEN '11:00'
                    WHEN end_time LIKE '%12:00%' THEN '12:00'
                    ELSE end_time
                END,
                slot_name = CASE 
                    WHEN slot_name LIKE '%Morning Session%' AND start_time LIKE '%09:00%' THEN 'Morning Session'
                    WHEN slot_name LIKE '%Mid-Morning%' OR (start_time LIKE '%10:00%' AND slot_name LIKE '%Morning%') THEN 'Mid-Morning Session'
                    WHEN slot_name LIKE '%Late Morning%' OR (start_time LIKE '%11:00%' AND slot_name LIKE '%Morning%') THEN 'Late Morning Session'
                    ELSE slot_name
                END
            ''')
        
        conn.commit()
        conn.close()
        
        print("✅ Database initialized successfully with 2026 MCES quarters")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

# Initialize database on startup
ensure_database_and_data()

# Logging middleware to see what the frontend is requesting
@app.before_request
def log_request_info():
    if request.path.startswith('/api/'):
        print(f"API Request: {request.method} {request.path}")

def get_quarters_data():
    """Common function to get quarters data with MCES branding"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT q.id, q.year, q.quarter_number, q.meeting_date, q.is_active,
                   COUNT(ls.id) as total_slots,
                   SUM(CASE WHEN ls.is_available = 1 THEN 1 ELSE 0 END) as available_slots
            FROM quarters q
            LEFT JOIN lecture_slots ls ON q.id = ls.quarter_id
            WHERE q.is_active = 1
            GROUP BY q.id, q.year, q.quarter_number, q.meeting_date, q.is_active
            ORDER BY q.year DESC, q.quarter_number ASC
        ''')
        
        quarters = cursor.fetchall()
        
        # Map quarter numbers to months for 2026 schedule
        quarter_months = {
            1: 'February',
            2: 'May', 
            3: 'August',
            4: 'November'
        }
        
        quarter_list = []
        for q in quarters:
            month_name = quarter_months.get(q[2], f'Q{q[2]}')
            quarter_name = f"{month_name} {q[1]} - MCES Education"
            
            quarter_list.append({
                'id': q[0],
                'year': q[1],
                'quarter_number': q[2],
                'meeting_date': q[3],
                'is_active': bool(q[4]),
                'name': quarter_name,
                'total_slots': q[5] or 0,
                'available_slots': q[6] or 0
            })
        
        conn.close()
        return quarter_list
        
    except Exception as e:
        print(f"Error getting quarters: {e}")
        return []

# ALL POSSIBLE ENDPOINTS THE FRONTEND MIGHT CALL

@app.route('/api/quarters', methods=['GET'])
def get_all_quarters():
    """Get all quarters - main endpoint"""
    quarters = get_quarters_data()
    print(f"Returning {len(quarters)} quarters from /api/quarters")
    return jsonify(quarters), 200

@app.route('/api/quarters/active', methods=['GET'])
def get_active_quarters():
    """Get active quarters - alternative endpoint"""
    quarters = get_quarters_data()
    print(f"Returning {len(quarters)} quarters from /api/quarters/active")
    return jsonify(quarters), 200

@app.route('/api/quarter', methods=['GET'])
def get_quarter_singular():
    """Get quarters - singular form endpoint"""
    quarters = get_quarters_data()
    print(f"Returning {len(quarters)} quarters from /api/quarter")
    return jsonify(quarters), 200

@app.route('/api/meetings', methods=['GET'])
def get_meetings():
    """Get meetings - alternative name"""
    quarters = get_quarters_data()
    print(f"Returning {len(quarters)} quarters from /api/meetings")
    return jsonify(quarters), 200

@app.route('/api/meetings/active', methods=['GET'])
def get_active_meetings():
    """Get active meetings - alternative name"""
    quarters = get_quarters_data()
    print(f"Returning {len(quarters)} quarters from /api/meetings/active")
    return jsonify(quarters), 200

@app.route('/api/quarterly-meetings', methods=['GET'])
def get_quarterly_meetings():
    """Get quarterly meetings - full name"""
    quarters = get_quarters_data()
    print(f"Returning {len(quarters)} quarters from /api/quarterly-meetings")
    return jsonify(quarters), 200

@app.route('/api/quarterly-meetings/active', methods=['GET'])
def get_active_quarterly_meetings():
    """Get active quarterly meetings - full name"""
    quarters = get_quarters_data()
    print(f"Returning {len(quarters)} quarters from /api/quarterly-meetings/active")
    return jsonify(quarters), 200

@app.route('/api/quarters/<int:quarter_id>/slots', methods=['GET'])
def get_quarter_slots(quarter_id):
    """Get available slots for a specific quarter with clean time formatting"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ls.id, ls.is_available, ts.start_time, ts.end_time, ts.slot_name
            FROM lecture_slots ls
            JOIN time_slots ts ON ls.time_slot_id = ts.id
            WHERE ls.quarter_id = ?
            ORDER BY ts.start_time
        ''', (quarter_id,))
        
        slots = cursor.fetchall()
        
        slot_list = []
        for slot in slots:
            # Clean time formatting - ensure HH:MM format
            start_time = slot[2]
            end_time = slot[3]
            
            # Format times to HH:MM if they have extra precision
            if ':' in start_time:
                start_time = ':'.join(start_time.split(':')[:2])
            if ':' in end_time:
                end_time = ':'.join(end_time.split(':')[:2])
            
            slot_list.append({
                'lecture_slot_id': slot[0],
                'is_available': bool(slot[1]),
                'start_time': start_time,
                'end_time': end_time,
                'slot_name': slot[4],
                'time_display': f"{start_time} - {end_time}"
            })
        
        conn.close()
        print(f"Returning {len(slot_list)} slots for quarter {quarter_id}")
        return jsonify(slot_list), 200
        
    except Exception as e:
        print(f"Error getting slots for quarter {quarter_id}: {e}")
        return jsonify({
            'message': f'Error getting slots: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/registrations', methods=['POST'])
def create_registration():
    """Handle speaker registration"""
    try:
        data = request.get_json()
        print(f"Registration attempt: {data}")
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the slot is still available
        cursor.execute('''
            SELECT is_available FROM lecture_slots WHERE id = ?
        ''', (data.get('lecture_slot_id'),))
        
        slot = cursor.fetchone()
        if not slot or not slot[0]:
            conn.close()
            return jsonify({'message': 'Selected time slot is no longer available'}), 400
        
        # Create the registration
        cursor.execute('''
            INSERT INTO speaker_registrations 
            (lecture_slot_id, speaker_name, speaker_email, speaker_phone, specialty, topic_title, topic_description, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('lecture_slot_id'),
            data.get('speaker_name'),
            data.get('speaker_email'),
            data.get('speaker_phone'),
            data.get('specialty'),
            data.get('topic_title'),
            data.get('topic_description'),
            'confirmed'
        ))
        
        # Mark the slot as unavailable
        cursor.execute('''
            UPDATE lecture_slots SET is_available = 0 WHERE id = ?
        ''', (data.get('lecture_slot_id'),))
        
        conn.commit()
        conn.close()
        
        print(f"Registration successful for {data.get('speaker_name')}")
        return jsonify({
            'message': 'Registration successful!',
            'status': 'confirmed'
        }), 201
        
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({
            'message': f'Error creating registration: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/quarters/create-2026', methods=['GET', 'POST'])
def create_2026_quarters():
    """Create 2026 MCES quarters with proper schedule"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Delete existing 2026 quarters
        cursor.execute('DELETE FROM lecture_slots WHERE quarter_id IN (SELECT id FROM quarters WHERE year = 2026)')
        cursor.execute('DELETE FROM quarters WHERE year = 2026')
        
        # Create 2026 MCES quarters
        quarters_2026 = [
            (2026, 1, '2026-02-15', 'February'),  # February meeting
            (2026, 2, '2026-05-15', 'May'),      # May meeting  
            (2026, 3, '2026-08-15', 'August'),   # August meeting
            (2026, 4, '2026-11-15', 'November'), # November meeting
        ]
        
        created_quarters = []
        
        for year, quarter_num, meeting_date, month_name in quarters_2026:
            cursor.execute('''
                INSERT INTO quarters (year, quarter_number, meeting_date, is_active)
                VALUES (?, ?, ?, ?)
            ''', (year, quarter_num, meeting_date, 1))
            
            quarter_id = cursor.lastrowid
            
            # Get time slot IDs
            cursor.execute('SELECT id FROM time_slots')
            time_slot_ids = [row[0] for row in cursor.fetchall()]
            
            # Create lecture slots for this quarter
            for time_slot_id in time_slot_ids:
                cursor.execute('''
                    INSERT INTO lecture_slots (quarter_id, time_slot_id, is_available)
                    VALUES (?, ?, ?)
                ''', (quarter_id, time_slot_id, 1))
            
            created_quarters.append({
                'id': quarter_id,
                'name': f"{month_name} {year} - MCES Education",
                'meeting_date': meeting_date,
                'slots_created': len(time_slot_ids)
            })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': '🎉 SUCCESS! 2026 MCES quarters created!',
            'quarters': created_quarters,
            'count': len(created_quarters),
            'schedule': 'February, May, August, November 2026'
        }), 201
        
    except Exception as e:
        return jsonify({
            'message': f'Error creating 2026 quarters: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/test')
def api_test():
    return {
        "message": "MCES Quarterly Education Series API is working!",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "database_path": DB_PATH,
        "database_exists": os.path.exists(DB_PATH)
    }, 200

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
            return "MCES Quarterly Education Series Scheduler - Server Running", 200

@app.route('/health')
def health_check():
    return {"status": "healthy", "message": "MCES Quarterly Education Series Scheduler is running"}, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting MCES Quarterly Education Series Scheduler on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
