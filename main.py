#!/usr/bin/env python3
"""
SEO-ready blog posts with catchy titles, TOC, emojis, images.
Uses Google Gemini via OpenRouter.
"""
import os, ssl, smtplib, textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import feedparser, requests, google.generativeai as genai
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
    return [{"title": e.title, "link": e.link, "summary": e.get("summary", "")}
            for e in feed.entries[:limit]]

def fetch_text(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        return " ".join(p.get_text(strip=True)
                        for p in soup.find_all("p") if p.get_text(strip=True))[:800]
    except Exception:
        return ""

def build_clickbait_title(original, vertical):
    """Turn a boring headline into a scroll-stopper."""
    prompt = f"""
Rewrite the headline below in french into a punchy, click-magnet title (max 70 chars).
Add one emoji at the start. Keep keywords.

Headline: {original}
Vertical: {vertical}
"""
    model = genai.GenerativeModel(MODEL)
    return model.generate_content(prompt).text.strip().strip('"')

def free_img(keyword):
    """Return a royalty-free Unsplash img for the keyword."""
    return f"https://picsum.photos/800/450?{keyword.replace(' ', '-')}"

def write_seo_post(vertical, article):
    title = build_clickbait_title(article["title"], vertical)
    keyword = vertical.lower()
    prompt = f"""
Write a fully-formatted HTML blog post for Blogger in French.

Requirements:
- 400-800 words
- Start with

META-DESC
(max 155 chars)
- Add a Table of Contents
with 3-4 jump links
- Use line breaks between paragraphs and large sections.
-Space out your text where necessary to make it more readable.
- Use H2 and H3 headings with emojis
- Bullet lists ✅
- Include 3 royalty-free image placeholders ()
- Internal link to "latest tech news" (#)
- Bold/italic for emphasis
- End with a call-to-action
- Cite source: original article

Topic: {article["title"]}
Snippet: {article["summary"]}
Body preview: {fetch_text(article["link"])}
Primary keyword: {keyword}
"""
    model = genai.GenerativeModel(MODEL)
    html = model.generate_content(prompt).text
    # Gemini sometimes wraps in ```html``` — strip it
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
            # Use the new punchy title as email subject
            subject = build_clickbait_title(article["title"], vertical)
            mail_post(subject, body)

if __name__ == "__main__":
    main()

