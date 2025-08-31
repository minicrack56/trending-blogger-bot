#!/usr/bin/env python3
"""
Pull top-5 daily searches for 5 verticals and mail them to Blogger.
"""
import os, ssl, smtplib, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import feedparser
from pytrends.request import TrendReq

# CONFIG -------------------------------------------------
BLOGGER_MAIL = os.environ["BLOGGER_SECRET_MAIL"]
GMAIL_USER   = os.environ["GMAIL_USER"]
GMAIL_PASS   = os.environ["GMAIL_PASS"]
SPORT_ID     = "20"
HEALTH_ID    = "45"
FINANCE_ID   = "12"
TECH_ID      = "5"
FOOD_ID      = "71"
# --------------------------------------------------------

def top_queries(cat_id):
    """Return top 5 rising queries from Google Trends RSS for a category."""
    url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo=US&cat={cat_id}"
    feed = feedparser.parse(url)
    return [e.title for e in feed.entries][:5]

def build_html():
    today = datetime.date.today().strftime("%Y-%m-%d")
    html = f"<h1>🔥 Top Searches for {today}</h1>"
    for name, cat in [
        ("🏀 Sport", SPORT_ID),
        ("💊 Healthcare", HEALTH_ID),
        ("💰 Finance", FINANCE_ID),
        ("🤖 Technology", TECH_ID),
        ("🍔 Food Industry", FOOD_ID),
    ]:
        html += f"<details><summary><strong>{name}</strong></summary><ol>"
        html += "".join(f"<li>{q}</li>" for q in top_queries(cat))
        html += "</ol></details><br>"
    return html

def send_mail(html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily Trending Search Digest – {datetime.date.today()}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = BLOGGER_MAIL
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, BLOGGER_MAIL, msg.as_string())

if __name__ == "__main__":
    send_mail(build_html())
