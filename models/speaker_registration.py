from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class SpeakerRegistration(db.Model):
    __tablename__ = 'speaker_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    lecture_slot_id = db.Column(db.Integer, db.ForeignKey('lecture_slots.id'), nullable=False)
    speaker_name = db.Column(db.String(200), nullable=False)
    speaker_email = db.Column(db.String(200), nullable=False)
    speaker_phone = db.Column(db.String(50))
    specialty = db.Column(db.String(200))
    topic_title = db.Column(db.String(300))
    topic_description = db.Column(db.Text)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='confirmed')  # 'confirmed', 'pending', 'cancelled'
    
    def __repr__(self):
        return f'<SpeakerRegistration {self.speaker_name} - {self.topic_title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'lecture_slot_id': self.lecture_slot_id,
            'speaker_name': self.speaker_name,
            'speaker_email': self.speaker_email,
            'speaker_phone': self.speaker_phone,
            'specialty': self.specialty,
            'topic_title': self.topic_title,
            'topic_description': self.topic_description,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'status': self.status,
            'lecture_slot': self.lecture_slot.to_dict() if self.lecture_slot else None
        }
    
    def cancel_registration(self):
        """Cancel this registration and make the slot available again"""
        self.status = 'cancelled'
        if self.lecture_slot:
            self.lecture_slot.mark_available()
        db.session.commit()
    
    def confirm_registration(self):
        """Confirm this registration and mark the slot as unavailable"""
        self.status = 'confirmed'
        if self.lecture_slot:
            self.lecture_slot.mark_unavailable()
        db.session.commit()

