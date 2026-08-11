from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class SeenTitle(db.Model):
    """Every article that's ever been shown, so we stop repeating them."""
    __tablename__ = "seen_titles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    genre = db.Column(db.String(50))
    seen_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "title", name="uq_user_title"),)


class LearnedEntry(db.Model):
    """Articles the user has marked as learned, with their own notes."""
    __tablename__ = "learned_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500))
    genre = db.Column(db.String(50))
    words = db.Column(db.Integer)
    rating = db.Column(db.Integer)          # 1-10, optional
    keywords = db.Column(db.String(300))    # short thoughts / tags, optional
    reflection = db.Column(db.Text)         # longer summary / what it invoked, optional
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def keyword_list(self):
        if not self.keywords:
            return []
        return [k.strip() for k in self.keywords.split(",") if k.strip()]


class ReadLaterEntry(db.Model):
    """Articles saved to read later — lighter than a full 'learned' entry."""
    __tablename__ = "read_later_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500))
    genre = db.Column(db.String(50))
    words = db.Column(db.Integer)
    note = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)