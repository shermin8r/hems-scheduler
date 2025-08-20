import os
from flask import Flask, send_from_directory
from flask_cors import CORS
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

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, origins="*")

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
            return "index.html not found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

