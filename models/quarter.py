from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class Quarter(db.Model):
    __tablename__ = 'quarters'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    quarter_number = db.Column(db.Integer, nullable=False)  # 1-4
    meeting_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship to lecture slots
    lecture_slots = db.relationship('LectureSlot', backref='quarter', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Quarter {self.year} Q{self.quarter_number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'year': self.year,
            'quarter_number': self.quarter_number,
            'meeting_date': self.meeting_date.isoformat() if self.meeting_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

