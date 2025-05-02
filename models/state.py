# models/state.py
from extensions import db

class State(db.Model):
    __tablename__ = 'state'
    
    state_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    abbreviation = db.Column(db.String(10), nullable=False, unique=True)
    
    
    
    def to_dict(self):
        return {
            'state_id': self.state_id,
            'name': self.name,
            'abbreviation': self.abbreviation
        }