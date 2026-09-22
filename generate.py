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
    "",
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

SERVICE_AREA_PAGES = [
    "service-areas/hospital-in-budgam.html",
    "service-areas/hospital-in-srinagar.html",
    "service-areas/hospital-in-ganderbal.html",
    "service-areas/hospital-in-pulwama.html",
    "service-areas/hospital-in-baramulla.html",
    "service-areas/hospital-in-anantnag.html",
    "service-areas/hospital-in-shopian.html",
    "service-areas/hospital-in-kulgam.html",
    "service-areas/hospital-in-kupwara.html",
    "service-areas/hospital-in-bandipora.html",
    "service-areas/hospital-near-chadoora-beerwah-charar.html",
    "service-areas/hospital-near-ompora-railway-station.html",
    "service-areas/emergency-hospital-budgam.html",
    "service-areas/dialysis-hospital-budgam.html",
    "service-areas/pmjay-hospital-kashmir.html",
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
    return " ".join(w.capitalize() if w else "" for w in (text or "").split())


def clean_name(raw_name: str) -> str:
    name = (raw_name or "").strip().rstrip(".")
    name = re.sub(r"^dr\.?\s*", "", name, flags=re.IGNORECASE).strip()
    name = " ".join(w.capitalize() for w in name.split())
    return f"Dr. {name}" if name else "Doctor"


def escape(value) -> str:
    return html.escape(str(value if value is not None else ""))


def json_escape(value) -> str:
    """Escape a string for embedding inside a JSON string literal."""
    s = str(value if value is not None else "")
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    return s


def fetch_csv(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "IbnSina-SSG/3.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(content)))
    for row in rows:
        for k, v in list(row.items()):
            if isinstance(v, str):
                row[k] = v.strip()
    return rows


def load_lastmod_cache() -> dict:
    if LASTMOD_CACHE.exists():
        try:
            return json.loads(LASTMOD_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_lastmod_cache(cache: dict) -> None:
    LASTMOD_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_lastmod(url: str, content: str, cache: dict) -> str:
    h = content_hash(content)
    entry = cache.get(url)
    if entry and entry.get("hash") == h:
        return entry["lastmod"]
    cache[url] = {"hash": h, "lastmod": TODAY}
    return TODAY


# ============================================================
# PARTIALS
# ============================================================
def partial_head(title: str, description: str, canonical: str, image: str = DEFAULT_IMAGE,
                 is_article: bool = False, extra_jsonld: str = "", root: str = "") -> str:
    og_type = "article" if is_article else "website"
    return f'''<!DOCTYPE html>
<html lang="en-IN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#2d4a2b">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<link rel="canonical" href="{escape(canonical)}">

<link rel="icon" type="image/webp" href="{FAVICON}">
<link rel="apple-touch-icon" href="{FAVICON}">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://i.ibb.co" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Nunito:wght@400;500;600;700&display=swap" rel="stylesheet">

<link rel="stylesheet" href="{root}css/style.css">
<link rel="stylesheet" href="{root}css/department.css">

<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="Ibn Sina Hospital">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:url" content="{escape(canonical)}">
<meta property="og:image" content="{escape(image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="en_IN">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escape(title)}">
<meta name="twitter:description" content="{escape(description)}">
<meta name="twitter:image" content="{escape(image)}">
{extra_jsonld}
<script async src="https://www.googletagmanager.com/gtag/js?id=G-SM7YH3P83K"></script>
<script>
window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}
gtag('js',new Date());gtag('config','G-SM7YH3P83K');
</script>
<script>document.documentElement.dataset.version='{TODAY}';</script>
</head>
<body>
<a href="#main-content" class="skip-link">Skip to main content</a>
'''


def partial_header(active: str = "", root: str = "") -> str:
    def link(href: str, label: str, key: str) -> str:
        cls = "nav-link active" if active == key else "nav-link"
        aria = ' aria-current="page"' if active == key else ""
        return f'<li><a class="{cls}" href="{root}{href}"{aria}>{label}</a></li>'

    return f'''<header class="site-header" id="site-header">
<div class="header-inner container">
  <a class="logo" href="{root}index.html" aria-label="Ibn Sina Hospital home">
    <img class="logo-img" src="{FAVICON}" alt="" width="40" height="40" aria-hidden="true">
    <span class="logo-text">Ibn Sina <strong>Hospital</strong></span>
  </a>
  <nav class="main-nav" id="main-nav" aria-label="Main navigation">
    <ul class="nav-list">
      {link("index.html", "Home", "home")}
      {link("about.html", "About", "about")}
      {link("services.html", "Services", "services")}
      {link("health-checkup-packages.html", "Health Checkups", "checkups")}
      {link("doctors.html", "Doctors", "doctors")}
      {link("gallery.html", "Gallery", "gallery")}
      {link("insurance-pmjay.html", "PM-JAY", "pmjay")}
      {link("blog.html", "Blog", "blog")}
      {link("careers.html", "Careers", "careers")}
      {link("faq.html", "FAQ", "faq")}
      {link("contact.html", "Contact", "contact")}
    </ul>
  </nav>
  <div class="header-actions">
    <a href="tel:+919622552553" class="emergency-badge" aria-label="Call emergency: 9622552553">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6.62 10.79a15.05 15.05 0 006.59 6.59l2.2-2.2a1 1 0 011.01-.24 11.36 11.36 0 003.58.57 1 1 0 011 1V20a1 1 0 01-1 1A17 17 0 013 4a1 1 0 011-1h3.5a1 1 0 011 1 11.36 11.36 0 00.57 3.58 1 1 0 01-.25 1.01l-2.2 2.2z"/></svg>
      <span>9622552553</span>
    </a>
    <a href="{root}appointment.html" class="btn btn-primary btn-book">Book Appointment</a>
    <button class="hamburger" id="hamburger" type="button" aria-label="Toggle navigation menu" aria-expanded="false" aria-controls="main-nav">
      <span class="hamburger-line"></span>
      <span class="hamburger-line"></span>
      <span class="hamburger-line"></span>
    </button>
  </div>
</div>
</header>
'''


def partial_footer(root: str = "") -> str:
    return f'''<footer class="site-footer">
<div class="container">
  <div class="footer-main">
    <div class="footer-col">
      <h3 class="footer-logo">Ibn Sina <strong>Hospital</strong></h3>
      <address>
        Near Railway Station, Ompora Railway Station Road,<br>
        Ompora, Budgam, Jammu &amp; Kashmir 191111
      </address>
      <p><a href="tel:+919622552553">📞 9622552553 / 9419023501</a></p>
      <p><a href="mailto:weibnsina@gmail.com">✉ weibnsina@gmail.com</a></p>
      <p class="footer-service-areas">
        <strong>Service Areas:</strong> Budgam, Srinagar, Ompora, Ganderbal,
        Pulwama, Shopian, Kulgam — across <strong>Jammu &amp; Kashmir</strong>
      </p>
    </div>
    <div class="footer-col">
      <h4>Quick Links</h4>
      <ul class="footer-links">
        <li><a href="{root}about.html">About Us</a></li>
        <li><a href="{root}services.html">Services</a></li>
        <li><a href="{root}doctors.html">Doctors</a></li>
        <li><a href="{root}health-checkup-packages.html">Health Checkups</a></li>
        <li><a href="{root}insurance-pmjay.html">PM-JAY / Insurance</a></li>
        <li><a href="{root}blog.html">Health Blog</a></li>
        <li><a href="{root}service-areas.html">Service Areas</a></li>
        <li><a href="{root}careers.html">Careers</a></li>
        <li><a href="{root}faq.html">FAQ</a></li>
        <li><a href="{root}contact.html">Contact</a></li>
      </ul>
    </div>
    <div class="footer-col">
      <h4>OPD &amp; Emergency</h4>
      <p><strong>OPD, Pharmacy, Lab &amp; Emergency:</strong><br>Open 24/7, 365 days</p>
      <div class="social-icons">
        <a class="social-icon" href="https://www.facebook.com/share/1HSWNC9UEy/" target="_blank" rel="noopener" aria-label="Facebook">FB</a>
        <a class="social-icon" href="https://www.instagram.com/ibn_sinahospital" target="_blank" rel="noopener" aria-label="Instagram">IG</a>
        <a class="social-icon" href="https://youtube.com/@ibnsinahospitalkashmir" target="_blank" rel="noopener" aria-label="YouTube">YT</a>
      </div>
    </div>
  </div>
  <div class="footer-bottom">
    <p>&copy; {datetime.date.today().year} Ibn Sina Hospital. All rights reserved. Operating since 2018.</p>
    <p><a href="https://maps.google.com/?q=IBN+SINA+HOSPITAL+Ompora+Budgam" target="_blank" rel="noopener">Find us on Google Maps →</a></p>
  </div>
</div>
</footer>
'''


def partial_scripts(root: str = "") -> str:
    return f'''<a href="https://wa.me/919622552553" class="floating-whatsapp" target="_blank" rel="noopener" aria-label="Chat on WhatsApp">
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
</a>
<script src="{root}js/main.js" defer></script>
<script src="{root}js/chatbot.js" defer></script>
</body>
</html>'''


# ============================================================
# DEPARTMENT CONTENT
# ============================================================
DEPARTMENT_CONTENT = {
    "cardiology": {
        "title": "Cardiology",
        "subtitle": "Advanced heart care in Budgam — consultant-led cardiology with 24/7 emergency response.",
        "treat": ["Coronary Artery Disease & Angina", "Heart Failure & Cardiomyopathy",
                  "Arrhythmias & Palpitations", "Valvular Heart Disease",
                  "Hypertension Management", "Interventional Cardiology",
                  "Cardiac Emergencies", "Preventive Cardiology"],
        "facilities": ["ECG & Holter monitoring", "2D Echo & Stress Echo",
                       "TMT (Treadmill Test)", "ABPM (24-hour BP)",
                       "Coronary angiography referral", "24/7 cardiac emergency care"],
        "faqs": [
            ("What are the early warning signs of a heart attack?",
             "Chest pain or pressure lasting more than a few minutes, pain radiating to the arm, jaw, or back, shortness of breath, cold sweat, and nausea. If you experience these, call 9622552553 immediately."),
            ("Do you offer TMT, Holter, and ABPM at Ibn Sina?",
             "Yes. All three tests are available in-house, with cardiology consultation to interpret the results."),
            ("Can I see a cardiologist without a referral?",
             "Yes. You can book directly through our appointment page or call reception."),
        ],
    },
    "gynaecology": {
        "title": "Gynaecology & Obstetrics",
        "subtitle": "Trusted women's health, pregnancy care, and gynaecological surgery in Budgam.",
        "treat": ["Menstrual disorders", "PCOS / PCOD management",
                  "Uterine fibroids & endometriosis", "Ovarian cysts",
                  "Infertility assessment", "Pregnancy & high-risk obstetrics",
                  "Menopause care", "Minimally invasive gynaecological surgery"],
        "facilities": ["Labour & delivery suites", "NICU for newborns",
                       "Laparoscopic surgery unit", "Fetal monitoring",
                       "24/7 blood bank & pharmacy", "High-risk pregnancy unit"],
        "faqs": [
            ("How many gynaecologists practice at Ibn Sina Hospital?",
             "Six consultant gynaecologists, covering general women's health, high-risk obstetrics, and minimally invasive surgery."),
            ("Do you offer 24/7 emergency delivery?",
             "Yes. Our labour ward, NICU, blood bank, and emergency team are available 24/7."),
            ("Is PM-JAY accepted for gynaecology treatments?",
             "Yes. Eligible families can receive cashless treatment under PM-JAY. Visit our PM-JAY page for details."),
        ],
    },
    "orthopaedics": {
        "title": "Orthopaedics & Joint Replacement",
        "subtitle": "Bone, joint, trauma, and joint replacement care in Budgam.",
        "treat": ["Joint replacement (hip, knee)", "Sports injuries & arthroscopy",
                  "Fractures & trauma", "Spinal disorders & back pain",
                  "Arthritis & osteoarthritis", "Ligament & tendon injuries",
                  "Paediatric orthopaedics", "Osteoporosis care"],
        "facilities": ["Joint replacement surgery suite", "Arthroscopy unit",
                       "Digital X-ray & MRI", "Physiotherapy centre",
                       "24/7 trauma & emergency care", "Post-operative rehabilitation"],
        "faqs": [
            ("When should I consider knee replacement?",
             "When conservative treatment (medication, physiotherapy, injections) no longer controls pain and daily activities become difficult. A consultation will assess suitability."),
            ("Do you offer sports injury care?",
             "Yes — arthroscopic surgery for ACL, meniscus, and rotator cuff injuries is available with our sports medicine specialist."),
            ("How long is recovery after joint replacement?",
             "Most patients walk with support within 24–48 hours, continue physiotherapy for 6–12 weeks, and return to normal activity within 3–6 months."),
        ],
    },
    "ent": {
        "title": "ENT (Ear, Nose & Throat)",
        "subtitle": "Ear, nose, throat, and head-and-neck care in Budgam.",
        "treat": ["Chronic sinusitis & nasal polyps", "Hearing loss & ear infections",
                  "Tonsillitis & adenoid disorders", "Voice & swallowing disorders",
                  "Head & neck cancers", "Sleep apnoea & snoring",
                  "Vertigo & balance disorders", "Thyroid & salivary gland disorders"],
        "facilities": ["Advanced endoscopy & microscopy", "Audiometry & hearing aid fitting",
                       "Head & neck surgical suite", "CT & MRI imaging",
                       "In-house pharmacy & lab", "24/7 emergency ENT"],
        "faqs": [
            ("When should I see an ENT for hearing loss?",
             "Sudden hearing loss, persistent tinnitus, dizziness, ear pain, or frequently asking people to repeat themselves."),
            ("Do you treat vertigo?",
             "Yes — diagnosis, medication, and vestibular rehabilitation are available."),
            ("What ENT surgeries do you offer?",
             "Tonsillectomy, adenoidectomy, sinus surgery, tympanoplasty, mastoidectomy, vocal cord surgery, and head & neck procedures."),
        ],
    },
    "general-medicine": {
        "title": "General Medicine",
        "subtitle": "Comprehensive internal medicine for adults in Budgam.",
        "treat": ["Hypertension & cardiovascular risk", "Diabetes & metabolic disorders",
                  "Respiratory infections", "Gastrointestinal & liver disease",
                  "Thyroid & endocrine disorders", "Chronic kidney disease",
                  "Infectious diseases & fever", "Preventive health checkups"],
        "facilities": ["24/7 diagnostic lab", "ECG & cardiac monitoring",
                       "Digital X-ray & ultrasound", "Pulmonary function testing",
                       "In-house pharmacy", "24/7 emergency services"],
        "faqs": [
            ("Do you manage diabetes and hypertension?",
             "Yes. Consultation, medication, lifestyle counselling, and monitoring are all available."),
            ("Do I need fasting for a diabetes test?",
             "Yes — fasting blood sugar requires 8 hours of fasting. HbA1c does not."),
            ("Can I get a full health checkup?",
             "Yes. See our Health Checkup Packages page for pricing."),
        ],
    },
    "general-surgery": {
        "title": "General Surgery",
        "subtitle": "Laparoscopic and emergency surgery in Budgam.",
        "treat": ["Gallbladder disease & gallstones", "Hernia (inguinal, umbilical, hiatal)",
                  "Appendicitis", "Gastrointestinal surgery",
                  "Breast disorders", "Thyroid surgery",
                  "Trauma & emergency surgery", "Colorectal & proctology"],
        "facilities": ["Advanced laparoscopic suite", "Minimally invasive equipment",
                       "CT, MRI & ultrasound", "Histopathology & lab",
                       "Blood bank", "24/7 trauma & emergency surgery"],
        "faqs": [
            ("Do you offer laparoscopic surgery?",
             "Yes — for gallbladder, hernia, appendix, and other abdominal procedures."),
            ("What is recovery time after laparoscopic surgery?",
             "Most patients recover within 1–2 weeks versus 4–6 weeks for open surgery."),
            ("Do you handle emergency surgeries?",
             "Yes, 24/7 for appendicitis, perforations, intestinal obstructions, and trauma."),
        ],
    },
    "nephrology": {
        "title": "Nephrology & Dialysis",
        "subtitle": "Kidney care and dialysis in Budgam — the only in-house dialysis unit in the district.",
        "treat": ["Chronic kidney disease", "Acute kidney injury",
                  "Diabetic nephropathy", "Hypertension & kidney disease",
                  "Kidney stones", "Glomerulonephritis",
                  "End-stage renal disease", "Electrolyte disorders"],
        "facilities": ["In-house hemodialysis unit", "Peritoneal dialysis support",
                       "Renal lab & imaging", "Dialysis catheter care",
                       "24/7 emergency kidney care", "PM-JAY cashless dialysis"],
        "faqs": [
            ("Is dialysis available at Ibn Sina Hospital?",
             "Yes. Our in-house dialysis unit operates on a scheduled basis. Call 9622552553 to check availability."),
            ("Is dialysis covered under PM-JAY?",
             "Yes, for eligible patients. Our Ayushman Mitra desk helps with eligibility checks and claims."),
            ("What are the warning signs of kidney disease?",
             "Persistent fatigue, swelling in legs or face, foamy urine, changes in urination, and difficulty controlling blood pressure."),
        ],
    },
    "gastroenterology": {
        "title": "Gastroenterology",
        "subtitle": "Digestive and liver care in Budgam.",
        "treat": ["Acid reflux & GERD", "Liver disease (hepatitis, cirrhosis)",
                  "Irritable bowel syndrome", "Inflammatory bowel disease",
                  "Pancreatic & gallbladder disorders", "Ulcers & gastritis",
                  "GI cancers screening", "Fatty liver disease"],
        "facilities": ["Advanced endoscopy suite", "Colonoscopy & ERCP",
                       "CT, MRI & ultrasound", "Comprehensive GI & liver lab",
                       "In-house pharmacy", "24/7 GI emergency"],
        "faqs": [
            ("Do you offer endoscopy and colonoscopy?",
             "Yes — upper GI endoscopy, colonoscopy, ERCP, and capsule endoscopy are available."),
            ("Is sedation available for endoscopy?",
             "Yes. Conscious sedation is offered for comfort during the procedure."),
            ("What are signs I should see a gastroenterologist?",
             "Persistent abdominal pain, chronic heartburn, difficulty swallowing, blood in stool, unexplained weight loss."),
        ],
    },
    "urology": {
        "title": "Urology",
        "subtitle": "Kidney, prostate, and urinary care in Budgam.",
        "treat": ["Kidney stones (laser & endoscopic)", "Prostate disorders (BPH)",
                  "Urinary tract infections", "Bladder & urethral disorders",
                  "Male infertility", "Urological cancers",
                  "Paediatric urology", "Laparoscopic urology"],
        "facilities": ["Laser lithotripsy unit", "Cystoscopy & urodynamics",
                       "Laparoscopic surgery suite", "CT urogram & ultrasound",
                       "In-house pharmacy", "24/7 urology emergency"],
        "faqs": [
            ("Do you offer laser treatment for kidney stones?",
             "Yes — laser lithotripsy is available for kidney and ureteric stones."),
            ("What is the treatment for enlarged prostate?",
             "Options include medication, minimally invasive procedures (TURP), and surgery in selected cases."),
            ("Do you treat male infertility?",
             "Yes — evaluation, medical management, counselling, and surgical options are available."),
        ],
    },
    "pediatric-surgery": {
        "title": "Paediatric Surgery",
        "subtitle": "Surgical care for children in Budgam.",
        "treat": ["Congenital anomalies", "Appendicitis & acute abdomen",
                  "Paediatric trauma", "GI disorders in newborns",
                  "Tumours & cysts", "Hypospadias & urological conditions",
                  "Chest wall deformities", "Minimally invasive paediatric surgery"],
        "facilities": ["Dedicated paediatric operating suite", "Advanced laparoscopic equipment",
                       "Child-friendly imaging", "Paediatric lab",
                       "Blood bank", "24/7 paediatric emergency"],
        "faqs": [
            ("What conditions does a paediatric surgeon treat?",
             "Congenital anomalies, appendicitis, hernias, undescended testis, tumours, trauma, and GI disorders in children."),
            ("Do you offer minimally invasive paediatric surgery?",
             "Yes — for appendectomy, hernia repair, and other procedures."),
            ("What emergency paediatric surgical services are available?",
             "24/7 for appendicitis, bowel obstruction, trauma, and life-threatening emergencies."),
        ],
    },
    "dermatology": {
        "title": "Dermatology",
        "subtitle": "Skin, hair, and nail care in Budgam.",
        "treat": ["Acne & acne scars", "Eczema, psoriasis & dermatitis",
                  "Skin infections", "Hair loss & scalp disorders",
                  "Nail disorders", "Vitiligo & pigmentation",
                  "Skin cancers & moles", "Cosmetic dermatology"],
        "facilities": ["Dermatoscopy & skin biopsy", "Laser therapy",
                       "PRP & injectables", "Hair transplant suite",
                       "In-house pharmacy & lab", "24/7 dermatology emergency"],
        "faqs": [
            ("What skin conditions do you treat?",
             "Acne, eczema, psoriasis, infections, vitiligo, hair loss, nail disorders, and skin cancers."),
            ("Do you offer cosmetic dermatology?",
             "Yes — chemical peels, laser treatments, fillers, PRP for hair restoration, and anti-aging treatments."),
            ("Is hair transplant available?",
             "Yes — performed by our Dermatologist & Hair Transplant Surgeon."),
        ],
    },
    "pulmonology": {
        "title": "Pulmonology",
        "subtitle": "Respiratory and lung care in Budgam.",
        "treat": ["Asthma & allergic disorders", "COPD",
                  "Pneumonia & lung infections", "Tuberculosis",
                  "Interstitial lung disease", "Sleep apnoea",
                  "Lung cancer & nodules", "Respiratory failure"],
        "facilities": ["Pulmonary function testing", "Chest X-ray & HRCT",
                       "Bronchoscopy", "Sleep study & CPAP therapy",
                       "In-house pharmacy", "24/7 respiratory emergency"],
        "faqs": [
            ("Do you offer pulmonary function tests?",
             "Yes — spirometry, lung volumes, and diffusion capacity testing."),
            ("Do you treat sleep apnoea?",
             "Yes — sleep studies, CPAP therapy, and lifestyle counselling."),
            ("What are COPD symptoms?",
             "Chronic cough, breathlessness on exertion, wheezing, and frequent respiratory infections."),
        ],
    },
    "rheumatology": {
        "title": "Rheumatology",
        "subtitle": "Arthritis and autoimmune care in Budgam.",
        "treat": ["Rheumatoid arthritis", "Osteoarthritis",
                  "Gout", "Ankylosing spondylitis",
                  "Lupus (SLE)", "Psoriatic arthritis",
                  "Fibromyalgia", "Vasculitis"],
        "facilities": ["Advanced lab testing", "Digital X-ray & MRI",
                       "Biologic therapy infusion unit", "Physiotherapy & rehab",
                       "In-house pharmacy", "24/7 emergency support"],
        "faqs": [
            ("What conditions do you treat?",
             "Rheumatoid arthritis, osteoarthritis, gout, lupus, ankylosing spondylitis, psoriatic arthritis, and fibromyalgia."),
            ("How is arthritis diagnosed?",
             "Clinical examination, blood tests (RF, anti-CCP, ESR, CRP), and imaging studies."),
            ("Do you offer biologic therapy?",
             "Yes — DMARDs and biologic infusions are available under consultant supervision."),
        ],
    },
    "radiology": {
        "title": "Radiology & Imaging",
        "subtitle": "Diagnostic imaging in Budgam.",
        "treat": ["MRI", "CT scan",
                  "Digital X-ray & fluoroscopy", "Ultrasound & Doppler",
                  "Mammography", "Contrast studies",
                  "Interventional radiology", "Emergency imaging"],
        "facilities": ["High-field MRI", "Multi-slice CT",
                       "Digital radiography", "High-resolution ultrasound",
                       "Contrast injection suite", "24/7 emergency imaging"],
        "faqs": [
            ("Do I need a referral for imaging?",
             "Most tests require a referral. X-ray and ultrasound may be done with a valid prescription."),
            ("How long do reports take?",
             "Preliminary reports within 24 hours; urgent cases are prioritised."),
            ("Is imaging safe during pregnancy?",
             "Ultrasound is safe. X-ray and CT are avoided unless essential. Our team takes extra precautions."),
        ],
    },
    "physiotherapy": {
        "title": "Physiotherapy & Rehabilitation",
        "subtitle": "Rehabilitation and physical therapy in Budgam.",
        "treat": ["Orthopaedic conditions", "Post-surgical rehabilitation",
                  "Sports injuries", "Neurological disorders",
                  "Spinal cord injury", "Paediatric physiotherapy",
                  "Geriatric rehabilitation", "Chronic pain"],
        "facilities": ["Manual therapy", "Therapeutic exercise",
                       "Electrotherapy (TENS, ultrasound, laser)", "Hydrotherapy",
                       "In-house pharmacy", "24/7 emergency support"],
        "faqs": [
            ("What conditions does physiotherapy treat?",
             "Musculoskeletal pain, sports injuries, post-surgical rehabilitation, stroke, Parkinson's, and chronic pain."),
            ("Do you offer neuro physiotherapy?",
             "Yes — a dedicated neuro physiotherapist handles stroke, spinal cord, and neuromuscular rehabilitation."),
            ("Is physiotherapy covered by insurance?",
             "Most plans cover physiotherapy when prescribed by a doctor."),
        ],
    },
    "plastic-surgery": {
        "title": "Plastic & Reconstructive Surgery",
        "subtitle": "Reconstructive and cosmetic surgery in Budgam.",
        "treat": ["Burn management & scar revision", "Trauma reconstruction",
                  "Cleft lip & palate repair", "Breast surgery",
                  "Skin cancer reconstruction", "Hand surgery",
                  "Facial cosmetic surgery", "Body contouring"],
        "facilities": ["Microsurgery suite", "Burn unit & skin grafting",
                       "Hand surgical unit", "Cosmetic surgery suite",
                       "In-house pharmacy", "24/7 emergency & trauma"],
        "faqs": [
            ("What procedures does a plastic surgeon perform?",
             "Reconstructive surgery for trauma and burns, cleft lip/palate repair, skin cancer reconstruction, and cosmetic procedures."),
            ("Do you treat burn injuries?",
             "Yes — emergency management, wound care, skin grafting, and reconstructive surgery."),
            ("What cosmetic procedures do you offer?",
             "Facelift, rhinoplasty, blepharoplasty, breast augmentation, liposuction, and injectables."),
        ],
    },
    "dentistry": {
        "title": "Dentistry",
        "subtitle": "Complete dental and oral care in Budgam.",
        "treat": ["Tooth decay & cavities", "Gum disease",
                  "Root canal treatment", "Extractions & wisdom tooth surgery",
                  "Crowns, bridges & dentures", "Dental implants",
                  "Cosmetic dentistry", "Preventive dentistry"],
        "facilities": ["Advanced dental chair", "Digital X-ray",
                       "Sterile treatment environment", "In-house pharmacy",
                       "Cosmetic dentistry suite", "24/7 emergency dental"],
        "faqs": [
            ("What dental services do you offer?",
             "Routine checkups, scaling, fillings, root canal, crowns, bridges, dentures, extractions, implants, and cosmetic dentistry."),
            ("How often should I visit the dentist?",
             "Every 6 months for a routine checkup and cleaning, or sooner if you have pain or bleeding gums."),
            ("Do you offer emergency dental care?",
             "Yes — for severe toothache, broken teeth, and dental infections."),
        ],
    },
    "ophthalmology": {
        "title": "Ophthalmology (Eye Care)",
        "subtitle": "Comprehensive eye care in Budgam.",
        "treat": ["Cataract", "Glaucoma",
                  "Diabetic retinopathy", "Macular degeneration",
                  "Refractive errors", "Dry eye",
                  "Eye infections & uveitis", "Corneal disorders"],
        "facilities": ["Phacoemulsification unit", "Slit-lamp & fundus camera",
                       "OCT imaging", "YAG & Argon lasers",
                       "In-house pharmacy", "24/7 eye emergency"],
        "faqs": [
            ("What are cataract symptoms?",
             "Blurred or cloudy vision, difficulty seeing at night, sensitivity to light, and fading colours."),
            ("How often should I get my eyes checked?",
             "Every 1–2 years for adults; annually after 60 or with diabetes, hypertension, or family history."),
            ("Do you offer LASIK?",
             "Refractive surgery including LASIK and PRK is available after suitability assessment."),
        ],
    },
    "neonatal-intensive-care-unit": {
        "title": "Neonatal Intensive Care Unit (NICU)",
        "subtitle": "Round-the-clock specialised newborn care in Budgam.",
        "treat": ["Premature & low-birth-weight babies", "Respiratory distress",
                  "Neonatal jaundice", "Neonatal infections & sepsis",
                  "Feeding & growth difficulties", "Birth asphyxia",
                  "Hypoglycemia & temperature instability", "Continuous monitoring for high-risk newborns"],
        "facilities": ["Incubators & radiant warmers", "Phototherapy units",
                       "Cardio-respiratory monitoring", "Neonatal respiratory support",
                       "24/7 lab & imaging", "24/7 neonatal emergency"],
        "team_note": "Our NICU is staffed 24/7 by experienced paediatricians and specially trained neonatal nursing staff, working under consultant supervision.",
        "faqs": [
            ("What is a NICU?",
             "A specialised unit providing round-the-clock care for premature, low-birth-weight, and critically ill newborns."),
            ("Which newborns need NICU care?",
             "Premature babies, those with breathing difficulty, jaundice requiring treatment, infections, or conditions needing continuous monitoring."),
            ("Can parents stay with their baby?",
             "Parental involvement is encouraged wherever medically appropriate, with guidance and support throughout the stay."),
        ],
    },
}


# ============================================================
# PAGE BUILDERS
# ============================================================
def build_department_page(slug: str, data: dict, doctors_for_dept: list) -> str:
    title = f"{data['title']} in Budgam | Ibn Sina Hospital"
    description = data["subtitle"]
    canonical = f"{SITE_URL}/department-pages/{slug}.html"

    # Build FAQ items as JSON objects — plain string concat to avoid
    # Python 3.11's f-string bracket restrictions.
    faq_items = []
    for q, a in data["faqs"]:
        faq_items.append(
            '{"@type": "Question", '
            f'"name": "{json_escape(q)}", '
            '"acceptedAnswer": {"@type": "Answer", '
            f'"text": "{json_escape(a)}"}}'
        )
    faq_json = "[" + ", ".join(faq_items) + "]"

    jsonld = f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "MedicalClinic",
      "name": "Ibn Sina Hospital — {json_escape(data['title'])}",
      "url": "{canonical}",
      "medicalSpecialty": "{json_escape(data['title'])}",
      "address": {{
        "@type": "PostalAddress",
        "streetAddress": "Near Railway Station, Ompora Railway Station Road, Ompora",
        "addressLocality": "Budgam",
        "addressRegion": "Jammu and Kashmir",
        "postalCode": "191111",
        "addressCountry": "IN"
      }},
      "telephone": "+919622552553"
    }},
    {{
      "@type": "FAQPage",
      "mainEntity": {faq_json}
    }},
    {{
      "@type": "BreadcrumbList",
      "itemListElement": [
        {{"@type": "ListItem", "position": 1, "name": "Home", "item": "{SITE_URL}/"}},
        {{"@type": "ListItem", "position": 2, "name": "Departments", "item": "{SITE_URL}/services.html"}},
        {{"@type": "ListItem", "position": 3, "name": "{json_escape(data['title'])}", "item": "{canonical}"}}
      ]
    }}
  ]
}}
</script>'''

    head = partial_head(title, description, canonical, extra_jsonld=jsonld, root="../")
    header = partial_header(active="services", root="../")
    footer = partial_footer(root="../")
    scripts = partial_scripts(root="../")

    treats = "".join(f'<div class="treat-item">{escape(t)}</div>' for t in data["treat"])
    facilities = "".join(f'<li>{escape(f)}</li>' for f in data["facilities"])

    doctors_html = ""
    if doctors_for_dept:
        cards = []
        for d in doctors_for_dept[:6]:
            name = clean_name(d.get("name", ""))
            slug_d = "doctor-" + slugify(d.get("name", ""))
            photo = d.get("photo_url") or ""
            img = (f'<img class="doctor-card-img" src="{escape(photo)}" alt="{escape(name)}" loading="lazy" width="96" height="96">'
                   if photo else '<div class="doctor-card-placeholder">👨‍⚕️</div>')
            cards.append(f'''<a class="doctor-card" href="../doctors/{slug_d}.html">
              {img}
              <h3>{escape(name)}</h3>
              <p class="doctor-card-specialty">{escape(title_case(d.get("specialty", "")))}</p>
              <p class="doctor-card-qual">{escape(d.get("qualifications", ""))}</p>
              <span class="btn btn-outline btn-sm">View Profile</span>
            </a>''')
        doctors_html = f'''
        <section class="section-padding section-flush-top">
          <div class="container">
            <h2 class="section-title">Our {escape(data["title"])} Team</h2>
            <div class="doctor-cards-grid">{"".join(cards)}</div>
          </div>
        </section>'''

    faqs_html = "".join(
        f'<details class="faq-item"><summary>{escape(q)}</summary><div class="faq-answer">{escape(a)}</div></details>'
        for q, a in data["faqs"]
    )

    team_note = ""
    if data.get("team_note"):
        team_note = f'<div class="team-note-card"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-6 8-6s8 2 8 6"/></svg><p>{escape(data["team_note"])}</p></div>'

    return f'''{head}
{header}
<main id="main-content">

  <nav class="breadcrumb-premium container" aria-label="Breadcrumb">
    <a href="../index.html">Home</a><span>›</span>
    <a href="../services.html">Departments</a><span>›</span>
    <span>{escape(data["title"])}</span>
  </nav>

  <section class="dept-hero">
    <div class="container">
      <h1>{escape(data["title"])}</h1>
      <p class="subtitle">{escape(data["subtitle"])}</p>
      <div class="hero-ctas">
        <a href="../appointment.html?dept={slug}" class="btn btn-primary">Book Appointment</a>
        <a href="https://wa.me/919622552553" class="btn btn-emergency" target="_blank" rel="noopener">WhatsApp</a>
        <a href="tel:+919622552553" class="btn btn-outline-light">Call 9622552553</a>
      </div>
      <div class="trust-badges">
        <span>🕐 24/7 OPD &amp; Emergency</span>
        <span>👨‍⚕️ Consultant-Led Care</span>
        <span>💳 PM-JAY / Insurance</span>
      </div>
    </div>
  </section>

  <section class="section-padding">
    <div class="container">
      <h2 class="section-title">What We Treat</h2>
      <div class="treat-grid">{treats}</div>
      <p class="treat-note">Consultant-led care for patients from Budgam, Srinagar, Ganderbal, and across Jammu &amp; Kashmir.</p>
    </div>
  </section>

  {doctors_html}

  <section class="section-padding" style="background:var(--bg-alt)">
    <div class="container">
      <h2 class="section-title">Our Facilities</h2>
      <ul class="facilities-list">{facilities}</ul>
      {team_note}
    </div>
  </section>

  <section class="section-padding">
    <div class="container">
      <h2 class="section-title">Why Ibn Sina Hospital</h2>
      <div class="why-grid">
        <div class="why-card"><div class="why-card-icon">🕐</div><h3>24/7 OPD &amp; Emergency</h3><p>Round-the-clock outpatient and emergency services.</p></div>
        <div class="why-card"><div class="why-card-icon">👨‍⚕️</div><h3>Consultant-Led Care</h3><p>Experienced consultants guide every case.</p></div>
        <div class="why-card"><div class="why-card-icon">💳</div><h3>PM-JAY &amp; Insurance</h3><p>Cashless treatment for eligible families.</p></div>
        <div class="why-card"><div class="why-card-icon">📍</div><h3>Accessible Location</h3><p>Ompora, Budgam — near the railway station.</p></div>
      </div>
    </div>
  </section>

  <section class="section-padding" style="background:var(--bg-alt)">
    <div class="container">
      <h2 class="section-title">Frequently Asked Questions</h2>
      <div class="faq-list">{faqs_html}</div>
    </div>
  </section>

  <section class="section-padding">
    <div class="container">
      <div class="also-serving">
        <h3>Also serving</h3>
        <div class="also-serving-links">
          <a href="../service-areas/hospital-in-srinagar.html">Srinagar patients</a>
          <a href="../service-areas/hospital-in-ganderbal.html">Ganderbal patients</a>
          <a href="../service-areas/hospital-near-chadoora-beerwah-charar.html">Chadoora, Beerwah &amp; Charar-i-Sharief</a>
        </div>
      </div>
    </div>
  </section>

  <section class="cta-banner">
    <div class="container cta-banner-inner">
      <div>
        <h2>Ready to book your visit?</h2>
        <p>Call us directly or book online. Our team will confirm within a few hours.</p>
        <div class="cta-banner-buttons">
          <a href="../appointment.html?dept={slug}" class="btn btn-primary btn-lg">Book Appointment</a>
          <a href="../contact.html" class="btn btn-outline-light btn-lg">Contact Us</a>
        </div>
      </div>
      <div class="emergency-callout">
        <strong>Emergency</strong>
        <a href="tel:9622552553">9622552553</a>
        <span>Available 24/7, 365 days</span>
      </div>
    </div>
  </section>

</main>
{footer}
{scripts}'''


def build_doctor_page(doc: dict, dept: dict, related: list) -> tuple:
    name = clean_name(doc.get("name", ""))
    slug = "doctor-" + slugify(doc.get("name", ""))
    filename = f"{slug}.html"
    url = f"{SITE_URL}/doctors/{filename}"
    specialty = title_case(doc.get("specialty", ""))
    department = title_case(doc.get("department", ""))
    qualifications = doc.get("qualifications", "")
    photo = doc.get("photo_url") or ""
    about = doc.get("about", "")

    title = f"{name} — {specialty} in Budgam | Ibn Sina Hospital"
    description = (f"{name} is a {specialty} at Ibn Sina Hospital, Budgam. "
                   f"View profile, qualifications, and book an appointment.")

    jsonld = f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "Physician",
      "name": "{json_escape(name)}",
      "medicalSpecialty": "{json_escape(specialty)}",
      "url": "{url}",
      {"\"image\": \"" + json_escape(photo) + "\"," if photo else ""}
      "worksFor": {{
        "@type": "Hospital",
        "name": "Ibn Sina Hospital",
        "address": {{
          "@type": "PostalAddress",
          "addressLocality": "Budgam",
          "addressRegion": "Jammu and Kashmir",
          "addressCountry": "IN"
        }}
      }}
    }},
    {{
      "@type": "BreadcrumbList",
      "itemListElement": [
        {{"@type": "ListItem", "position": 1, "name": "Home", "item": "{SITE_URL}/"}},
        {{"@type": "ListItem", "position": 2, "name": "Doctors", "item": "{SITE_URL}/doctors.html"}},
        {{"@type": "ListItem", "position": 3, "name": "{json_escape(name)}", "item": "{url}"}}
      ]
    }}
  ]
}}
</script>'''

    head = partial_head(title, description, url, image=photo or DEFAULT_IMAGE,
                        extra_jsonld=jsonld, root="../")
    header = partial_header(active="doctors", root="../")
    footer = partial_footer(root="../")
    scripts = partial_scripts(root="../")

    photo_html = (f'<img class="doctor-profile-photo" src="{escape(photo)}" alt="{escape(name)} — {escape(specialty)}" width="140" height="140">'
                  if photo else '<div class="doctor-profile-photo doctor-card-placeholder" aria-hidden="true">👨‍⚕️</div>')

    dept_link = ""
    if dept:
        dept_link = f'<p><a href="../department-pages/{escape(dept["slug"])}.html">View {escape(title_case(dept["name"]))} Department →</a></p>'

    related_html = ""
    if related:
        items = "".join(
            f'<li><a href="doctor-{slugify(r.get("name",""))}.html">{escape(clean_name(r.get("name","")))} — {escape(title_case(r.get("specialty","")))}</a></li>'
            for r in related[:5]
        )
        related_html = f'<div class="related-doctors"><strong>Other {escape(department)} Specialists</strong><ul>{items}</ul></div>'

    return filename, url, f'''{head}
{header}
<main id="main-content">
  <nav class="breadcrumb-premium container" aria-label="Breadcrumb">
    <a href="../index.html">Home</a><span>›</span>
    <a href="../doctors.html">Doctors</a><span>›</span>
    <span>{escape(name)}</span>
  </nav>

  <article class="container doctor-profile">
    <header class="doctor-profile-header">
      {photo_html}
      <h1>{escape(name)}</h1>
      <span class="doctor-profile-specialty">{escape(specialty)}</span>
      <div class="doctor-profile-meta">
        <span><strong>Department:</strong> {escape(department)}</span>
        {f'<span><strong>Qualifications:</strong> {escape(qualifications)}</span>' if qualifications else ''}
      </div>
      {dept_link}
    </header>

    {f'<div class="doctor-profile-bio">{escape(about)}</div>' if about else ''}

    {related_html}

    <div class="doctor-profile-ctas">
      <a href="../appointment.html?doctor={quote(name)}" class="btn btn-primary btn-lg">Book Appointment</a>
      <a href="tel:9622552553" class="btn btn-outline">Call 9622552553</a>
    </div>
  </article>
</main>
{footer}
{scripts}'''


def build_blog_post(post: dict, related: list) -> tuple:
    slug = post.get("slug") or slugify(post.get("title", ""))
    filename = f"blog-{slug}.html"
    url = f"{SITE_URL}/blog/{filename}"
    title = post.get("title", "Health Article")
    summary = post.get("short_summary") or post.get("short summary") or ""
    body = post.get("body", "")
    published = post.get("published_at", "")
    image = post.get("cover_image_url") or DEFAULT_IMAGE
    category = post.get("category", "Health")
    reading = max(1, math.ceil(len(re.sub(r"<[^>]+>", " ", body).split()) / 200))

    # Rewrite internal links from /blog/
    body = re.sub(r'href="appointment\.html"', 'href="../appointment.html"', body)
    body = re.sub(r'href="insurance-pmjay\.html"', 'href="../insurance-pmjay.html"', body)
    body = re.sub(r'href="services\.html"', 'href="../services.html"', body)
    body = re.sub(r'href="doctors\.html"', 'href="../doctors.html"', body)
    body = re.sub(r'href="contact\.html"', 'href="../contact.html"', body)
    body = re.sub(r'href="about\.html"', 'href="../about.html"', body)
    body = re.sub(r'href="blog\.html"', 'href="../blog.html"', body)
    body = re.sub(r'href="faq\.html"', 'href="../faq.html"', body)
    body = re.sub(r'href="health-checkup-packages\.html"', 'href="../health-checkup-packages.html"', body)
    body = re.sub(r'href="department-pages/', 'href="../department-pages/', body)

    if "<p>" not in body and "<div" not in body and "<ul" not in body:
        body = format_blog_body(body)

    related_html = ""
    if related:
        items = "".join(
            f'<li><a href="blog-{escape(r.get("slug",""))}.html">{escape(r.get("title",""))}</a></li>'
            for r in related[:3]
        )
        related_html = f'<section class="blog-related-articles"><h2>Related Articles</h2><ul>{items}</ul></section>'

    formatted_date = format_date(published)

    jsonld = f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{json_escape(title)}",
  "description": "{json_escape(summary[:160])}",
  "image": "{json_escape(image)}",
  "datePublished": "{json_escape(published)}",
  "dateModified": "{json_escape(published)}",
  "author": {{"@type": "Organization", "name": "Ibn Sina Hospital", "url": "{SITE_URL}/"}},
  "publisher": {{
    "@type": "Organization",
    "name": "Ibn Sina Hospital",
    "logo": {{"@type": "ImageObject", "url": "{FAVICON}"}}
  }},
  "mainEntityOfPage": {{"@type": "WebPage", "@id": "{url}"}}
}}
</script>'''

    head = partial_head(title, summary[:160], url, image=image, is_article=True,
                        extra_jsonld=jsonld, root="../")
    header = partial_header(active="blog", root="../")
    footer = partial_footer(root="../")
    scripts = partial_scripts(root="../")

    return filename, url, f'''{head}
{header}
<main id="main-content">
  <nav class="breadcrumb-premium container" aria-label="Breadcrumb">
    <a href="../index.html">Home</a><span>›</span>
    <a href="../blog.html">Health Insights</a><span>›</span>
    <span>{escape(title)}</span>
  </nav>

  <article class="blog-article">
    <header class="blog-article-header">
      <span class="blog-article-category">{escape(category)}</span>
      <h1 class="blog-article-title">{escape(title)}</h1>
      <p class="blog-article-summary">{escape(summary)}</p>
      <div class="blog-article-meta">
        <time datetime="{escape(published)}">📅 {escape(formatted_date)}</time>
        <span>⏱ {reading} min read</span>
        <span>Ibn Sina Hospital</span>
      </div>
    </header>

    <figure class="blog-hero-media">
      <img src="{escape(image)}" alt="{escape(title)}" loading="eager" fetchpriority="high" width="1200" height="630">
    </figure>

    <div class="blog-body">
      {body}
      {related_html}
      <aside class="blog-medical-disclaimer">
        <strong>Medical Disclaimer</strong>
        This article is for general information only and does not replace consultation with a qualified healthcare professional.
      </aside>
    </div>

    <section class="blog-article-cta">
      <h2>Have a health concern?</h2>
      <p>Our team at Ibn Sina Hospital is here to help. Book an appointment or call us directly.</p>
      <div class="blog-article-cta-actions">
        <a href="../appointment.html" class="btn btn-primary btn-lg">Book Appointment</a>
        <a href="tel:9622552553" class="btn btn-outline btn-lg">Call 9622552553</a>
      </div>
    </section>
  </article>
</main>
{footer}
{scripts}'''


def format_blog_body(text: str) -> str:
    text = re.sub(r"[\u200B-\u200D\u2060\uFEFF]", "", text)
    blocks = re.split(r"\n\s*\n", text)
    out = []
    lead_assigned = False

    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        is_bulleted = all(re.match(r"^[-•*]\s+", l) for l in lines)
        is_numbered = all(re.match(r"^\d+[.)]\s+", l) for l in lines)

        if is_bulleted:
            items = "".join(f"<li>{html.escape(re.sub(r'^[-•*]\s+', '', l))}</li>" for l in lines)
            out.append(f"<ul>{items}</ul>")
        elif is_numbered:
            items = "".join(f"<li>{html.escape(re.sub(r'^\d+[.)]\s+', '', l))}</li>" for l in lines)
            out.append(f"<ol>{items}</ol>")
        elif len(lines) == 1:
            line = lines[0]
            wc = len(line.split())
            if line.endswith("?") and wc <= 20:
                out.append(f'<p class="blog-pull-quote">{html.escape(line)}</p>')
            elif wc <= 8 and not re.search(r"[.!?:;,]$", line) and re.match(r"^[A-Z]", line):
                out.append(f'<h3 class="blog-subheading">{html.escape(line)}</h3>')
            else:
                cls = " class=\"blog-lead-paragraph\"" if not lead_assigned else ""
                lead_assigned = True
                out.append(f"<p{cls}>{html.escape(line)}</p>")
        else:
            cls = " class=\"blog-lead-paragraph\"" if not lead_assigned else ""
            lead_assigned = True
            out.append(f"<p{cls}>" + "<br>".join(html.escape(l) for l in lines) + "</p>")

    return "".join(out)


def format_date(value: str) -> str:
    if not value:
        return ""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            d = datetime.datetime.strptime(value.strip(), fmt)
            return f"{d.day} {d.strftime('%B')} {d.year}"
        except (ValueError, AttributeError):
            continue
    return value


# ============================================================
# MAIN
# ============================================================
def main():
    print("[1/6] Fetching data from Google Sheets…")
    doctors_raw = fetch_csv(SHEETS["doctors"])
    blog_raw = fetch_csv(SHEETS["blog"])
    departments_raw = fetch_csv(SHEETS["departments"])
    gallery_raw = fetch_csv(SHEETS["gallery"])
    updates_raw = fetch_csv(SHEETS["updates"])

    # Normalize blog short summary field name (sheet uses "short summary" with a space)
    for post in blog_raw:
        if "short summary" in post and not post.get("short_summary"):
            post["short_summary"] = post.pop("short summary")

    print(f"  → {len(doctors_raw)} doctors, {len(blog_raw)} posts, "
          f"{len(departments_raw)} departments, {len(gallery_raw)} gallery items, "
          f"{len(updates_raw)} updates")

    Path("data").mkdir(exist_ok=True)
    (Path("data") / "doctors.json").write_text(json.dumps(doctors_raw, ensure_ascii=False), encoding="utf-8")
    (Path("data") / "departments.json").write_text(json.dumps(departments_raw, ensure_ascii=False), encoding="utf-8")
    (Path("data") / "blog.json").write_text(json.dumps(blog_raw, ensure_ascii=False), encoding="utf-8")
    (Path("data") / "gallery.json").write_text(json.dumps(gallery_raw, ensure_ascii=False), encoding="utf-8")
    (Path("data") / "updates.json").write_text(json.dumps(updates_raw, ensure_ascii=False), encoding="utf-8")

    print("[2/6] Generating department pages…")
    Path("department-pages").mkdir(exist_ok=True)
    departments_by_slug = {}
    for d in departments_raw:
        departments_by_slug[slugify(d.get("name", ""))] = d
        departments_by_slug[d.get("slug", "")] = d

    dept_urls = []
    for slug, content in DEPARTMENT_CONTENT.items():
        dept_meta = departments_by_slug.get(slug, {})
        dept_doctors = [
            doc for doc in doctors_raw
            if slugify(doc.get("department", "")) == slug or slugify(doc.get("specialty", "")) == slug
        ]
        html_out = build_department_page(slug, content, dept_doctors)
        (Path("department-pages") / f"{slug}.html").write_text(html_out, encoding="utf-8")
        dept_urls.append(f"{SITE_URL}/department-pages/{slug}.html")
    print(f"  → {len(DEPARTMENT_CONTENT)} department pages")

    print("[3/6] Generating doctor profile pages…")
    Path("doctors").mkdir(exist_ok=True)
    doctor_urls = []
    for i, doc in enumerate(doctors_raw):
        dept_slug = slugify(doc.get("department", ""))
        dept_meta = departments_by_slug.get(dept_slug, {"slug": dept_slug, "name": doc.get("department", "")})
        related = [
            d for d in doctors_raw
            if slugify(d.get("department", "")) == dept_slug
            and d.get("name", "") != doc.get("name", "")
        ]
        filename, url, html_out = build_doctor_page(doc, dept_meta, related)
        (Path("doctors") / filename).write_text(html_out, encoding="utf-8")
        doctor_urls.append(url)
    print(f"  → {len(doctor_urls)} doctor pages")

    print("[4/6] Generating blog posts…")
    Path("blog").mkdir(exist_ok=True)
    blog_urls = []
    published_posts = [p for p in blog_raw if str(p.get("is_published", "")).lower().strip() in ("true", "yes", "1", "y")]
    for post in published_posts:
        related = [p for p in published_posts if p.get("slug") != post.get("slug")][:3]
        filename, url, html_out = build_blog_post(post, related)
        (Path("blog") / filename).write_text(html_out, encoding="utf-8")
        blog_urls.append(url)
    print(f"  → {len(blog_urls)} blog posts")

    print("[5/6] Building sitemap…")
    cache = load_lastmod_cache()

    static_pages = [f"{SITE_URL}/{p}" if p else f"{SITE_URL}/" for p in STATIC_TOP_LEVEL_PAGES]
    service_area_urls = [f"{SITE_URL}/{p}" for p in SERVICE_AREA_PAGES]

    directory_pages = [
        f"{SITE_URL}/department-pages/specialties-directory.html",
        f"{SITE_URL}/department-pages/doctor-directory.html",
        f"{SITE_URL}/department-pages/jammu-kashmir-healthcare.html",
    ]

    all_urls = list(set(
        static_pages
        + service_area_urls
        + dept_urls
        + doctor_urls
        + blog_urls
        + directory_pages
    ))

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    for url in sorted(all_urls):
        if url == f"{SITE_URL}/":
            priority = "1.0"
        elif "/doctors/" in url or "/blog/" in url or "/department-pages/" in url:
            priority = "0.8"
        else:
            priority = "0.7"
        lastmod = cache.get(url, {}).get("lastmod", TODAY)
        xml.append(f"  <url><loc>{url}</loc><lastmod>{lastmod}</lastmod>"
                   f"<changefreq>weekly</changefreq><priority>{priority}</priority></url>")

    xml.append("</urlset>")
    Path("sitemap.xml").write_text("\n".join(xml), encoding="utf-8")
    print(f"  → {len(all_urls)} URLs in sitemap")

    for url in all_urls:
        if url not in cache:
            cache[url] = {"hash": "", "lastmod": TODAY}
    save_lastmod_cache(cache)

    print("[6/6] Submitting to IndexNow…")
    try:
        payload = {
            "host": HOST,
            "key": INDEXNOW_KEY,
            "keyLocation": f"https://{HOST}/{INDEXNOW_KEY}.txt",
            "urlList": dept_urls + doctor_urls + blog_urls,
        }
        req = urllib.request.Request(
            INDEXNOW_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"  → IndexNow: {r.status}")
    except Exception as e:
        print(f"  → IndexNow submission failed (non-fatal): {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
