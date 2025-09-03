#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Blogger feeder with history:
- Picks 2 categories per UTC day sequentially
- Loops back to top when reaching the end
- Generates punchy French clickbait titles and unique meta descriptions
- Ensures unique articles per loop
- Prevents duplicates using .data/blog_history.json
- Emails each article to Blogger
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

# ---------------- CONFIG ----------------
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

# ---------------- HISTORY HANDLING ----------------
def ensure_history_path(path: str):
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

def load_history(path: str):
    ensure_history_path(path)
    if not os.path.exists(path):
        return {"titles": [], "days": {}, "cat_index": 0, "category_loops": {}}
    try:
        return json.load(open(path, "r", encoding="utf-8"))
    except Exception:
        return {"titles": [], "days": {}, "cat_index": 0, "category_loops": {}}

def save_history(path: str, data: dict):
    ensure_history_path(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def title_in_history(title: str, history: dict) -> bool:
    h = hashlib.sha1(title.strip().lower().encode("utf-8")).hexdigest()
    return h in history.get("titles", [])

def add_title_to_history(title: str, history: dict):
    h = hashlib.sha1(title.strip().lower().encode("utf-8")).hexdigest()
    if "titles" not in history:
        history["titles"] = []
    if h not in history["titles"]:
        history["titles"].append(h)

# ---------------- MAIL ----------------
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

# ---------------- AI PROMPTS ----------------
def gen_punchy_title_and_meta(category: str, loop_index: int = 0):
    prompt = f"""
Tu es un rédacteur SEO en 2025. Crée pour la catégorie suivante un SEUL titre
percutant et “clickbait” en français (max 70 caractères), commençant par UN seul emoji.
Puis une méta description unique (max 155 caractères).

Catégorie: {category}
C'est la {loop_index+1}ᵉ fois que nous écrivons sur cette catégorie,
donne un angle et un texte UNIQUE, différent des fois précédentes.

Renvoie STRICTEMENT au format JSON:
{{"title": "...", "meta": "..."}}
"""
    model = genai.GenerativeModel(MODEL)
    out = model.generate_content(prompt).text.strip()
    import re, json as pyjson
    m = re.search(r'\{.*\}', out, re.S)
    if not m:
        return ("✨ " + category.split("–")[0].strip(), "Découvrez nos conseils essentiels.")
    try:
        data = pyjson.loads(m.group(0))
        title = data.get("title","").strip().strip('"')
        meta  = data.get("meta","").strip()[:155]
        if not title:
            title = "✨ " + category.split("–")[0].strip()
        return title, meta
    except Exception:
        return ("✨ " + category.split("–")[0].strip(), "Découvrez nos conseils essentiels.")

def gen_full_article_html(category: str, title: str, meta_desc: str, loop_index: int = 0):
    prompt = f"""
Rédige un article de blog en FRANÇAIS pour Blogger (HTML uniquement, sans <html> ni <body>).

Contexte:
- Catégorie: {category}
- Titre: {title}
- Meta description: {meta_desc}
- C'est la {loop_index+1}ᵉ fois que nous écrivons sur cette catégorie,
  propose un angle DIFFÉRENT des fois précédentes et un contenu UNIQUE.

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
- Interdiction de répéter mot pour mot les versions précédentes
"""
    model = genai.GenerativeModel(MODEL)
    html = model.generate_content(prompt).text.strip()
    if html.startswith("```html"):
        html = html[7:]
    if html.endswith("```"):
        html = html[:-3]
    return html

# ---------------- MAIN ----------------
def main():
    today_utc = datetime.now(timezone.utc)
    today_key = today_utc.strftime("%Y-%m-%d")

    history = load_history(HISTORY_FILE)
    if "days" not in history:
        history["days"] = {}
    if "cat_index" not in history:
        history["cat_index"] = 0
    if "category_loops" not in history:
        history["category_loops"] = {}

    start_idx = history["cat_index"]
    chosen = []
    for i in range(ARTICLES_PER_DAY):
        idx = (start_idx + i) % len(CATEGORIES)
        chosen.append(CATEGORIES[idx])
    history["cat_index"] = (start_idx + ARTICLES_PER_DAY) % len(CATEGORIES)

    posted_today = []

    for category in chosen:
        loop_index = history["category_loops"].get(category, 0)

        title, meta = gen_punchy_title_and_meta(category, loop_index)
        tries = 0
        while title_in_history(title, history) and tries < MAX_RETRIES_TITLE:
            tries += 1
            title, meta = gen_punchy_title_and_meta(category, loop_index)
        if title_in_history(title, history):
            print(f"[SKIP] Titre déjà utilisé pour '{category}': {title}")
            continue

        html = gen_full_article_html(category, title, meta, loop_index)
        mail_post(title, html)
        add_title_to_history(title, history)
        posted_today.append(category)

        history["category_loops"][category] = loop_index + 1

        print(f"[OK] Publié: {title} ({category}, loop {loop_index+1})")

    history["days"][today_key] = posted_today
    save_history(HISTORY_FILE, history)

if __name__ == "__main__":
    main()
