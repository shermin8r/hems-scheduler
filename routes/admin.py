from flask import Blueprint, request, jsonify, session
from src.models.user import db
from src.models.admin_user import AdminUser
from src.models.quarter import Quarter
from src.models.speaker_registration import SpeakerRegistration
from src.models.lecture_slot import LectureSlot
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Admin authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        admin = AdminUser.query.filter_by(username=data['username']).first()
        
        if admin and admin.check_password(data['password']):
            session['admin_id'] = admin.id
            return jsonify({
                'success': True,
                'admin': admin.to_dict(),
                'message': 'Login successful'
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/logout', methods=['POST'])
@admin_required
def admin_logout():
    """Admin logout endpoint"""
    session.pop('admin_id', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@admin_bp.route('/admin/check-auth', methods=['GET'])
def check_admin_auth():
    """Check if admin is authenticated"""
    if 'admin_id' in session:
        admin = AdminUser.query.get(session['admin_id'])
        if admin:
            return jsonify({
                'success': True,
                'authenticated': True,
                'admin': admin.to_dict()
            })
    
    return jsonify({
        'success': True,
        'authenticated': False
    })

@admin_bp.route('/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    """Get admin dashboard data"""
    try:
        # Get summary statistics
        total_quarters = Quarter.query.count()
        active_quarters = Quarter.query.filter_by(is_active=True).count()
        total_registrations = SpeakerRegistration.query.filter_by(status='confirmed').count()
        
        # Get recent registrations
        recent_registrations = SpeakerRegistration.query.order_by(
            SpeakerRegistration.registered_at.desc()
        ).limit(10).all()
        
        # Get quarters with registration counts
        quarters_with_counts = []
        quarters = Quarter.query.order_by(Quarter.year.desc(), Quarter.quarter_number.desc()).all()
        
        for quarter in quarters:
            registration_count = SpeakerRegistration.query.join(LectureSlot).filter(
                LectureSlot.quarter_id == quarter.id,
                SpeakerRegistration.status == 'confirmed'
            ).count()
            
            quarter_data = quarter.to_dict()
            quarter_data['registration_count'] = registration_count
            quarter_data['total_slots'] = 3  # Always 3 time slots per quarter
            quarters_with_counts.append(quarter_data)
        
        return jsonify({
            'success': True,
            'dashboard': {
                'summary': {
                    'total_quarters': total_quarters,
                    'active_quarters': active_quarters,
                    'total_registrations': total_registrations
                },
                'recent_registrations': [reg.to_dict() for reg in recent_registrations],
                'quarters': quarters_with_counts
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/export/registrations', methods=['GET'])
@admin_required
def export_registrations():
    """Export registrations data"""
    try:
        quarter_id = request.args.get('quarter_id', type=int)
        
        query = SpeakerRegistration.query.join(LectureSlot)
        
        if quarter_id:
            query = query.filter(LectureSlot.quarter_id == quarter_id)
        
        registrations = query.order_by(
            LectureSlot.quarter_id.desc(),
            SpeakerRegistration.registered_at.desc()
        ).all()
        
        # Format data for export
        export_data = []
        for reg in registrations:
            export_data.append({
                'Quarter': f"{reg.lecture_slot.quarter.year} Q{reg.lecture_slot.quarter.quarter_number}",
                'Meeting Date': reg.lecture_slot.quarter.meeting_date.isoformat(),
                'Time Slot': reg.lecture_slot.time_slot.slot_name,
                'Speaker Name': reg.speaker_name,
                'Email': reg.speaker_email,
                'Phone': reg.speaker_phone or '',
                'Specialty': reg.specialty or '',
                'Topic Title': reg.topic_title or '',
                'Topic Description': reg.topic_description or '',
                'Registration Date': reg.registered_at.isoformat(),
                'Status': reg.status
            })
        
        return jsonify({
            'success': True,
            'data': export_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/change-password', methods=['POST'])
@admin_required
def change_admin_password():
    """Change admin password"""
    try:
        data = request.get_json()
        
        if not data or 'current_password' not in data or 'new_password' not in data:
            return jsonify({'success': False, 'error': 'Current and new password required'}), 400
        
        admin = AdminUser.query.get(session['admin_id'])
        
        if not admin.check_password(data['current_password']):
            return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400
        
        if len(data['new_password']) < 6:
            return jsonify({'success': False, 'error': 'New password must be at least 6 characters'}), 400
        
        admin.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

