from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.lecture_slot import LectureSlot
from src.models.speaker_registration import SpeakerRegistration
from datetime import datetime
import re

registrations_bp = Blueprint('registrations', __name__)

def validate_email(email):
    """Simple email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@registrations_bp.route('/registrations', methods=['POST'])
def create_registration():
    """Create a new speaker registration"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['lecture_slot_id', 'speaker_name', 'speaker_email']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Validate email format
        if not validate_email(data['speaker_email']):
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400
        
        # Check if lecture slot exists and is available
        lecture_slot = LectureSlot.query.get(data['lecture_slot_id'])
        if not lecture_slot:
            return jsonify({'success': False, 'error': 'Lecture slot not found'}), 404
        
        if not lecture_slot.is_available:
            return jsonify({'success': False, 'error': 'This time slot is no longer available'}), 400
        
        # Check if speaker already registered for this quarter
        existing_registration = SpeakerRegistration.query.join(LectureSlot).filter(
            LectureSlot.quarter_id == lecture_slot.quarter_id,
            SpeakerRegistration.speaker_email == data['speaker_email'],
            SpeakerRegistration.status == 'confirmed'
        ).first()
        
        if existing_registration:
            return jsonify({
                'success': False, 
                'error': 'You have already registered for a slot in this quarter'
            }), 400
        
        # Create registration
        registration = SpeakerRegistration(
            lecture_slot_id=data['lecture_slot_id'],
            speaker_name=data['speaker_name'],
            speaker_email=data['speaker_email'],
            speaker_phone=data.get('speaker_phone', ''),
            specialty=data.get('specialty', ''),
            topic_title=data.get('topic_title', ''),
            topic_description=data.get('topic_description', ''),
            status='confirmed'
        )
        
        db.session.add(registration)
        
        # Mark lecture slot as unavailable
        lecture_slot.is_available = False
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'registration': registration.to_dict(),
            'message': 'Registration successful! You will receive a confirmation email shortly.'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@registrations_bp.route('/registrations/<int:registration_id>', methods=['GET'])
def get_registration(registration_id):
    """Get registration details"""
    try:
        registration = SpeakerRegistration.query.get_or_404(registration_id)
        return jsonify({
            'success': True,
            'registration': registration.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@registrations_bp.route('/registrations', methods=['GET'])
def get_all_registrations():
    """Get all registrations (admin only)"""
    try:
        # Optional filtering by quarter
        quarter_id = request.args.get('quarter_id', type=int)
        status = request.args.get('status')
        
        query = SpeakerRegistration.query
        
        if quarter_id:
            query = query.join(LectureSlot).filter(LectureSlot.quarter_id == quarter_id)
        
        if status:
            query = query.filter(SpeakerRegistration.status == status)
        
        registrations = query.order_by(SpeakerRegistration.registered_at.desc()).all()
        
        return jsonify({
            'success': True,
            'registrations': [reg.to_dict() for reg in registrations]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@registrations_bp.route('/registrations/<int:registration_id>', methods=['PUT'])
def update_registration(registration_id):
    """Update registration status (admin only)"""
    try:
        registration = SpeakerRegistration.query.get_or_404(registration_id)
        data = request.get_json()
        
        old_status = registration.status
        
        # Update fields if provided
        if 'status' in data:
            registration.status = data['status']
            
            # Handle slot availability based on status change
            if old_status == 'confirmed' and data['status'] == 'cancelled':
                # Make slot available again
                registration.lecture_slot.is_available = True
            elif old_status == 'cancelled' and data['status'] == 'confirmed':
                # Make slot unavailable
                registration.lecture_slot.is_available = False
        
        if 'speaker_name' in data:
            registration.speaker_name = data['speaker_name']
        if 'speaker_email' in data:
            registration.speaker_email = data['speaker_email']
        if 'speaker_phone' in data:
            registration.speaker_phone = data['speaker_phone']
        if 'specialty' in data:
            registration.specialty = data['specialty']
        if 'topic_title' in data:
            registration.topic_title = data['topic_title']
        if 'topic_description' in data:
            registration.topic_description = data['topic_description']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'registration': registration.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@registrations_bp.route('/registrations/<int:registration_id>', methods=['DELETE'])
def delete_registration(registration_id):
    """Delete registration (admin only)"""
    try:
        registration = SpeakerRegistration.query.get_or_404(registration_id)
        
        # Make the lecture slot available again
        if registration.lecture_slot:
            registration.lecture_slot.is_available = True
        
        db.session.delete(registration)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Registration deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@registrations_bp.route('/registrations/check-availability', methods=['POST'])
def check_slot_availability():
    """Check if a specific slot is still available"""
    try:
        data = request.get_json()
        lecture_slot_id = data.get('lecture_slot_id')
        
        if not lecture_slot_id:
            return jsonify({'success': False, 'error': 'Missing lecture_slot_id'}), 400
        
        lecture_slot = LectureSlot.query.get(lecture_slot_id)
        if not lecture_slot:
            return jsonify({'success': False, 'error': 'Lecture slot not found'}), 404
        
        return jsonify({
            'success': True,
            'is_available': lecture_slot.is_available,
            'lecture_slot': lecture_slot.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

