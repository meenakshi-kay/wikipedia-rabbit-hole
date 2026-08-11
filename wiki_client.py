"""
Talks to Wikipedia. The key speed fix vs the old version: instead of doing
a search request and then one extract request PER title (up to 11 requests
per attempt), this uses generator=search to fetch the search results AND
their extracts in a single HTTP request. Combined with a reused Session
(keep-alive) and automatic retry/backoff at the HTTP layer, a full search
across several genre terms is normally a handful of requests total instead
of dozens.
"""
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = "https://en.wikipedia.org/w/api.php"
MIN_WORDS = 500
MAX_TERM_ATTEMPTS = 6
REQUEST_TIMEOUT = 10

HEADERS = {
    "User-Agent": "RandomTopicGenerator/2.0 personal learning project"
}

GENRES = {
    "history": [
        "ancient civilization", "medieval history", "historical battle",
        "lost city", "archaeological discovery", "historical figure",
        "empire", "revolution", "history",
    ],
    "literature": [
        "novel", "poetry", "literary movement", "epic poem",
        "gothic literature", "banned book", "literary magazine", "historical literature",
    ],
    "physics": [
        "quantum mechanics", "thermodynamics", "particle physics",
        "astrophysics", "condensed matter physics", "physics experiment", "physics",
    ],
    "biology": [
        "evolution", "genetics", "microorganism", "marine biology",
        "extinct species", "symbiosis", "biology", "cell biology",
    ],
    "chemistry": [
        "organic chemistry", "chemical compound", "chemical reaction",
        "materials science", "biochemistry", "alchemy", "chemistry",
    ],
    "computer science": [
        "algorithm", "programming language", "computer architecture",
        "cryptography", "artificial intelligence", "early computer", "computer",
    ],
    "math": [
        "number theory", "geometry", "topology", "mathematical paradox",
        "mathematician", "combinatorics", "mathematics",
    ],
    "space": [
        "astronomy", "space exploration", "exoplanet", "space telescope",
        "space mission", "black hole", "galaxy", "astrophysics",
    ],
    "engineering": [
        "aerospace engineering", "mechanical engineering", "electronics engineering",
        "structural failure", "engineering design", "robotics",
    ],
    "psychology": [
        "memory", "cognitive science", "psychological phenomenon",
        "behavioral psychology", "perception", "neuroscience", "psychology", "mental health",
    ],
    "mythology": [
        "greek mythology", "norse mythology", "folklore", "legendary creature",
        "creation myth", "mythological hero", "roman mythology", "mythology",
    ],
    "geography": [
        "river", "mountain", "island", "desert", "geological formation",
        "extreme environment",
    ],
    "random": [
        "unusual phenomenon", "mystery", "oddity", "unsolved mystery",
        "unusual event", "anomaly",
    ],
}

# One session, reused for every call: keeps the TCP/TLS connection alive
# instead of renegotiating it on every request, and retries transient
# failures / 429s automatically (respecting Wikipedia's Retry-After header).
_session = requests.Session()
_session.headers.update(HEADERS)
_retry = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    respect_retry_after_header=True,
    allowed_methods=frozenset(["GET"]),
)
_session.mount("https://", HTTPAdapter(max_retries=_retry))


def _get(params):
    response = _session.get(API, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _search_and_extract(term, offset=0):
    """One request: gets up to 20 search results for `term` AND their
    extracts, using search-as-generator."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": term,
        "gsrlimit": 20,
        "gsroffset": offset,
        "prop": "extracts|info",
        "explaintext": True,
        "exlimit": "max",
        "redirects": True,
        "inprop": "url",
        "format": "json",
    }
    data = _get(params)
    pages = data.get("query", {}).get("pages", {})

    candidates = []
    for page in pages.values():
        if "missing" in page:
            continue

        title = page.get("title", "")
        extract = page.get("extract", "").strip()
        url = page.get("fullurl", "")
        words = len(extract.split())

        if not title or not extract:
            continue
        if title.lower().startswith("list of"):
            continue
        if "(disambiguation)" in title.lower():
            continue
        if words < MIN_WORDS:
            continue

        candidates.append({"title": title, "url": url, "words": words})

    return candidates


def find_article(genre, seen_titles):
    """Returns a dict {title, url, words, genre, search_term} or None."""
    if genre not in GENRES:
        raise ValueError(f"unknown genre: {genre}")

    terms = list(GENRES[genre])
    random.shuffle(terms)

    for term in terms[:MAX_TERM_ATTEMPTS]:
        offset = random.choice([0, 0, 20, 40, 60])
        candidates = _search_and_extract(term, offset=offset)

        if not candidates and offset != 0:
            candidates = _search_and_extract(term, offset=0)
        if not candidates:
            continue

        fresh = [a for a in candidates if a["title"] not in seen_titles]
        pool = fresh if fresh else candidates  # allow repeats if everything's been seen

        article = random.choice(pool)
        article["genre"] = genre
        article["search_term"] = term
        return article

    return None
