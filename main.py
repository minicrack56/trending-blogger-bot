#!/usr/bin/env python3
"""
SEO-ready blog posts with catchy titles, TOC, emojis, images.
Uses Google Gemini and embeds **all images in the exact order**
they appear in the original article.
"""
import os
import ssl
import smtplib
import re
from urllib.parse import urljoin
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import feedparser
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# ---------- CONFIG -------------------------------------------------
BLOGGER_MAIL = os.environ["BLOGGER_SECRET_MAIL"]
GMAIL_USER   = os.environ["GMAIL_USER"]
GMAIL_PASS   = os.environ["GMAIL_PASS"]

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"

SECTIONS = {
    "Sport":        "https://feeds.bbci.co.uk/sport/rss.xml",
    "Healthcare":   "https://feeds.bbci.co.uk/news/health/rss.xml",
    "Finance":      "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Technology":   "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "News world":"https://feeds.bbci.co.uk/news/world/rss.xml"
}

# -------------------------------------------------------------------

def top_articles(url, limit=1):
    feed = feedparser.parse(url)
    return [
        {"title": e.title, "link": e.link, "summary": e.get("summary", "")}
        for e in feed.entries[:limit]
    ]

from playwright.sync_api import sync_playwright

def extract_images_and_text(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, "lxml")

    # strip clutter
    for tag in soup(["script", "style", "nav", "aside", "footer", "header"]):
        tag.decompose()

    flow = []

    # walk every <p> and every <img>/<picture>
    for el in soup.find_all(["p", "img", "picture"]):
        if el.name == "p":
            txt = el.get_text(" ", strip=True)
            if len(txt) > 30:
                flow.append({"type": "text", "payload": txt})
        else:  # img or picture
            img = el.find("img") if el.name == "picture" else el
            if img:
                # try every possible lazy attribute
                src = (
                    img.get("src")
                    or img.get("data-src")
                    or img.get("data-lazy-src")
                    or img.get("data-original")
                    or img.get("srcset", "").split()[0]  # first in srcset
                )
                if src and src.startswith("http") and "1x1" not in src:
                    flow.append({"type": "img", "payload": src})

    return flow

def build_clickbait_title(original, vertical):
    prompt = f"""
Rewrite the headline below in french into a punchy, click-magnet title (max 70 chars).
Add one emoji at the start. Keep keywords if necessary. choose and use only one punchy headline per articles.

Headline: {original}
Vertical: {vertical}
"""
    model = genai.GenerativeModel(MODEL)
    return model.generate_content(prompt).text.strip().strip('"')

def write_seo_post(vertical, article):
    flow = extract_images_and_text(article["link"])
    title = build_clickbait_title(article["title"], vertical)
    keyword = vertical.lower()

    # Build plaintext for Gemini context
    text_only = " ".join([f["payload"] for f in flow if f["type"] == "text"])[:1000]
    img_urls  = [f["payload"] for f in flow if f["type"] == "img"]

    prompt = f"""
You are an SEO copywriter in 2025. Re-write the following article as HTML for Blogger post in French.

Rules:
- 400-800 words
- Start with <p class='meta'>META-DESC (max 155 chars)</p>
- Always use line breaks/space between paragraphs and headings must be separe by a line break.
- Use H2/H3 headings with emojis
- Space out the text where necessary to make it more readable.
- Reproduce the exact order of paragraphs & images
- For every img URL insert:
  <img src="URL" alt="{keyword}" width="800" height="450" style="border-radius:8px;">
- Add TOC <nav id='toc'> with jump-links to each H2
- Bullet lists ✅, bold/italic or color for emphasis
- End with a call-to-action
- Cite: <a href='{article["link"]}'>original article</a>

Plain text snippets:
{text_only}

Images in order:
{img_urls}
"""
    model = genai.GenerativeModel(MODEL)
    html = model.generate_content(prompt).text
    if html.startswith("```html"):
        html = html[7:-4]
    return html

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

def main():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    for vertical, rss_url in SECTIONS.items():
        for article in top_articles(rss_url, limit=1):
            body = write_seo_post(vertical, article)
            subject = build_clickbait_title(article["title"], vertical)
            mail_post(subject, body)

if __name__ == "__main__":
    main()
