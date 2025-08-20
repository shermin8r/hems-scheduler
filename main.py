import os
import sys
from datetime import datetime
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, origins="*")

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create database directory if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)

# Initialize database and models
try:
    from models.user import db
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        print("✅ Database initialized successfully")
        
        # Import models after database is initialized
        from models.quarter import Quarter
        from models.time_slot import TimeSlot
        from models.lecture_slot import LectureSlot
        from models.speaker_registration import SpeakerRegistration
        from models.admin_user import AdminUser
        
        # Initialize default data
        TimeSlot.create_default_slots()
        AdminUser.create_default_admin()
        print("✅ Default data created")
        
except Exception as e:
    print(f"❌ Error during initialization: {e}")

# Import and register blueprints
try:
    from routes.user import user_bp
    from routes.quarters import quarters_bp
    from routes.registrations import registrations_bp
    from routes.admin import admin_bp
    
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(quarters_bp, url_prefix='/api')
    app.register_blueprint(registrations_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    print("✅ Blueprints registered successfully")
    
except Exception as e:
    print(f"❌ Error registering blueprints: {e}")

# Direct quarter creation route (bypasses blueprint issues)
@app.route('/api/quarters/create-sample', methods=['GET', 'POST'])
def create_sample_quarter_direct():
    """Direct route to create sample quarter"""
    try:
        # Import models directly in the route
        sys.path.insert(0, os.path.dirname(__file__))
        
        from models.quarter import Quarter
        from models.time_slot import TimeSlot
        from models.lecture_slot import LectureSlot
        
        # Check if we already have quarters
        with app.app_context():
            existing = Quarter.get_all()
            if existing:
                return jsonify({
                    'message': '✅ Success! Quarters already exist',
                    'quarters': [q.to_dict() for q in existing],
                    'count': len(existing),
                    'status': 'already_exists',
                    'registration_url': 'https://hems.shermerautomation.com'
                }), 200
            
            # Create Q1 2025 sample quarter
            quarter = Quarter.create(
                name='Q1 2025 - HEMS Education',
                start_date='2025-01-01',
                end_date='2025-03-31',
                location='HEMS Training Center',
                description='First quarter 2025 education meetings for HEMS clinicians'
            )
            
            if quarter:
                # Create lecture slots
                time_slots = TimeSlot.get_all()
                slots_created = []
                
                for time_slot in time_slots:
                    lecture_slot = LectureSlot.create(quarter.id, time_slot.id)
                    if lecture_slot:
                        slots_created.append({
                            'time': f"{time_slot.start_time} - {time_slot.end_time}",
                            'available': True
                        })
                
                return jsonify({
                    'message': '🎉 SUCCESS! Sample quarter created successfully!',
                    'quarter': quarter.to_dict(),
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
            else:
                return jsonify({
                    'message': '❌ Failed to create sample quarter',
                    'error': 'Database creation failed'
                }), 500
            
    except ImportError as e:
        return jsonify({
            'message': f'Import error: {str(e)}',
            'error_type': 'ImportError',
            'suggestion': 'Check if all model files exist in the models/ directory'
        }), 500
    except Exception as e:
        return jsonify({
            'message': f'Error creating quarter: {str(e)}',
            'error_type': type(e).__name__
        }), 500

# Simple quarter creation without complex models (fallback)
@app.route('/api/quarters/create-simple', methods=['GET', 'POST'])
def create_simple_quarter():
    """Simplified quarter creation using direct SQL"""
    try:
        from models.user import db
        
        with app.app_context():
            # Check if quarters table exists and has data
            result = db.engine.execute("SELECT COUNT(*) as count FROM quarters").fetchone()
            if result and result[0] > 0:
                return jsonify({
                    'message': '✅ Quarters already exist in database',
                    'count': result[0],
                    'status': 'already_exists'
                }), 200
            
            # Insert quarter directly
            db.engine.execute("""
                INSERT INTO quarters (name, start_date, end_date, location, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                'Q1 2025 - HEMS Education',
                '2025-01-01',
                '2025-03-31', 
                'HEMS Training Center',
                'First quarter 2025 education meetings',
                datetime.now()
            ))
            
            return jsonify({
                'message': '🎉 SUCCESS! Simple quarter created!',
                'quarter': {
                    'name': 'Q1 2025 - HEMS Education',
                    'start_date': '2025-01-01',
                    'end_date': '2025-03-31',
                    'location': 'HEMS Training Center'
                },
                'status': 'created',
                'registration_url': 'https://hems.shermerautomation.com'
            }), 201
            
    except Exception as e:
        return jsonify({
            'message': f'Simple creation error: {str(e)}',
            'error_type': type(e).__name__
        }), 500

# Test route
@app.route('/api/test')
def api_test():
    return {
        "message": "API is working!",
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }, 200

# Check quarters route
@app.route('/api/quarters/check', methods=['GET'])
def check_quarters():
    """Check what quarters exist"""
    try:
        from models.quarter import Quarter
        with app.app_context():
            quarters = Quarter.get_all()
            return jsonify({
                'message': f'Found {len(quarters)} quarter(s)',
                'quarters': [q.to_dict() for q in quarters],
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
