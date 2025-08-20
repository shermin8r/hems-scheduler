import os
import sqlite3
from datetime import datetime
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
        
        # Create admin_users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create default admin user if it doesn't exist
        cursor.execute('SELECT COUNT(*) FROM admin_users WHERE username = ?', ('admin',))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO admin_users (username, password_hash, email)
                VALUES (?, ?, ?)
            ''', ('admin', 'admin123', 'admin@example.com'))  # Simple password for now
        
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
        
        conn.commit()
        conn.close()
        
        print("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

# Initialize database on startup
ensure_database_and_data()

def send_notification_email(registration_data, quarter_info, slot_info):
    """Send email notification when someone registers"""
    try:
        # This is a placeholder - you'll need to configure with your email settings
        # For now, we'll just log the notification
        print(f"""
        📧 EMAIL NOTIFICATION:
        =====================
        New speaker registration!
        
        Speaker: {registration_data['speaker_name']}
        Email: {registration_data['speaker_email']}
        Phone: {registration_data.get('speaker_phone', 'Not provided')}
        Specialty: {registration_data.get('specialty', 'Not provided')}
        
        Meeting: {quarter_info['name']}
        Date: {quarter_info['meeting_date']}
        Time Slot: {slot_info['time_display']}
        
        Topic: {registration_data['topic_title']}
        Description: {registration_data.get('topic_description', 'Not provided')}
        
        Registered at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        =====================
        """)
        
        # TODO: Configure actual email sending
        # You can set up SMTP settings here when ready
        
    except Exception as e:
        print(f"Error sending notification: {e}")

# Logging middleware
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

# ADMIN ENDPOINTS

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Simple admin login"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, email FROM admin_users WHERE username = ? AND password_hash = ?', 
                      (username, password))
        user = cursor.fetchone()
        
        conn.close()
        
        if user:
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user_id': user[0],
                'email': user[1]
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Login error: {str(e)}'
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

@app.route('/api/admin/registrations/quarter/<int:quarter_id>', methods=['GET'])
def get_quarter_registrations(quarter_id):
    """Get registrations for a specific quarter"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                sr.speaker_name,
                sr.speaker_email,
                sr.speaker_phone,
                sr.specialty,
                sr.topic_title,
                sr.topic_description,
                sr.registered_at,
                ts.start_time,
                ts.end_time,
                ts.slot_name
            FROM speaker_registrations sr
            JOIN lecture_slots ls ON sr.lecture_slot_id = ls.id
            JOIN time_slots ts ON ls.time_slot_id = ts.id
            WHERE ls.quarter_id = ?
            ORDER BY ts.start_time ASC
        ''', (quarter_id,))
        
        registrations = cursor.fetchall()
        
        registration_list = []
        for reg in registrations:
            # Clean time formatting
            start_time = reg[7]
            end_time = reg[8]
            if ':' in start_time:
                start_time = ':'.join(start_time.split(':')[:2])
            if ':' in end_time:
                end_time = ':'.join(end_time.split(':')[:2])
            
            registration_list.append({
                'speaker_name': reg[0],
                'speaker_email': reg[1],
                'speaker_phone': reg[2],
                'specialty': reg[3],
                'topic_title': reg[4],
                'topic_description': reg[5],
                'registered_at': reg[6],
                'time_slot': f"{start_time} - {end_time}",
                'slot_name': reg[9]
            })
        
        conn.close()
        
        return jsonify({
            'registrations': registration_list,
            'count': len(registration_list)
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error getting quarter registrations: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/admin/export/csv', methods=['GET'])
def export_registrations_csv():
    """Export all registrations as CSV data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                sr.speaker_name,
                sr.speaker_email,
                sr.speaker_phone,
                sr.specialty,
                sr.topic_title,
                sr.topic_description,
                sr.registered_at,
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
        
        # Create CSV content
        csv_content = "Speaker Name,Email,Phone,Specialty,Topic Title,Topic Description,Registered At,Year,Quarter,Meeting Date,Time Slot,Slot Name\n"
        
        quarter_months = {1: 'February', 2: 'May', 3: 'August', 4: 'November'}
        
        for reg in registrations:
            # Clean time formatting
            start_time = reg[10]
            end_time = reg[11]
            if ':' in start_time:
                start_time = ':'.join(start_time.split(':')[:2])
            if ':' in end_time:
                end_time = ':'.join(end_time.split(':')[:2])
            
            month_name = quarter_months.get(reg[8], f'Q{reg[8]}')
            time_slot = f"{start_time} - {end_time}"
            
            # Escape commas and quotes in CSV
            row = [
                f'"{reg[0]}"',  # speaker_name
                f'"{reg[1]}"',  # speaker_email
                f'"{reg[2] or ""}"',  # speaker_phone
                f'"{reg[3] or ""}"',  # specialty
                f'"{reg[4]}"',  # topic_title
                f'"{reg[5] or ""}"',  # topic_description
                f'"{reg[6]}"',  # registered_at
                str(reg[7]),    # year
                month_name,     # quarter
                f'"{reg[9]}"',  # meeting_date
                time_slot,      # time_slot
                f'"{reg[12]}"'  # slot_name
            ]
            csv_content += ','.join(row) + '\n'
        
        conn.close()
        
        return jsonify({
            'csv_data': csv_content,
            'filename': f'MCES_Registrations_{datetime.now().strftime("%Y%m%d")}.csv'
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error exporting CSV: {str(e)}',
            'error_type': type(e).__name__
        }), 500

# EXISTING ENDPOINTS (quarters, slots, registrations)

@app.route('/api/quarters', methods=['GET'])
def get_all_quarters():
    quarters = get_quarters_data()
    return jsonify(quarters), 200

@app.route('/api/quarters/active', methods=['GET'])
def get_active_quarters():
    quarters = get_quarters_data()
    return jsonify(quarters), 200

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
        
        slot_display = {
            'time_display': f"{start_time} - {end_time}"
        }
        
        send_notification_email(data, quarter_info, slot_display)
        
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
