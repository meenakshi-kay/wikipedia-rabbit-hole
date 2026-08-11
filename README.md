# the archive

A Flask web app that pulls random-but-substantial Wikipedia articles by topic,
and lets you keep a personal "learned" shelf with your own rating, keywords,
and reflections. SQLite database via SQLAlchemy, no external services needed.

## Setup

```bash
cd wiki_app
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Then open **http://127.0.0.1:5000** in your browser.

A `library.db` SQLite file will be created automatically in this folder on
first run — that's where seen titles and your "learned" entries live.

## How it's structured

- `app.py` : Flask routes (`/`, `/api/find`, `/api/learn`, `/learned`, delete)
- `models.py` : SQLAlchemy models: `SeenTitle`, `LearnedEntry`
- `wiki_client.py` :talks to the Wikipedia API (this is where genres/search
  terms live, and the speed-critical fetching logic)
- `templates/` : Jinja2 templates
- `static/css/style.css`, `static/js/app.js`

## Why it's fast now

The old desktop version made one API request per search result title (up to
~11 requests per attempt) with a hard sleep before each one. This version:

- Uses `generator=search` so a single request returns both the search
  results *and* their article extracts together.
- Reuses one `requests.Session` (keep-alive connection) instead of opening a
  new connection per request.
- Retries transient failures/429s automatically at the HTTP layer via
  `urllib3.Retry`, respecting Wikipedia's `Retry-After` header, instead of
  manual blanket sleeps.

Typical searches should now finish in a couple of seconds. The UI shows a
live elapsed timer while searching, and "found in X.Xs" once it lands, so
you can see this for yourself.

## Notes

- `MIN_WORDS` and the per-genre search terms live at the top of
  `wiki_client.py` if you want to tune them.
- Shown articles are recorded in `SeenTitle` so you won't get repeats across
  sessions, regardless of whether you mark them "learned."
