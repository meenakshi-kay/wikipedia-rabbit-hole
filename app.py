import os


from flask import Flask, render_template, request, jsonify, redirect, url_for

from models import db, SeenTitle, LearnedEntry, ReadLaterEntry
import wiki_client

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "library.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def index():
    return render_template("index.html", genres=list(wiki_client.GENRES.keys()))


@app.route("/api/find", methods=["POST"])
def api_find():
    payload = request.get_json(silent=True) or {}
    genre = payload.get("genre")

    if genre not in wiki_client.GENRES:
        return jsonify(error="that's not a shelf I recognise."), 400

    seen = {row.title for row in SeenTitle.query.with_entities(SeenTitle.title).all()}

    try:
        article = wiki_client.find_article(genre, seen)
    except Exception as error:
        return jsonify(error=f"couldn't reach wikipedia: {error}"), 502

    if not article:
        return jsonify(error="couldn't find anything fresh on this shelf. try again?"), 404

    db.session.add(SeenTitle(title=article["title"], genre=genre))
    db.session.commit()

    return jsonify(article)


@app.route("/api/learn", methods=["POST"])
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


@app.route("/api/read-later", methods=["POST"])
def api_read_later():
    payload = request.get_json(silent=True) or {}

    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify(error="missing title"), 400

    entry = ReadLaterEntry(
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
def read_later():
    entries = ReadLaterEntry.query.order_by(ReadLaterEntry.created_at.desc()).all()
    return render_template("read_later.html", entries=entries)


@app.route("/read-later/<int:entry_id>/delete", methods=["POST"])
def delete_read_later(entry_id):
    entry = ReadLaterEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for("read_later"))

@app.route("/learned")
def learned():
    entries = LearnedEntry.query.order_by(LearnedEntry.created_at.desc()).all()
    return render_template("learned.html", entries=entries)


@app.route("/learned/<int:entry_id>/delete", methods=["POST"])
def delete_learned(entry_id):
    entry = LearnedEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for("learned"))


if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)
