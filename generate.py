#!/usr/bin/env python3
"""
Ibn Sina Hospital — Static Site Generator
Fetches data from Google Sheets, generates doctor pages, blog posts,
department pages, and sitemap. Runs on GitHub Actions.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import datetime
import hashlib
import html
import urllib.request
from pathlib import Path
from urllib.parse import quote

# ============================================================
# CONFIG
# ============================================================
SITE_URL = "https://ibnsinahospital.in"
HOST = "ibnsinahospital.in"
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "78ee931b79be4739af08e1e0b0af036f")
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

SHEETS = {
    "doctors":     "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ_H8Rgr6VOjrap91SR_3nbBQLVf7QOQOHqZSs-pT6SfoNpyHjpj-QD0nNtcHDr5ip439naZ0sTr62Y/pub?output=csv",
    "blog":        "https://docs.google.com/spreadsheets/d/e/2PACX-1vRyksX4tU5UEPKPVbRGUiCe7lXxS-Z0WqSgB1vghBBqEvddzZ9M5ZSMtvfoCFPXRZoLojgWjIEmbQH8/pub?output=csv",
    "departments": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSY7cmsIsfCzFSfe6Gf6wG-XWffYscBhXHqnFqv0RvwuqbG7kNnPG7eSmSaR_E-ztlY8qLkHZ2yuL-t/pub?output=csv",
    "gallery":     "https://docs.google.com/spreadsheets/d/e/2PACX-1vR3ipvIHQSd0uvYjhDFrlMhG7nF5J9FKMPxB60sb9mrGWd-PiiTrmeMwqhPEUOXn8KI-MPov0hbAjSu/pub?output=csv",
    "updates":     "https://docs.google.com/spreadsheets/d/e/2PACX-1vSZW6V9At9Nb8LCupYha92UshFV5P6sbSKAOJmDoaZR6IbZyFoJorhEyJPcq5zscDdTSC_B39-j1RW5/pub?output=csv",
}

STATIC_TOP_LEVEL_PAGES = [
    "",  # homepage
    "about.html",
    "services.html",
    "doctors.html",
    "gallery.html",
    "blog.html",
    "careers.html",
    "faq.html",
    "contact.html",
    "appointment.html",
    "insurance-pmjay.html",
    "health-checkup-packages.html",
    "service-areas.html",
]

LASTMOD_CACHE = Path("lastmod_cache.json")
TODAY = datetime.date.today().isoformat()

DEFAULT_IMAGE = "https://i.ibb.co/NgNyCQgf/8e1694fa3791.webp"
FAVICON = "https://i.ibb.co/NgNyCQgf/8e1694fa3791.webp"


# ============================================================
# HELPERS
# ============================================================
def slugify(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def title_case(text: str) -> str:
    return " ".join(w.capitalize() if w else "" for w in (text or "").
