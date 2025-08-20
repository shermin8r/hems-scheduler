from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class LectureSlot(db.Model):
    __tablename__ = 'lecture_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    quarter_id = db.Column(db.Integer, db.ForeignKey('quarters.id'), nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slots.id'), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to speaker registrations
    registrations = db.relationship('SpeakerRegistration', backref='lecture_slot', lazy=True, cascade='all, delete-orphan')
    
    # Unique constraint to prevent duplicate quarter-time combinations
    __table_args__ = (db.UniqueConstraint('quarter_id', 'time_slot_id', name='unique_quarter_time'),)
    
    def __repr__(self):
        return f'<LectureSlot Q{self.quarter.quarter_number if self.quarter else "?"} {self.time_slot.slot_name if self.time_slot else "?"}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'quarter_id': self.quarter_id,
            'time_slot_id': self.time_slot_id,
            'is_available': self.is_available,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'quarter': self.quarter.to_dict() if self.quarter else None,
            'time_slot': self.time_slot.to_dict() if self.time_slot else None,
            'registration_count': len(self.registrations)
        }
    
    def mark_unavailable(self):
        """Mark this slot as unavailable"""
        self.is_available = False
        db.session.commit()
    
    def mark_available(self):
        """Mark this slot as available"""
        self.is_available = True
        db.session.commit()

