from flask_sqlalchemy import SQLAlchemy
from datetime import time
from src.models.user import db

class TimeSlot(db.Model):
    __tablename__ = 'time_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    slot_name = db.Column(db.String(100), nullable=False)
    
    # Relationship to lecture slots
    lecture_slots = db.relationship('LectureSlot', backref='time_slot', lazy=True)
    
    def __repr__(self):
        return f'<TimeSlot {self.slot_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'slot_name': self.slot_name
        }
    
    @staticmethod
    def create_default_slots():
        """Create the three default time slots if they don't exist"""
        slots = [
            {'start_time': time(9, 0), 'end_time': time(10, 0), 'slot_name': 'Morning Session (09:00-10:00)'},
            {'start_time': time(10, 0), 'end_time': time(11, 0), 'slot_name': 'Mid-Morning Session (10:00-11:00)'},
            {'start_time': time(11, 0), 'end_time': time(12, 0), 'slot_name': 'Late Morning Session (11:00-12:00)'}
        ]
        
        for slot_data in slots:
            existing = TimeSlot.query.filter_by(start_time=slot_data['start_time']).first()
            if not existing:
                slot = TimeSlot(**slot_data)
                db.session.add(slot)
        
        db.session.commit()

