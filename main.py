#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Blogger feeder:
- Each UTC day, pick 2 random categories from a fixed list (deterministic per day).
- For each category, generate a punchy French clickbait title (<= 70 chars)
  and a fully SEO-optimized HTML article for Blogger (no <html>/<body> wrapper).
- Strong formatting: line breaks between headings & paragraphs, bullet lists,
  bold/italic, inline code, occasional color spans, callouts, CTA.
- Prevent duplicates: keep a JSON history of previously used titles and skip/regenerate.
- Email each article to Blogger (subject = generated title).

ENV required:
  BLOGGER_SECRET_MAIL : blogger post-by-email address
  GMAIL_USER          : Gmail username (sender)
  GMAIL_PASS          : Gmail app password (NOT your regular password)
  GEMINI_API_KEY      : Google Generative AI key

Optional ENV:
  GEMINI_MODEL        : default "gemini-2.5-flash"
  HISTORY_FILE        : default ".data/blog_history.json"
  ARTICLES_PER_DAY    : default 2
  MAX_RETRIES_TITLE   : default 5
"""

import os
import ssl
import smtplib
import json
import random
import hashlib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import google.generativeai as genai

# ---------------------- CONFIG ------------------------------------
BLOGGER_MAIL = os.environ["BLOGGER_SECRET_MAIL"]
GMAIL_USER   = os.environ["GMAIL_USER"]
GMAIL_PASS   = os.environ["GMAIL_PASS"]

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

HISTORY_FILE = os.getenv("HISTORY_FILE", ".data/blog_history.json")
ARTICLES_PER_DAY = int(os.getenv("ARTICLES_PER_DAY", "2"))
MAX_RETRIES_TITLE = int(os.getenv("MAX_RETRIES_TITLE", "5"))

CATEGORIES = [
    "Sécurité informatique et protection des données",
    "Astuces et productivité",
    "Maintenance et dépannage",
    "Programmation et développement",
    "Cloud, stockage et synchronisation",
    "Android et iOS – Astuces",
    "Bureautique et outils",
    "Création de contenu et multimédia",
    "Internet et navigation",
    "Cybersécurité avancée",
    "Technologie et projets DIY",
    "Outils et services en ligne",
    "Formation et apprentissage",
    "Hacking Éthique & Sécurité",
    "Programmation & Scripts de Sécurité",
    "OSINT (Open Source Intelligence)",
    "Pentesting Réseau",
    "Sécurité Web & Bypass",
    "Sécurité Mobile & Android",
    "Dark Web & Anonymat",
    "Cyberdéfense & Prévention",
    "Hacking Éthique Avancé",
    "Divers & Automatisation",
]

# ---------------------- UTILS -------------------------------------
def ensure_history_path(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def load_history(path: str):
    ensure_history_path(path)
    if not os.path.exists(path):
        return {"titles": [], "days": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"titles": [], "days": {}}

def save_history(path: str, data: dict):
    ensure_history_path(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def title_in_history(title: str, history: dict) -> bool:
    # Normalize by lowercasing and hashing to be resilient
    norm = title.strip().lower()
    h = hashlib.sha1(norm.encode("utf-8")).hexdigest()
    return h in history.get("titles", [])

def add_title_to_history(title: str, history: dict):
    norm = title.strip().lower()
    h = hashlib.sha1(norm.encode("utf-8")).hexdigest()
    if "titles" not in history:
        history["titles"] = []
    if h not in history["titles"]:
        history["titles"].append(h)

def pick_daily_categories(today_utc: datetime, k: int) -> list:
    # Deterministic per-date sample using seed = YYYY-MM-DD
    seed = today_utc.strftime("%Y-%m-%d")
    rng = random.Random(seed)
    return rng.sample(CATEGORIES, k=min(k, len(CATEGORIES)))

# ---------------------- MAIL --------------------------------------
def mail_post(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = BLOGGER_MAIL
    msg.attach(MIMEText(html_body, "html"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, BLOGGER_MAIL, msg.as_string())

# ---------------------- AI PROMPTS --------------------------------
def gen_punchy_title_and_meta(category: str):
    """
    Returns (title, meta_desc). Both in French.
    Title <= 70 chars, no quotes, 1 leading emoji.
    """
    prompt = f"""
Tu es un rédacteur SEO en 2025. Crée pour la catégorie suivante un SEUL titre
percutant et “clickbait” en français (max 70 caractères), commençant par UN seul emoji.
Puis une méta description unique (max 155 caractères).

Catégorie: {category}

Renvoie STRICTEMENT au format JSON:
{{"title": "...", "meta": "..."}}
"""
    model = genai.GenerativeModel(MODEL)
    out = model.generate_content(prompt).text.strip()
    # Best effort parse JSON without external libs
    import re, json as pyjson
    m = re.search(r'\{.*\}', out, re.S)
    if not m:
        # Fallback minimal
        return ("✨ " + category.split("–")[0].strip(), "Découvrez nos conseils essentiels.")
    try:
        data = pyjson.loads(m.group(0))
        title = data.get("title","").strip().strip('"')
        meta  = data.get("meta","").strip()
        if not title:
            title = "✨ " + category.split("–")[0].strip()
        return (title, meta[:155])
    except Exception:
        return ("✨ " + category.split("–")[0].strip(), "Découvrez nos conseils essentiels.")

def gen_full_article_html(category: str, title: str, meta_desc: str):
    """
    Generate rich Blogger-ready HTML in French with strong formatting and SEO.
    """
    keyword = category.lower()
    prompt = f"""
Rédige un article de blog en FRANÇAIS pour Blogger (HTML uniquement, sans <html> ni <body>).

Contexte:
- Catégorie: {category}
- Titre: {title}
- Meta description: {meta_desc}

Exigences SEO & mise en forme:
- Longueur: 800–1200 mots
- Première ligne EXACTE: <p class='meta'>{meta_desc}</p>
- Titre H1: <h1>{title}</h1>
- TOC ancré: <nav id='toc'> avec liens vers CHAQUE H2 (ancres id)
- Structure: H2 (sections), H3 (sous-sections)
- Laisse une LIGNE BLANCHE entre chaque titre et chaque paragraphe
- Utilise des listes à puces (ul/li) quand pertinent
- Mets en valeur avec <strong>, <em>, et du monospace <code> pour commandes/extraits
- Ajoute quelques touches de couleur pertinentes via <span style="color:#2363eb">…</span> (modéré)
- Ajoute 1–2 encadrés “conseil/alerte” avec <blockquote class="tip"> et <blockquote class="warning">
- Inclure 1 court extrait de code pertinent (3–8 lignes) si la catégorie s’y prête (entre balises <pre><code>)
- Ajoute un CTA final (inscription newsletter / partage / commentaire)
- Pas d’images externes dans cet article
- Pas d’auto-promo, pas de répétition inutile
- Français naturel, ton professionnel et pédagogique

Renvoie UNIQUEMENT le HTML.
"""
    model = genai.GenerativeModel(MODEL)
    html = model.generate_content(prompt).text.strip()
    # Nettoyage éventuel de ```html ... ```
    if html.startswith("```html"):
        html = html[7:]
    if html.endswith("```"):
        html = html[:-3]
    return html

# ---------------------- MAIN --------------------------------------
def main():
    today_utc = datetime.now(timezone.utc)
    today_key = today_utc.strftime("%Y-%m-%d")

    history = load_history(HISTORY_FILE)
    if "days" not in history:
        history["days"] = {}

    # Choisir 2 catégories du jour, de manière déterministe
    chosen = pick_daily_categories(today_utc, ARTICLES_PER_DAY)

    # Optionnel: si vous voulez éviter de republier les mêmes catégories deux jours de suite,
    # vous pouvez décommenter ce bloc pour re-tirer si identique à la veille.
     yesterday_key = (today_utc - timedelta(days=1)).strftime("%Y-%m-%d")
    if yesterday_key in history.get("days", {}):
         ycats = set(history["days"][yesterday_key])
         if set(chosen) == ycats:
             # prenez les 2 suivantes dans un mélange fixe
             rng = random.Random(today_key + "-alt")
             pool = [c for c in CATEGORIES if c not in ycats]
             if len(pool) >= ARTICLES_PER_DAY:
                 chosen = rng.sample(pool, ARTICLES_PER_DAY)

    posted_today = []
    for category in chosen:
        # 1) Générer titre + meta, avec tentatives pour éviter doublons
        title, meta = gen_punchy_title_and_meta(category)

        tries = 0
        while title_in_history(title, history) and tries < MAX_RETRIES_TITLE:
            tries += 1
            title, meta = gen_punchy_title_and_meta(category)

        # Si encore en doublon après N essais, skip cette catégorie
        if title_in_history(title, history):
            print(f"[SKIP] Titre déjà utilisé pour '{category}': {title}")
            continue

        # 2) Générer l'article HTML
        html = gen_full_article_html(category, title, meta)

        # 3) Envoyer l'email (sujet = titre)
        mail_post(title, html)

        # 4) Marquer comme publié (anti-doublon futur)
        add_title_to_history(title, history)
        posted_today.append(category)
        print(f"[OK] Publié: {title} ({category})")

    # Mémoriser les catégories du jour (info)
    history["days"][today_key] = posted_today
    save_history(HISTORY_FILE, history)

if __name__ == "__main__":
    main()
