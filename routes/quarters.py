from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.quarter import Quarter
from src.models.time_slot import TimeSlot
from src.models.lecture_slot import LectureSlot
from datetime import datetime

quarters_bp = Blueprint('quarters', __name__)

@quarters_bp.route('/quarters/active', methods=['GET'])
def get_active_quarters():
    """Get all active quarters"""
    try:
        quarters = Quarter.query.filter_by(is_active=True).order_by(Quarter.year.desc(), Quarter.quarter_number.desc()).all()
        return jsonify({
            'success': True,
            'quarters': [quarter.to_dict() for quarter in quarters]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@quarters_bp.route('/quarters/<int:quarter_id>/available-slots', methods=['GET'])
def get_available_slots(quarter_id):
    """Get available lecture slots for a specific quarter"""
    try:
        quarter = Quarter.query.get_or_404(quarter_id)
        
        # Get all time slots
        time_slots = TimeSlot.query.all()
        available_slots = []
        
        for time_slot in time_slots:
            # Check if there's a lecture slot for this quarter-time combination
            lecture_slot = LectureSlot.query.filter_by(
                quarter_id=quarter_id,
                time_slot_id=time_slot.id
            ).first()
            
            if not lecture_slot:
                # Create lecture slot if it doesn't exist
                lecture_slot = LectureSlot(
                    quarter_id=quarter_id,
                    time_slot_id=time_slot.id,
                    is_available=True
                )
                db.session.add(lecture_slot)
                db.session.commit()
            
            if lecture_slot.is_available:
                slot_data = lecture_slot.to_dict()
                available_slots.append(slot_data)
        
        return jsonify({
            'success': True,
            'quarter': quarter.to_dict(),
            'available_slots': available_slots
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@quarters_bp.route('/quarters', methods=['GET'])
def get_all_quarters():
    """Get all quarters (admin only)"""
    try:
        quarters = Quarter.query.order_by(Quarter.year.desc(), Quarter.quarter_number.desc()).all()
        return jsonify({
            'success': True,
            'quarters': [quarter.to_dict() for quarter in quarters]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@quarters_bp.route('/quarters', methods=['POST'])
def create_quarter():
    """Create a new quarter (admin only)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['year', 'quarter_number', 'meeting_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Parse meeting date
        try:
            meeting_date = datetime.strptime(data['meeting_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Check if quarter already exists
        existing = Quarter.query.filter_by(
            year=data['year'],
            quarter_number=data['quarter_number']
        ).first()
        
        if existing:
            return jsonify({'success': False, 'error': 'Quarter already exists'}), 400
        
        # Create new quarter
        quarter = Quarter(
            year=data['year'],
            quarter_number=data['quarter_number'],
            meeting_date=meeting_date,
            is_active=data.get('is_active', True)
        )
        
        db.session.add(quarter)
        db.session.commit()
        
        # Create lecture slots for this quarter
        time_slots = TimeSlot.query.all()
        for time_slot in time_slots:
            lecture_slot = LectureSlot(
                quarter_id=quarter.id,
                time_slot_id=time_slot.id,
                is_available=True
            )
            db.session.add(lecture_slot)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'quarter': quarter.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@quarters_bp.route('/quarters/<int:quarter_id>', methods=['PUT'])
def update_quarter(quarter_id):
    """Update a quarter (admin only)"""
    try:
        quarter = Quarter.query.get_or_404(quarter_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'year' in data:
            quarter.year = data['year']
        if 'quarter_number' in data:
            quarter.quarter_number = data['quarter_number']
        if 'meeting_date' in data:
            quarter.meeting_date = datetime.strptime(data['meeting_date'], '%Y-%m-%d').date()
        if 'is_active' in data:
            quarter.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'quarter': quarter.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@quarters_bp.route('/quarters/<int:quarter_id>', methods=['DELETE'])
def delete_quarter(quarter_id):
    """Delete a quarter (admin only)"""
    try:
        quarter = Quarter.query.get_or_404(quarter_id)
        db.session.delete(quarter)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Quarter deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

