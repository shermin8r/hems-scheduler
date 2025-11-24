import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from flask import Flask, send_from_directory, jsonify, request, make_response
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'mces-secure-scheduler-2024-' + secrets.token_hex(16)

# Enable CORS for all routes
CORS(app, origins="*")

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'app.db')

# Simple session storage (in production, use Redis or database)
admin_sessions = {}

def hash_password(password):
    """Simple password hashing"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return salt + password_hash

def verify_password(password, stored_hash):
    """Verify password against stored hash"""
    try:
        salt = stored_hash[:32]
        stored_password_hash = stored_hash[32:]
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash == stored_password_hash
    except:
        return False

def generate_session_token():
    """Generate simple session token"""
    return secrets.token_hex(32)

def log_admin_activity(username, action, success=True):
    """Log admin activities"""
    try:
        print(f"🔒 ADMIN ACTIVITY: {username} - {action} - {'SUCCESS' if success else 'FAILED'} - {datetime.now()}")
    except Exception as e:
        print(f"Error logging admin activity: {e}")

def ensure_database_and_data():
    """Ensure database exists with proper structure and secure admin user"""
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
        
        # Create simple admin_users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Check if secure admin user exists
        cursor.execute('SELECT COUNT(*) FROM admin_users WHERE username = ?', ('mces_admin',))
        admin_exists = cursor.fetchone()[0] > 0
        
        if not admin_exists:
            # Create secure admin user
            secure_password = 'MCES2024!Secure'
            password_hash = hash_password(secure_password)
            
            cursor.execute('''
                INSERT INTO admin_users (username, password_hash, is_active)
                VALUES (?, ?, ?)
            ''', ('mces_admin', password_hash, 1))
            
            print("✅ Secure admin user created: mces_admin / MCES2024!Secure")
        
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
        
        conn.commit()
        conn.close()
        
        print("✅ Secure database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

# Initialize database on startup
ensure_database_and_data()

def send_notification_email(registration_data, quarter_info, slot_info):
    """Send email notification when someone registers"""
    try:
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
        
    except Exception as e:
        print(f"Error sending notification: {e}")

def require_admin_auth(f):
    """Simple decorator to require admin authentication"""
    def decorated_function(*args, **kwargs):
        session_token = request.headers.get('Authorization')
        if not session_token:
            session_token = request.cookies.get('admin_session')
        
        if not session_token:
            return jsonify({'error': 'No authentication provided'}), 401
        
        # Remove 'Bearer ' prefix if present
        if session_token.startswith('Bearer '):
            session_token = session_token[7:]
        
        if session_token not in admin_sessions:
            return jsonify({'error': 'Invalid or expired session'}), 401
        
        session_data = admin_sessions[session_token]
        if datetime.now() > session_data['expires']:
            del admin_sessions[session_token]
            return jsonify({'error': 'Session expired'}), 401
        
        # Extend session
        session_data['expires'] = datetime.now() + timedelta(hours=8)
        
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

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

# SECURE ADMIN ENDPOINTS

@app.route('/api/admin-secure-mces/login', methods=['POST'])
def secure_admin_login():
    """Secure admin login"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No login data provided'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password are required'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, password_hash, is_active 
            FROM admin_users 
            WHERE username = ? AND is_active = 1
        ''', (username,))
        user = cursor.fetchone()
        
        if user and verify_password(password, user[2]):
            # Generate session token
            session_token = generate_session_token()
            
            # Store session
            admin_sessions[session_token] = {
                'user_id': user[0],
                'username': user[1],
                'expires': datetime.now() + timedelta(hours=8)
            }
            
            log_admin_activity(username, 'LOGIN_SUCCESS', True)
            
            # Create response with secure cookie
            response = make_response(jsonify({
                'success': True,
                'message': 'Login successful',
                'token': session_token,
                'user': {'id': user[0], 'username': user[1]}
            }))
            
            response.set_cookie('admin_session', session_token, max_age=8*3600, httponly=True)
            
            conn.close()
            return response, 200
        else:
            log_admin_activity(username, 'LOGIN_FAILED', False)
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
            
    except Exception as e:
        print(f"Secure login error: {e}")
        return jsonify({'success': False, 'message': 'Login error occurred'}), 500

@app.route('/api/admin-secure-mces/logout', methods=['POST'])
@require_admin_auth
def secure_admin_logout():
    """Secure admin logout"""
    try:
        session_token = request.headers.get('Authorization') or request.cookies.get('admin_session')
        if session_token and session_token.startswith('Bearer '):
            session_token = session_token[7:]
        
        if session_token in admin_sessions:
            username = admin_sessions[session_token]['username']
            del admin_sessions[session_token]
            log_admin_activity(username, 'LOGOUT', True)
        
        response = make_response(jsonify({'success': True, 'message': 'Logged out successfully'}))
        response.set_cookie('admin_session', '', expires=0)
        
        return response, 200
        
    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({'success': False, 'message': 'Logout error occurred'}), 500

@app.route('/api/admin-secure-mces/verify', methods=['GET'])
@require_admin_auth
def verify_admin_session():
    """Verify admin session is still valid"""
    try:
        session_token = request.headers.get('Authorization') or request.cookies.get('admin_session')
        if session_token and session_token.startswith('Bearer '):
            session_token = session_token[7:]
        
        if session_token in admin_sessions:
            session_data = admin_sessions[session_token]
            return jsonify({
                'success': True,
                'user': {
                    'id': session_data['user_id'],
                    'username': session_data['username']
                }
            }), 200
        
        return jsonify({'success': False, 'message': 'Session not found'}), 401
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Session verification failed'}), 401

@app.route('/api/admin-secure-mces/registrations', methods=['GET'])
@require_admin_auth
def get_all_registrations_secure():
    """Get all speaker registrations for secure admin view"""
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

@app.route('/api/admin-secure-mces/reset-registrations', methods=['POST'])
@require_admin_auth
def reset_registrations_secure():
    """Secure reset of all speaker registrations"""
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
        
        log_admin_activity('admin', f'RESET_REGISTRATIONS_{registration_count}', True)
        
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

@app.route('/api/admin-secure-mces/export/csv', methods=['GET'])
@require_admin_auth
def export_registrations_csv_secure():
    """Secure export of all registrations as CSV data"""
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
        
        log_admin_activity('admin', 'EXPORT_CSV', True)
        
        return jsonify({
            'csv_data': csv_content,
            'filename': f'MCES_Registrations_{datetime.now().strftime("%Y%m%d")}.csv'
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error exporting CSV: {str(e)}',
            'error_type': type(e).__name__
        }), 500

# PUBLIC ENDPOINTS (quarters, slots, registrations)

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
    print(f"🔒 Secure admin access available")
    app.run(host='0.0.0.0', port=port, debug=False)
