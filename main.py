import os
from datetime import datetime
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, origins="*")

# Import models and routes after app creation
try:
    from models.user import db
    from models.quarter import Quarter
    from models.time_slot import TimeSlot
    from models.lecture_slot import LectureSlot
    from models.speaker_registration import SpeakerRegistration
    from models.admin_user import AdminUser
    from routes.user import user_bp
    from routes.quarters import quarters_bp
    from routes.registrations import registrations_bp
    from routes.admin import admin_bp
    
    # Register blueprints
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(quarters_bp, url_prefix='/api')
    app.register_blueprint(registrations_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    
    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    # Create database directory if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)
    
    with app.app_context():
        db.create_all()
        # Initialize default data
        TimeSlot.create_default_slots()
        AdminUser.create_default_admin()
        
    print("✅ Database and API routes initialized successfully")
        
except Exception as e:
    print(f"❌ Error during initialization: {e}")
    # Continue without database for basic functionality

# Add direct quarter creation route to main app (bypass blueprint issues)
@app.route('/api/quarters/create-sample', methods=['GET', 'POST'])
def create_sample_quarter_direct():
    """Direct route to create sample quarter - bypasses blueprint issues"""
    try:
        # Import here to avoid circular imports
        from models.quarter import Quarter
        from models.time_slot import TimeSlot
        from models.lecture_slot import LectureSlot
        
        # Check if we already have quarters
        existing = Quarter.get_all()
        if existing:
            return jsonify({
                'message': 'Success! Quarters already exist',
                'quarters': [q.to_dict() for q in existing],
                'status': 'already_exists'
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
                'next_steps': [
                    '✅ Speakers can now register at your website',
                    '✅ Share the registration link with potential speakers',
                    '✅ Three time slots are ready: 9-10, 10-11, 11-12',
                    '✅ System prevents double-booking automatically'
                ],
                'registration_url': 'https://hems.shermerautomation.com',
                'status': 'created'
            }), 201
        else:
            return jsonify({
                'message': 'Failed to create sample quarter',
                'error': 'Database creation failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Error creating quarter: {str(e)}',
            'error_type': type(e).__name__
        }), 500

# Add test route to verify API is working
@app.route('/api/test')
def api_test():
    return {
        "message": "API is working!",
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }, 200

# Add route to check existing quarters
@app.route('/api/quarters/check', methods=['GET'])
def check_quarters():
    """Check what quarters exist"""
    try:
        from models.quarter import Quarter
        quarters = Quarter.get_all()
        return jsonify({
            'message': f'Found {len(quarters)} quarter(s)',
            'quarters': [q.to_dict() for q in quarters],
            'count': len(quarters)
        }), 200
    except Exception as e:
        return jsonify({
            'message': f'Error checking quarters: {str(e)}'
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
