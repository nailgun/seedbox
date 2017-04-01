from .db import db


class CredentialsData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cert = db.Column(db.Binary, nullable=False)
    key = db.Column(db.Binary, nullable=False)

    def __repr__(self):
        return '<CredentialsData #%r>' % self.id
