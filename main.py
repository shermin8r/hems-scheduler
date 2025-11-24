import os
import sqlite3
from datetime import datetime
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'mces-scheduler-2024'

# Enable CORS for all routes
CORS(app, origins="*")

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'app.db')

def ensure_database_and_data():
    """Ensure database exists with proper structure and 2026 MCES quarters"""
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
        
        # Create admin_users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Ensure we have the standard time slots with clean formatting
        cursor.execute('SELECT COUNT(*) FROM time_slots')
        slot_count = cursor.fetchone()[0]
        
        if slot_count == 0:
            # Insert clean time slots
            time_slots = [
                ('09:00', '10:00', 'Morning Session (09:00-10:00)'),
                ('10:00', '11:00', 'Mid-Morning Session (10:00-11:00)'),
                ('11:00', '12:00', 'Late Morning Session (11:00-12:00)')
            ]
            
            cursor.executemany('''
                INSERT INTO time_slots (start_time, end_time, slot_name)
                VALUES (?, ?, ?)
            ''', time_slots)
            
            print("✅ Time slots created")
        
        # Auto-create 2026 quarters if they don't exist
        cursor.execute('SELECT COUNT(*) FROM quarters WHERE year = 2026')
        quarters_exist = cursor.fetchone()[0] > 0
        
        if not quarters_exist:
            # Create 2026 quarters automatically
            quarters_data = [
                (2026, 1, '2026-02-15'),  # February
                (2026, 2, '2026-05-15'),  # May
                (2026, 3, '2026-08-15'),  # August
                (2026, 4, '2026-11-15')   # November
            ]
            
            for year, quarter_num, meeting_date in quarters_data:
                # Insert quarter
                cursor.execute('''
                    INSERT INTO quarters (year, quarter_number, meeting_date, is_active)
                    VALUES (?, ?, ?, 1)
                ''', (year, quarter_num, meeting_date))
                
                quarter_id = cursor.lastrowid
                
                # Get time slots
                cursor.execute('SELECT id FROM time_slots ORDER BY start_time')
                time_slots = cursor.fetchall()
                
                # Create lecture slots for this quarter
                for time_slot in time_slots:
                    cursor.execute('''
                        INSERT INTO lecture_slots (quarter_id, time_slot_id, is_available)
                        VALUES (?, ?, 1)
                    ''', (quarter_id, time_slot[0]))
            
            print("✅ 2026 MCES quarters auto-created")
        
        # Create admin user if it doesn't exist
        cursor.execute('SELECT COUNT(*) FROM admin_users WHERE username = ?', ('admin',))
        admin_exists = cursor.fetchone()[0] > 0
        
        if not admin_exists:
            cursor.execute('''
                INSERT INTO admin_users (username, password_hash, email)
                VALUES (?, ?, ?)
            ''', ('admin', 'admin123', 'admin@mces.edu'))
            print("✅ Admin user created")
        
        conn.commit()
        conn.close()
        
        print("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

# Initialize database on startup
ensure_database_and_data()

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

# API ENDPOINTS

@app.route('/api/quarters', methods=['GET'])
def get_all_quarters():
    """Get all active quarters"""
    quarters = get_quarters_data()
    return jsonify(quarters), 200

@app.route('/api/quarters/active', methods=['GET'])
def get_active_quarters():
    """Get active quarters"""
    quarters = get_quarters_data()
    return jsonify(quarters), 200

@app.route('/api/quarters/create-2026', methods=['GET'])
def create_2026_quarters():
    """Force create 2026 quarters"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Delete existing 2026 quarters
        cursor.execute('DELETE FROM speaker_registrations WHERE lecture_slot_id IN (SELECT id FROM lecture_slots WHERE quarter_id IN (SELECT id FROM quarters WHERE year = 2026))')
        cursor.execute('DELETE FROM lecture_slots WHERE quarter_id IN (SELECT id FROM quarters WHERE year = 2026)')
        cursor.execute('DELETE FROM quarters WHERE year = 2026')
        
        # Create 2026 quarters
        quarters_data = [
            (2026, 1, '2026-02-15'),  # February
            (2026, 2, '2026-05-15'),  # May
            (2026, 3, '2026-08-15'),  # August
            (2026, 4, '2026-11-15')   # November
        ]
        
        created_quarters = []
        
        for year, quarter_num, meeting_date in quarters_data:
            # Insert quarter
            cursor.execute('''
                INSERT INTO quarters (year, quarter_number, meeting_date, is_active)
                VALUES (?, ?, ?, 1)
            ''', (year, quarter_num, meeting_date))
            
            quarter_id = cursor.lastrowid
            
            # Get time slots
            cursor.execute('SELECT id FROM time_slots ORDER BY start_time')
            time_slots = cursor.fetchall()
            
            slots_created = 0
            # Create lecture slots for this quarter
            for time_slot in time_slots:
                cursor.execute('''
                    INSERT INTO lecture_slots (quarter_id, time_slot_id, is_available)
                    VALUES (?, ?, 1)
                ''', (quarter_id, time_slot[0]))
                slots_created += 1
            
            # Map quarter number to month name
            quarter_months = {1: 'February', 2: 'May', 3: 'August', 4: 'November'}
            month_name = quarter_months.get(quarter_num, f'Q{quarter_num}')
            quarter_name = f"{month_name} {year} - MCES Education"
            
            created_quarters.append({
                'id': quarter_id,
                'name': quarter_name,
                'meeting_date': meeting_date,
                'slots_created': slots_created
            })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': '🎉 SUCCESS! 2026 MCES quarters created!',
            'count': len(created_quarters),
            'quarters': created_quarters,
            'schedule': 'February, May, August, November 2026'
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error creating 2026 quarters: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/quarters/<int:quarter_id>/slots', methods=['GET'])
def get_quarter_slots(quarter_id):
    """Get available slots for a specific quarter with registration info"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                ls.id, 
                ls.is_available, 
                ts.start_time, 
                ts.end_time, 
                ts.slot_name,
                sr.speaker_name,
                sr.topic_title
            FROM lecture_slots ls
            JOIN time_slots ts ON ls.time_slot_id = ts.id
            LEFT JOIN speaker_registrations sr ON ls.id = sr.lecture_slot_id
            WHERE ls.quarter_id = ?
            ORDER BY ts.start_time
        ''', (quarter_id,))
        
        slots = cursor.fetchall()
        
        slot_list = []
        for slot in slots:
            # Clean time formatting
            start_time = slot[2]
            end_time = slot[3]
            if ':' in start_time:
                start_time = ':'.join(start_time.split(':')[:2])
            if ':' in end_time:
                end_time = ':'.join(end_time.split(':')[:2])
            
            slot_info = {
                'lecture_slot_id': slot[0],
                'is_available': bool(slot[1]),
                'start_time': start_time,
                'end_time': end_time,
                'slot_name': slot[4],
                'time_display': f"{start_time} - {end_time}"
            }
            
            # Add speaker info if slot is taken
            if not slot[1] and slot[5]:  # not available and has speaker
                slot_info['speaker_name'] = slot[5]
                slot_info['topic_title'] = slot[6]
                slot_info['status'] = 'booked'
            
            slot_list.append(slot_info)
        
        conn.close()
        return jsonify(slot_list), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error getting slots: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/registrations', methods=['POST'])
def create_registration():
    """Handle speaker registration with notification"""
    try:
        data = request.get_json()
        print(f"Registration attempt: {data}")
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the slot is still available
        cursor.execute('''
            SELECT ls.is_available, q.year, q.quarter_number, q.meeting_date, ts.start_time, ts.end_time
            FROM lecture_slots ls
            JOIN quarters q ON ls.quarter_id = q.id
            JOIN time_slots ts ON ls.time_slot_id = ts.id
            WHERE ls.id = ?
        ''', (data.get('lecture_slot_id'),))
        
        slot_info = cursor.fetchone()
        if not slot_info or not slot_info[0]:
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
        
        # Send notification
        quarter_months = {1: 'February', 2: 'May', 3: 'August', 4: 'November'}
        month_name = quarter_months.get(slot_info[2], f'Q{slot_info[2]}')
        
        quarter_info = {
            'name': f"{month_name} {slot_info[1]} - MCES Education",
            'meeting_date': slot_info[3]
        }
        
        # Clean time formatting
        start_time = slot_info[4]
        end_time = slot_info[5]
        if ':' in start_time:
            start_time = ':'.join(start_time.split(':')[:2])
        if ':' in end_time:
            end_time = ':'.join(end_time.split(':')[:2])
        
        print(f"""
        📧 NEW SPEAKER REGISTRATION:
        ===========================
        Speaker: {data.get('speaker_name')}
        Email: {data.get('speaker_email')}
        Phone: {data.get('speaker_phone', 'Not provided')}
        Specialty: {data.get('specialty', 'Not provided')}
        
        Meeting: {quarter_info['name']}
        Date: {quarter_info['meeting_date']}
        Time Slot: {start_time} - {end_time}
        
        Topic: {data.get('topic_title')}
        Description: {data.get('topic_description', 'Not provided')}
        
        Registered at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        ===========================
        """)
        
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

# ADMIN ENDPOINTS (Simple version)

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Simple admin login"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username == 'admin' and password == 'admin123':
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {'username': 'admin'}
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Login error occurred'
        }), 500

@app.route('/api/admin/registrations', methods=['GET'])
def get_all_registrations():
    """Get all speaker registrations for admin view"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                sr.id,
                sr.speaker_name,
                sr.speaker_email,
                sr.speaker_phone,
                sr.specialty,
                sr.topic_title,
                sr.topic_description,
                sr.registered_at,
                sr.status,
                q.year,
                q.quarter_number,
                q.meeting_date,
                ts.start_time,
                ts.end_time,
                ts.slot_name
            FROM speaker_registrations sr
            JOIN lecture_slots ls ON sr.lecture_slot_id = ls.id
            JOIN quarters q ON ls.quarter_id = q.id
            JOIN time_slots ts ON ls.time_slot_id = ts.id
            ORDER BY q.year DESC, q.quarter_number ASC, ts.start_time ASC
        ''')
        
        registrations = cursor.fetchall()
        
        # Map quarter numbers to months
        quarter_months = {1: 'February', 2: 'May', 3: 'August', 4: 'November'}
        
        registration_list = []
        for reg in registrations:
            month_name = quarter_months.get(reg[10], f'Q{reg[10]}')
            quarter_name = f"{month_name} {reg[9]} - MCES Education"
            
            # Clean time formatting
            start_time = reg[12]
            end_time = reg[13]
            if ':' in start_time:
                start_time = ':'.join(start_time.split(':')[:2])
            if ':' in end_time:
                end_time = ':'.join(end_time.split(':')[:2])
            
            registration_list.append({
                'id': reg[0],
                'speaker_name': reg[1],
                'speaker_email': reg[2],
                'speaker_phone': reg[3],
                'specialty': reg[4],
                'topic_title': reg[5],
                'topic_description': reg[6],
                'registered_at': reg[7],
                'status': reg[8],
                'quarter_name': quarter_name,
                'meeting_date': reg[11],
                'time_slot': f"{start_time} - {end_time}",
                'slot_name': reg[14]
            })
        
        conn.close()
        
        return jsonify({
            'registrations': registration_list,
            'count': len(registration_list)
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error getting registrations: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/admin/reset-registrations', methods=['POST'])
def reset_registrations():
    """Reset all speaker registrations"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Count existing registrations
        cursor.execute('SELECT COUNT(*) FROM speaker_registrations')
        registration_count = cursor.fetchone()[0]
        
        # Delete all speaker registrations
        cursor.execute('DELETE FROM speaker_registrations')
        
        # Mark all lecture slots as available
        cursor.execute('UPDATE lecture_slots SET is_available = 1')
        
        conn.commit()
        conn.close()
        
        print(f"🔄 ADMIN ACTION: Reset {registration_count} registrations")
        
        return jsonify({
            'message': f'🎉 SUCCESS! System reset complete!',
            'cleared_registrations': registration_count,
            'status': 'All time slots are now available'
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error resetting registrations: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/test')
def api_test():
    return {
        "message": "MCES Quarterly Education Series API is working!",
        "timestamp": datetime.now().isoformat(),
        "status": "success"
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
