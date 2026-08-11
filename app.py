import os

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)

from models import db, User, SeenTitle, LearnedEntry, ReadLaterEntry
import wiki_client

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "library.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# IMPORTANT: set a real secret key via environment variable in production —
# this signs the session cookie. Don't hardcode it once deployed.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not password:
            flash("username and password are both required.")
            return render_template("register.html")
        if password != confirm:
            flash("passwords don't match.")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash("that username is taken.")
            return render_template("register.html")

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("wrong username or password.")
            return render_template("login.html")

        login_user(user)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("index"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# app routes (all scoped to current_user)
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def index():
    return render_template("index.html", genres=list(wiki_client.GENRES.keys()))


@app.route("/api/find", methods=["POST"])
@login_required
def api_find():
    payload = request.get_json(silent=True) or {}
    genre = payload.get("genre")

    if genre not in wiki_client.GENRES:
        return jsonify(error="that's not a shelf I recognise."), 400

    seen = {
        row.title for row in SeenTitle.query
            .filter_by(user_id=current_user.id)
            .with_entities(SeenTitle.title)
            .all()
    }

    try:
        article = wiki_client.find_article(genre, seen)
    except Exception as error:
        return jsonify(error=f"couldn't reach wikipedia: {error}"), 502

    if not article:
        return jsonify(error="couldn't find anything fresh on this shelf. try again?"), 404

    db.session.add(SeenTitle(user_id=current_user.id, title=article["title"], genre=genre))
    db.session.commit()

    return jsonify(article)


@app.route("/api/learn", methods=["POST"])
@login_required
def api_learn():
    payload = request.get_json(silent=True) or {}

    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify(error="missing title"), 400

    rating = payload.get("rating")
    try:
        rating = int(rating) if rating not in (None, "") else None
        if rating is not None and not (1 <= rating <= 10):
            rating = None
    except (TypeError, ValueError):
        rating = None

    entry = LearnedEntry(
        user_id=current_user.id,
        title=title,
        url=payload.get("url"),
        genre=payload.get("genre"),
        words=payload.get("words"),
        rating=rating,
        keywords=(payload.get("keywords") or "").strip() or None,
        reflection=(payload.get("reflection") or "").strip() or None,
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify(success=True, id=entry.id)


@app.route("/learned")
@login_required
def learned():
    entries = (
        LearnedEntry.query
        .filter_by(user_id=current_user.id)
        .order_by(LearnedEntry.created_at.desc())
        .all()
    )
    return render_template("learned.html", entries=entries)


@app.route("/learned/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_learned(entry_id):
    entry = LearnedEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        return "not found", 404
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for("learned"))


@app.route("/api/read-later", methods=["POST"])
@login_required
def api_read_later():
    payload = request.get_json(silent=True) or {}

    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify(error="missing title"), 400

    entry = ReadLaterEntry(
        user_id=current_user.id,
        title=title,
        url=payload.get("url"),
        genre=payload.get("genre"),
        words=payload.get("words"),
        note=(payload.get("note") or "").strip() or None,
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify(success=True, id=entry.id)


@app.route("/read-later")
@login_required
def read_later():
    entries = (
        ReadLaterEntry.query
        .filter_by(user_id=current_user.id)
        .order_by(ReadLaterEntry.created_at.desc())
        .all()
    )
    return render_template("read_later.html", entries=entries)


@app.route("/read-later/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_read_later(entry_id):
    entry = ReadLaterEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        return "not found", 404
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for("read_later"))


if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)