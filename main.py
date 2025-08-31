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
    "Sport":        "https://news.google.com/rss/search?q=category:sports&hl=en-US&gl=US",
    "Healthcare":   "https://news.google.com/rss/search?q=category:health&hl=en-US&gl=US",
    "Finance":      "https://news.google.com/rss/search?q=category:business&hl=en-US&gl=US",
    "Technology":   "https://news.google.com/rss/search?q=category:technology&hl=en-US&gl=US",
    "Food Industry":"https://news.google.com/rss/search?q=food%20industry&hl=en-US&gl=US"
}
# -------------------------------------------------------------------

def top_articles(url, limit=1):
    feed = feedparser.parse(url)
    return [
        {"title": e.title, "link": e.link, "summary": e.get("summary", "")}
        for e in feed.entries[:limit]
    ]

def extract_images_and_text(url):
    """
    Walk the source page and return ordered list of
    {'type':'text'|'img', 'payload': str}
    """
    r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    # Remove non-content tags
    for tag in soup(["script", "style", "nav", "aside", "footer"]):
        tag.decompose()

    flow = []
    for el in soup.find_all(["p", "img"]):
        if el.name == "p":
            txt = el.get_text(strip=True)
            if txt:
                flow.append({"type": "text", "payload": txt})
        elif el.name == "img":
            src = el.get("src") or el.get("data-src")
            if src:
                src = urljoin(url, src)
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
You are an SEO copywriter. Re-write the following article as **HTML** for Blogger in French.

Rules:
- 400-800 words
- Start with <p class='meta'>META-DESC (max 155 chars)</p>
- Use H2/H3 headings with emojis
- Use line breaks between paragraphs and large sections.
- Space out the text where necessary to make it more readable.
- Reproduce the **exact order** of paragraphs & images
- For every img URL insert:
  <img src="URL" alt="{keyword}" width="800" height="450" style="border-radius:8px;">
- Add TOC <nav id='toc'> with jump-links to each H2
- Bullet lists ✅, bold/italic emphasis
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
