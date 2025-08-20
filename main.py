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

@app.route('/api/quarters/create-sample', methods=['GET', 'POST'])
def create_sample_quarter():
    """Create sample quarter using the correct database schema"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if quarters already exist
        cursor.execute('SELECT COUNT(*) FROM quarters WHERE is_active = 1')
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            # Get existing active quarters
            cursor.execute('''
                SELECT id, year, quarter_number, meeting_date, is_active 
                FROM quarters 
                WHERE is_active = 1
            ''')
            quarters = cursor.fetchall()
            
            quarter_list = []
            for q in quarters:
                quarter_list.append({
                    'id': q[0],
                    'year': q[1],
                    'quarter_number': q[2],
                    'meeting_date': q[3],
                    'is_active': q[4]
                })
            
            conn.close()
            return jsonify({
                'message': '✅ SUCCESS! Active quarters already exist',
                'quarters': quarter_list,
                'count': existing_count,
                'status': 'already_exists',
                'registration_url': 'https://hems.shermerautomation.com'
            }), 200
        
        # Create new quarter using the correct schema
        # quarters table: id, year, quarter_number, meeting_date, created_at, is_active
        cursor.execute('''
            INSERT INTO quarters (year, quarter_number, meeting_date, is_active)
            VALUES (?, ?, ?, ?)
        ''', (
            2025,      # year
            1,         # quarter_number (Q1)
            '2025-03-15',  # meeting_date (mid-quarter)
            1          # is_active
        ))
        
        quarter_id = cursor.lastrowid
        
        # Get existing time slots
        cursor.execute('SELECT id, start_time, end_time, slot_name FROM time_slots')
        time_slots = cursor.fetchall()
        
        # If no time slots exist, create them
        if not time_slots:
            default_slots = [
                ('09:00', '10:00', 'Morning Session'),
                ('10:00', '11:00', 'Mid-Morning Session'),
                ('11:00', '12:00', 'Late Morning Session')
            ]
            
            for slot in default_slots:
                cursor.execute('''
                    INSERT INTO time_slots (start_time, end_time, slot_name)
                    VALUES (?, ?, ?)
                ''', slot)
            
            # Get the newly created time slots
            cursor.execute('SELECT id, start_time, end_time, slot_name FROM time_slots')
            time_slots = cursor.fetchall()
        
        # Create lecture slots for this quarter
        # lecture_slots table: id, quarter_id, time_slot_id, is_available, created_at
        slots_created = []
        for time_slot in time_slots:
            cursor.execute('''
                INSERT INTO lecture_slots (quarter_id, time_slot_id, is_available)
                VALUES (?, ?, ?)
            ''', (quarter_id, time_slot[0], 1))  # 1 = available
            
            slots_created.append({
                'time_slot_id': time_slot[0],
                'time': f"{time_slot[1]} - {time_slot[2]}",
                'name': time_slot[3],
                'available': True
            })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': '🎉 SUCCESS! Q1 2025 quarter created successfully!',
            'quarter': {
                'id': quarter_id,
                'year': 2025,
                'quarter_number': 1,
                'meeting_date': '2025-03-15',
                'name': 'Q1 2025 - HEMS Education',
                'is_active': True
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
    """Get active quarters using the correct schema"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get active quarters with slot information
        cursor.execute('''
            SELECT q.id, q.year, q.quarter_number, q.meeting_date, q.is_active,
                   COUNT(ls.id) as total_slots,
                   SUM(CASE WHEN ls.is_available = 1 THEN 1 ELSE 0 END) as available_slots
            FROM quarters q
            LEFT JOIN lecture_slots ls ON q.id = ls.quarter_id
            WHERE q.is_active = 1
            GROUP BY q.id, q.year, q.quarter_number, q.meeting_date, q.is_active
        ''')
        
        quarters = cursor.fetchall()
        
        quarter_list = []
        for q in quarters:
            quarter_list.append({
                'id': q[0],
                'year': q[1],
                'quarter_number': q[2],
                'meeting_date': q[3],
                'is_active': bool(q[4]),
                'name': f"Q{q[2]} {q[1]} - HEMS Education",
                'total_slots': q[5] or 0,
                'available_slots': q[6] or 0
            })
        
        conn.close()
        return jsonify(quarter_list), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error getting quarters: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/quarters/<int:quarter_id>/slots', methods=['GET'])
def get_quarter_slots(quarter_id):
    """Get available slots for a specific quarter"""
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
            slot_list.append({
                'lecture_slot_id': slot[0],
                'is_available': bool(slot[1]),
                'start_time': slot[2],
                'end_time': slot[3],
                'slot_name': slot[4],
                'time_display': f"{slot[2]} - {slot[3]}"
            })
        
        conn.close()
        return jsonify(slot_list), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Error getting slots: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/api/test')
def api_test():
    return {
        "message": "API is working!",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "database": "SQLite with correct schema"
    }, 200

@app.route('/api/quarters/check', methods=['GET'])
def check_quarters():
    """Check what quarters exist"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, year, quarter_number, meeting_date, is_active FROM quarters')
        quarters = cursor.fetchall()
        
        quarter_list = []
        for q in quarters:
            quarter_list.append({
                'id': q[0],
                'year': q[1],
                'quarter_number': q[2],
                'meeting_date': q[3],
                'is_active': bool(q[4]),
                'name': f"Q{q[2]} {q[1]} - HEMS Education"
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
