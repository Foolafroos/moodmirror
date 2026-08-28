"""Compréhension du contenu — 100% local, zéro API externe.

Trois niveaux selon ce qu'on a réellement sous la main :
- article/page web  → texte récupéré localement (urllib) + analyse de valence
                       par lexique sentiment (FR/EN), fonctionne hors-ligne
- vidéo (YouTube…)  → l'historique ne donne que URL + titre → analyse sur le
                       titre, confiance marquée "low" (on ne fabrique rien)
- tweet/X          → lecture bloquée sans auth → marque "low confidence"

Bonus optionnel : si LM Studio expose un modèle (http://localhost:1234),
analyse plus riche (thème + résumé). Sinon fallback automatique sur lexique.
"""
from __future__ import annotations

import json
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Classification du contenu par URL
# ---------------------------------------------------------------------------

def classify_url(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "video"
    if "x.com" in host or "twitter.com" in host:
        return "tweet"
    if any(d in host for d in ("reddit.com", "news.ycombinator.com", "discord.gg")):
        return "forum"
    if any(d in host for d in ("instagram.com", "tiktok.com", "twitch.tv")):
        return "social-video"
    if any(d in host for d in ("wikipedia.org", "wiki.", "medium.com", "blog.", "news.")):
        return "article"
    return "web"


# ---------------------------------------------------------------------------
# Extraction de texte local (stdlib uniquement)
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer"}

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.chunks: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        elif self._skip_depth == 0 and data.strip():
            self.chunks.append(data.strip())


def fetch_text(url: str, timeout: int = 8) -> tuple[str | None, str | None]:
    """Récupère (texte, titre) d'une page localement. None si échec."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (MoodMirror local; +privacy-first)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(400_000).decode("utf-8", errors="replace")
    except Exception:
        return None, None
    p = _TextExtractor()
    try:
        p.feed(raw)
    except Exception:
        pass
    text = " ".join(p.chunks)[:4000] or None
    title = " ".join("".join(p.title_parts).split())[:300] or None
    return text, title


# ---------------------------------------------------------------------------
# Analyse de valence par lexique (FR + EN) — fonctionne hors-ligne
# ---------------------------------------------------------------------------

_POSITIVE = {
    # EN
    "good", "great", "excellent", "amazing", "wonderful", "beautiful", "love",
    "happy", "joy", "win", "won", "success", "successful", "brilliant", "fantastic",
    "impressive", "delight", "enjoy", "enjoyable", "calm", "peaceful", "hope",
    "hopeful", "optimistic", "inspiring", "motivating", "helpful", "useful",
    "relaxing", "comfort", "warm", "kind", "generous", "grateful", "thankful",
    "fun", "entertaining", "refreshing", "uplifting", "triumph", "celebrate",
    # FR
    "bien", "bon", "bonne", "magnifique", "merveilleux", "superbe", "beau",
    "belle", "heureux", "heureuse", "joie", "réussi", "réussite", "excellent",
    "excellente", "brillant", "brillante", "fantastique", "impressif", "délicieux",
    "délit", "plaire", "calme", "paisible", "espoir", "optimiste", "inspirant",
    "motivant", "utile", "apaisant", "confortable", "chaleureux", "gentil",
    "généreux", "reconnaissant", "amusant", "divertissant", "rafraîchissant",
    "triomphe", "célébrer", "réjouir", "ravir", "satisfait", "satisfaire",
}

_NEGATIVE = {
    # EN
    "bad", "terrible", "awful", "horrible", "hate", "angry", "anger", "sad",
    "sadness", "depressing", "depression", "loss", "lost", "fail", "failed",
    "failure", "disaster", "crisis", "war", "attack", "killed", "death", "dying",
    "fear", "scary", "anxiety", "anxious", "stress", "stressful", "pain", "hurt",
    "ugly", "stupid", "useless", "boring", "annoying", "frustrating", "disappointing",
    "disappointed", "worried", "worry", "guilt", "shame", "furious", "outrage",
    "scandal", "corruption", "collapse", "plague", "outbreak", "emergency",
    # FR
    "mal", "mauvais", "mauvaise", "terrible", "affreux", "horrible", "détester",
    "colère", "furieux", "triste", "tristesse", "déprimant", "dépression", "perte",
    "perdu", "échec", "échoué", "catastrophe", "crise", "guerre", "attaque",
    "tué", "mort", "mourir", "peur", "effrayant", "angoisse", "anxieux", "stress",
    "stressant", "douleur", "blessé", "laid", "stupid", "inutile", "ennuyeux",
    "agaçant", "frustrant", "décevant", "déçu", "inquiété", "souci", "culpabilité",
    "honte", "scandale", "corruption", "effondrement", "épidémie", "urgence",
}

_STOPWORDS = {
    # EN
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "it", "its", "this", "that", "these",
    "those", "you", "your", "we", "our", "they", "their", "he", "she", "his",
    "her", "i", "my", "me", "as", "at", "by", "from", "not", "no", "so", "if",
    # FR
    "le", "la", "les", "un", "une", "des", "et", "ou", "mais", "de", "du", "à",
    "au", "aux", "pour", "avec", "sans", "est", "sont", "était", "être", "ce",
    "cette", "ces", "il", "elle", "ils", "elles", "on", "je", "tu", "nous",
    "vous", "se", "sa", "son", "ses", "en", "y", "ne", "pas", "plus", "très",
    "comme", "que", "qui", "quoi", "dont", "où", "dans", "sur", "sous", "entre",
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zà-öø-ÿ]+(?:['’-][a-zà-öø-ÿ]+)*", text.lower())


def lexicon_valence(text: str) -> tuple[float, int, int]:
    """Retourne (valence -1..+1, nb_positifs, nb_negatifs)."""
    toks = _tokens(text)
    pos = sum(1 for t in toks if t in _POSITIVE)
    neg = sum(1 for t in toks if t in _NEGATIVE)
    total = pos + neg
    if total == 0:
        return 0.0, 0, 0
    return (pos - neg) / total, pos, neg


def extract_topic(text: str, top_n: int = 3) -> str | None:
    """Proxy de thème : mots les plus fréquents hors stop-words."""
    counts: dict[str, int] = {}
    for t in _tokens(text):
        if len(t) < 4 or t in _STOPWORDS:
            continue
        counts[t] = counts.get(t, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    return ", ".join(w for w, _ in top) if top else None


# ---------------------------------------------------------------------------
# Analyse optionnelle via LM Studio (local uniquement)
# ---------------------------------------------------------------------------

LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"


def llm_analyze(text: str, timeout: int = 60) -> dict | None:
    """Si un modèle est chargé dans LM Studio → analyse riche. Sinon None."""
    prompt = (
        "Analyse ce texte pour une app de bien-être numérique. "
        'Réponds UNIQUEMENT en JSON valide : {"valence": nombre entre -1 et 1, '
        '"theme": "un court thème", "resume": "une phrase max"}.\n\n'
        f"Texte :\n{text[:3000]}"
    )
    body = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 120,
        "temperature": 0.2,
    }).encode()
    req = urllib.request.Request(LMSTUDIO_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        content = data["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", content, re.DOTALL)
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# API publique du module
# ---------------------------------------------------------------------------

def analyze_content(url: str, title: str | None = None) -> dict:
    """Analyse un contenu vu. Retourne un dict prêt pour la table analyses."""
    kind = classify_url(url)
    meta: dict = {"kind": kind}

    if kind in ("tweet", "social-video"):
        # Lecture bloquée sans auth → on ne fabrique rien
        v, _, _ = lexicon_valence(title or "")
        return {
            "valence": v, "topic": None, "method": "title-only",
            "confidence": "low", "meta": meta, "text_excerpt": None,
        }

    text, fetched_title = (None, None)
    if kind in ("article", "web", "forum"):
        text, fetched_title = fetch_text(url)
    if title is None:
        title = fetched_title

    llm = None
    if text:
        llm = llm_analyze(text)

    if llm and isinstance(llm.get("valence"), (int, float)):
        return {
            "valence": max(-1.0, min(1.0, float(llm["valence"]))),
            "topic": llm.get("theme") or extract_topic(text),
            "method": "llm", "confidence": "high",
            "meta": {**meta, "resume": llm.get("resume")},
            "text_excerpt": text[:2000],
        }

    source_text = text or title or ""
    v, pos, neg = lexicon_valence(source_text)
    meta.update({"lex_pos": pos, "lex_neg": neg,
                 "fetch_failed": text is None and kind in ("article", "web")})
    return {
        "valence": v,
        "topic": extract_topic(text) if text else None,
        "method": "lexicon" if text else "title-only",
        "confidence": "medium" if text else "low",
        "meta": meta,
        "text_excerpt": (text or title)[:2000] if (text or title) else None,
    }
