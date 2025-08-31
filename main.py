#!/usr/bin/env python3
"""
Create 5 SEO posts (one per vertical) using trending articles
and DeepSeek via OpenRouter, then mail them to Blogger.
"""
import os
import ssl
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import feedparser
import openai
import requests
from bs4 import BeautifulSoup

# ---------- CONFIG -------------------------------------------------
BLOGGER_MAIL = os.environ["BLOGGER_SECRET_MAIL"]
GMAIL_USER   = os.environ["GMAIL_USER"]
GMAIL_PASS   = os.environ["GMAIL_PASS"]
OPENROUTER_KEY = os.environ["OPENROUTER_API_KEY"]

# OpenRouter endpoint & DeepSeek model
openai.api_key = OPENROUTER_KEY
openai.api_base = "https://openrouter.ai/api/v1"
MODEL = "deepseek/deepseek-chat"  # or deepseek/deepseek-r1:free

# Google News RSS for each vertical
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

def fetch_text(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
        return " ".join(paragraphs)[:800]
    except Exception:
        return ""

def write_seo_post(vertical, article):
    prompt = f"""
You are an experienced SEO copywriter.
Write a 300–400 word, unique blog post in French about the following trending news.
Include the keyword "{vertical.lower()}" naturally 2–3 times.
Add a catchy meta-description (max 155 chars) at the top in <p class='meta'></p>.
Use H2 for the headline and H3 for sub-headings.
Cite the original source with a link.

Title: {article['title']}
Source URL: {article['link']}
Snippet: {article['summary']}
Body preview: {fetch_text(article['link'])}
"""
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        headers={
            "HTTP-Referer": f"https://github.com/{os.getenv('GITHUB_REPOSITORY', 'user/repo')}",
            "X-Title": "Trending-Blogger-Bot"
        }
    )
    return response.choices[0].message.content.strip()

def mail_post(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = BLOGGER_MAIL
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, BLOGGER_MAIL, msg.as_string())

def main():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    for vertical, rss_url in SECTIONS.items():
        articles = top_articles(rss_url, limit=1)
        if not articles:
            continue
        art = articles[0]
        body = write_seo_post(vertical, art)
        mail_post(f"{vertical} Hot Take – {today}", body)

if __name__ == "__main__":
    main()