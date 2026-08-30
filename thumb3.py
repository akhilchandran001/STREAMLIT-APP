#!/usr/bin/env python3
"""
Kerala Lottery Scraper & Tri-Language Thumbnail Generator (English, Malayalam, Tamil)
Extracts real draw metadata and renders 3 high-impact thumbnails using exact 4-band geometry.
"""

import os
import re
import sys
import time
import random
import datetime
import requests
import cv2
import numpy as np
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# -------------------------------------------------------------
# CONFIGURATION & STORAGE PATHS (GITHUB REPO ROOT)
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEED_URL = "https://www.keralalotteries.net/feeds/posts/default?alt=json&max-results=10"
PICTURES_DIR = os.path.join(BASE_DIR, "Lottery")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "renders")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# -------------------------------------------------------------
# FONT RESOLUTION (Strictly repository root fonts)
# -------------------------------------------------------------
def get_font_path(lang="en"):
    """Finds appropriate ExtraBold/Bold font files for English, Malayalam, and Tamil from the repo."""
    if lang == "ml":
        candidates = [
            os.path.join(BASE_DIR, "AnekMalayalam-ExtraBold.ttf"),
            os.path.join(BASE_DIR, "AnekMalayalam-Bold.ttf")
        ]
    elif lang == "ta":
        candidates = [
            os.path.join(BASE_DIR, "AnekTamil-ExtraBold.ttf"),
            os.path.join(BASE_DIR, "AnekTamil-Bold.ttf")
        ]
    else:  # en
        candidates = [
            os.path.join(BASE_DIR, "Montserrat-ExtraBold.ttf"),
            os.path.join(BASE_DIR, "Montserrat-Bold.ttf"),
            os.path.join(BASE_DIR, "Anton-Regular.ttf")
        ]

    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


# -------------------------------------------------------------
# LANGUAGE DICTIONARIES & MAPPINGS
# -------------------------------------------------------------
ENGLISH_MONTHS = {
    1: 'JANUARY', 2: 'FEBRUARY', 3: 'MARCH', 4: 'APRIL',
    5: 'MAY', 6: 'JUNE', 7: 'JULY', 8: 'AUGUST',
    9: 'SEPTEMBER', 10: 'OCTOBER', 11: 'NOVEMBER', 12: 'DECEMBER'
}

MALAYALAM_MONTHS = {
    1: "ജനുവരി", 2: "ഫെബ്രുവരി", 3: "മാർച്ച്", 4: "ഏപ്രിൽ",
    5: "മെയ്", 6: "ജൂൺ", 7: "ജൂലൈ", 8: "ആഗസ്റ്റ്",
    9: "സെപ്റ്റംബർ", 10: "ഒക്ടോബർ", 11: "നവംബർ", 12: "ഡിസംബർ"
}

TAMIL_MONTHS = {
    1: "ஜனவரி", 2: "பிப்ரவரி", 3: "மார்ச்", 4: "ஏப்ரல்",
    5: "மே", 6: "ஜூன்", 7: "ஜூலை", 8: "ஆகஸ்ட்",
    9: "செப்டம்பர்", 10: "அக்டோபர்", 11: "நவம்பர்", 12: "டிசம்பர்"
}

LOTTERY_NAMES_MALAYALAM = {
    "SUVARNA KERALAM": "സുവർണ്ണ കേരളം",
    "SAMRUDHI": "സമൃദ്ധി",
    "BHAGYATHARA": "ഭാഗ്യതാര",
    "STHREE SAKTHI": "സ്ത്രീ ശക്തി",
    "DHANALEKSHMI": "ധനലക്ഷ്മി",
    "KARUNYA PLUS": "കാരുണ്യ പ്ലസ്",
    "KARUNYA": "കാരുണ്യ",
    "FIFTY FIFTY": "ഫിഫ്റ്റി ഫിഫ്റ്റി",
    "WIN WIN": "വിൻ വിൻ",
    "NIRMAL": "നിർമ്മൽ",
    "AKSHAYA": "അക്ഷയ",
    "THIRUVONAM BUMPER": "തിരുവോണം ബംബർ",
    "MONSOON BUMPER": "മൺസൂൺ ബംബർ",
    "VISHU BUMPER": "വിഷു ബംബർ",
    "POOJA BUMPER": "പൂജ ബംബർ",
    "SUMMER BUMPER": "സമ്മർ ബംബർ",
    "XMAS NEW YEAR BUMPER": "ക്രിസ്മസ് ന്യൂ ഇയർ ബംബർ"
}

LOTTERY_NAMES_TAMIL = {
    "SUVARNA KERALAM": "சுவர்ண கேரளம்",
    "SAMRUDHI": "சம்ருதி",
    "BHAGYATHARA": "பாக்யதாரா",
    "STHREE SAKTHI": "ஸ்த்ரீ சக்தி",
    "DHANALEKSHMI": "தனலட்சுமி",
    "KARUNYA PLUS": "காருண்யா பிளஸ்",
    "KARUNYA": "காருண்யா",
    "FIFTY FIFTY": "பிப்டி பிப்டி",
    "WIN WIN": "வின் வின்",
    "NIRMAL": "நிர்மல்",
    "AKSHAYA": "அக்ஷயா",
    "THIRUVONAM BUMPER": "திருவோணம் பம்பர்",
    "MONSOON BUMPER": "மான்சூன் பம்பர்",
    "VISHU BUMPER": "விஷு பம்பர்",
    "POOJA BUMPER": "பூஜா பம்பர்",
    "SUMMER BUMPER": "சம்மர் பம்பர்",
    "XMAS NEW YEAR BUMPER": "கிறிஸ்துமஸ் நியூ இயர் பம்பர்"
}

LOTTERY_NAMES = list(LOTTERY_NAMES_MALAYALAM.keys())


def transliterate_to_tamil(text: str) -> str:
    """Fallback phonetic transliterator to Tamil via Google Input Tools API."""
    url = "https://inputtools.google.com/request"
    params = {
        "text": text,
        "itc": "ta-t-i0-und",
        "num": 1,
        "cp": 0,
        "cs": 1,
        "ie": "utf-8",
        "oe": "utf-8",
        "app": "test"
    }
    try:
        res = requests.get(url, params=params, timeout=4).json()
        if res[0] == "SUCCESS":
            return " ".join([w[1][0] for w in res[1]])
    except Exception:
        pass
    return text


def clean_prize_to_pure_words(prize_str: str) -> str:
    """Converts any raw prize string/number into pure English words format without digit noise."""
    p = str(prize_str).upper().replace("₹", "").replace("RS.", "").replace("RS", "").strip()
    p = re.sub(r'\[.*?\]|\(.*?\)', '', p).strip()
    
    if "25 CRORE" in p or "250000000" in p:
        return "25 CRORE"
    elif "20 CRORE" in p or "200000000" in p:
        return "20 CRORE"
    elif "16 CRORE" in p or "160000000" in p:
        return "16 CRORE"
    elif "12 CRORE" in p or "120000000" in p:
        return "12 CRORE"
    elif "10 CRORE" in p or "100000000" in p:
        return "10 CRORE"
    elif "6 CRORE" in p or "60000000" in p:
        return "6 CRORE"
    elif "5 CRORE" in p or "50000000" in p:
        return "5 CRORE"
    elif "1 CRORE" in p or "10000000" in p or "1,00,00,000" in p:
        return "1 CRORE"
    elif "80 LAKH" in p or "8000000" in p or "80,00,000" in p:
        return "80 LAKHS"
    elif "75 LAKH" in p or "7500000" in p or "75,00,000" in p:
        return "75 LAKHS"
    elif "70 LAKH" in p or "7000000" in p or "70,00,000" in p:
        return "70 LAKHS"
    elif "50 LAKH" in p or "5000000" in p or "50,00,000" in p:
        return "50 LAKHS"
    
    match = re.search(r'\b(\d+)\s*(CRORE|LAKH|CRORES|LAKHS)\b', p)
    if match:
        num, unit = match.group(1), match.group(2)
        if "LAKH" in unit:
            return f"{num} LAKHS"
        return f"{num} CRORE"
        
    return "1 CRORE"


def convert_prize_to_malayalam(english_prize_str: str) -> str:
    """Converts English prize text into Malayalam currency format."""
    clean_str = clean_prize_to_pure_words(english_prize_str)
    prize_map = {
        "25 CRORE": "₹25 കോടി",
        "20 CRORE": "₹20 കോടി",
        "16 CRORE": "₹16 കോടി",
        "12 CRORE": "₹12 കോടി",
        "10 CRORE": "₹10 കോടി",
        "6 CRORE": "₹6 കോടി",
        "5 CRORE": "₹5 കോടി",
        "1 CRORE": "₹1 കോടി",
        "80 LAKHS": "₹80 ലക്ഷം",
        "75 LAKHS": "₹75 ലക്ഷം",
        "70 LAKHS": "₹70 ലക്ഷം",
        "50 LAKHS": "₹50 ലക്ഷം"
    }
    return prize_map.get(clean_str, f"₹{clean_str}")


def convert_prize_to_tamil(english_prize_str: str) -> str:
    """Converts English prize text into Tamil currency format."""
    clean_str = clean_prize_to_pure_words(english_prize_str)
    prize_map = {
        "25 CRORE": "₹25 கோடி",
        "20 CRORE": "₹20 கோடி",
        "16 CRORE": "₹16 கோடி",
        "12 CRORE": "₹12 கோடி",
        "10 CRORE": "₹10 கோடி",
        "6 CRORE": "₹6 கோடி",
        "5 CRORE": "₹5 கோடி",
        "1 CRORE": "₹1 கோடி",
        "80 LAKHS": "₹80 லட்சம்",
        "75 LAKHS": "₹75 லட்சம்",
        "70 LAKHS": "₹70 லட்சம்",
        "50 LAKHS": "₹50 லட்சம்"
    }
    return prize_map.get(clean_str, f"₹{clean_str}")


# -------------------------------------------------------------
# EXACT GRAPHICAL DRAWING FUNCTIONS (UNTOUCHED GEOMETRY)
# -------------------------------------------------------------
def smart_resize_and_crop(image, target_w=1280, target_h=300):
    """Scales and center-crops the image to fit 1280x300 without stretching."""
    h, w = image.shape[:2]
    scale = max(target_w / w, target_h / h)
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))

    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    start_x = max(0, (new_w - target_w) // 2)
    start_y = max(0, (new_h - target_h) // 2)
    return resized[start_y:start_y + target_h, start_x:start_x + target_w]


def draw_perfect_fit_text(draw, text, font_path, box_coords, text_color, max_w_ratio=0.95, max_h_ratio=0.78):
    """Scales font size to fill the box based on provided margin ratios."""
    x1, y1, x2, y2 = box_coords
    box_w = x2 - x1
    box_h = y2 - y1

    size = 250
    if not os.path.exists(font_path):
        print(f"Error: Font missing at {font_path}")
        return

    font = ImageFont.truetype(font_path, size)

    while size > 10:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        if w <= box_w * max_w_ratio and h <= box_h * max_h_ratio:
            break
        size -= 1
        font = ImageFont.truetype(font_path, size)

    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    x = x1 + (box_w - w) / 2 - bbox[0]
    y = y1 + (box_h - h) / 2 - bbox[1]

    draw.text((x, y), text, font=font, fill=text_color)


def draw_date_and_live_icon(draw, date_str, suffix_text, font_path, box_coords):
    """Custom renderer for Box 2: Proportionally balances Date, [LIVE] badge, and Draw status."""
    x1, y1, x2, y2 = box_coords
    box_w = x2 - x1
    box_h = y2 - y1

    size = 250
    if not os.path.exists(font_path):
        return

    live_text = "LIVE"
    end_text = " " + suffix_text

    while size > 10:
        font = ImageFont.truetype(font_path, size)

        bbox_date = draw.textbbox((0, 0), date_str, font=font)
        w_date = bbox_date[2] - bbox_date[0]
        h_date = bbox_date[3] - bbox_date[1]

        bbox_live = draw.textbbox((0, 0), live_text, font=font)
        w_live = bbox_live[2] - bbox_live[0]
        h_live = bbox_live[3] - bbox_live[1]

        bbox_end = draw.textbbox((0, 0), end_text, font=font)
        w_end = bbox_end[2] - bbox_end[0]
        h_end = bbox_end[3] - bbox_end[1]

        gap = int(size * 0.25)
        box_pad_x = int(size * 0.35)
        box_pad_y = int(size * 0.15)

        live_box_w = w_live + (box_pad_x * 2)
        live_box_h = h_live + (box_pad_y * 2)

        total_w = w_date + gap + live_box_w + w_end
        max_h = max(h_date, live_box_h, h_end)

        if total_w <= box_w * 0.94 and max_h <= box_h * 0.80:
            break
        size -= 1

    font = ImageFont.truetype(font_path, size)
    start_x = x1 + (box_w - total_w) / 2
    center_y = y1 + (box_h / 2)

    # 1. Draw Date
    date_y = center_y - (h_date / 2) - bbox_date[1]
    draw.text((start_x, date_y), date_str, font=font, fill=(255, 255, 255))

    # 2. Draw Red Rounded 'LIVE' Box
    current_x = start_x + w_date + gap
    rect_y1 = center_y - (live_box_h / 2)
    rect_y2 = center_y + (live_box_h / 2)
    rect_x1 = current_x
    rect_x2 = current_x + live_box_w

    draw.rounded_rectangle([rect_x1, rect_y1, rect_x2, rect_y2], radius=int(size * 0.14), fill=(230, 0, 0))

    live_x = rect_x1 + box_pad_x - bbox_live[0]
    live_y = center_y - (h_live / 2) - bbox_live[1]
    draw.text((live_x, live_y), live_text, font=font, fill=(255, 255, 255))

    # 3. Draw End Text
    current_x = rect_x2
    end_y = center_y - (h_end / 2) - bbox_end[1]
    draw.text((current_x, end_y), end_text, font=font, fill=(255, 255, 255))


def render_thumbnail(text1, date_str, suffix_text, text3, text4, font_path, save_path, cached_middle_rgb=None):
    """Renders the exact 4-band layout."""
    width, height = 1280, 720
    yellow_bg = [255, 230, 0]
    black_bg = [0, 0, 0]
    black_text = (0, 0, 0)
    white_text = (255, 255, 255)

    canvas = np.zeros((height, width, 3), dtype=np.uint8)

    # Top Banners
    canvas[0:110, :] = yellow_bg
    canvas[110:210, :] = black_bg

    # Image Insertion (reusing processed middle RGB for identical backgrounds)
    if cached_middle_rgb is not None:
        canvas[210:510, :] = cached_middle_rgb
    else:
        canvas[210:510, :] = [150, 150, 150]

    # Bottom Banners
    canvas[510:610, :] = black_bg
    canvas[610:720, :] = yellow_bg

    img_pil = Image.fromarray(canvas)
    draw = ImageDraw.Draw(img_pil)

    # Box 1: Yellow Banner
    draw_perfect_fit_text(draw, text1, font_path, (0, 0, width, 110), black_text, max_w_ratio=0.95, max_h_ratio=0.76)

    # Box 2: Black Banner with LIVE badge
    draw_date_and_live_icon(draw, date_str, suffix_text, font_path, (0, 110, width, 210))

    # Box 3: Black Banner (Prize)
    draw_perfect_fit_text(draw, text3, font_path, (0, 510, width, 610), white_text, max_w_ratio=0.95, max_h_ratio=0.76)

    # Box 4: Yellow Banner (Clamped to 75% width for timestamp safe zone)
    draw_perfect_fit_text(draw, text4, font_path, (0, 610, width, 720), black_text, max_w_ratio=0.75, max_h_ratio=0.74)

    try:
        img_pil.save(save_path, "PNG")
        return save_path
    except Exception as e:
        print(f"\033[91mFailed to save {save_path}: {e}\033[0m")
        return None


# -------------------------------------------------------------
# SCRAPING & METADATA PARSING LOGIC
# -------------------------------------------------------------
def fetch_live_feed():
    """Fetches real-time JSON feed with cache-busting."""
    cache_buster = int(time.time())
    url = f"{FEED_URL}&_nocache={cache_buster}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        return response.json()
    except Exception as err:
        print(f"\033[91m❌ Network error while fetching feed: {err}\033[0m")
        return None


def parse_lottery_entry(title, content):
    """Accurately parses lottery name, code, draw date, and first prize money."""
    soup = BeautifulSoup(content, "html.parser")
    full_text = soup.get_text(separator=" ").replace("\xa0", " ")

    # 1. Parse Draw Date
    date_match = re.search(r'(\d{2})[./-](\d{2})[./-](\d{4})', title) or \
                 re.search(r'(\d{2})[./-](\d{2})[./-](\d{4})', full_text)
    
    if date_match:
        d, m, y = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
    else:
        now = datetime.datetime.now()
        d, m, y = now.day, now.month, now.year

    # 2. Parse Lottery Name
    lottery_name = ""
    title_upper = title.upper()
    for name in LOTTERY_NAMES:
        if name in title_upper:
            lottery_name = name
            break

    # 3. Parse Lottery Code (e.g. SK 67, SM 70)
    code_match = re.search(r'\b([A-Z]{1,3})[-.\s]*(\d{2,4})\b', title) or \
                 re.search(r'\b([A-Z]{1,3})[-.\s]*(\d{2,4})\b', full_text)
    code_str = f"{code_match.group(1)} {code_match.group(2)}" if code_match else ""

    if not lottery_name:
        lottery_name = "KERALA LOTTERY"

    # 4. Parse 1st Prize Money (Strictly pure words)
    prize_match = re.search(r'1st\s*Prize[^\n<:]*[:\s]*[₹Rs.]*([\d,]+)/-?\s*\[?([^\]\n<]+)?\]?', full_text, re.IGNORECASE)
    prize_money = "1 CRORE"
    if prize_match:
        bracket_val = prize_match.group(2)
        raw_num = prize_match.group(1)
        if bracket_val and any(k in bracket_val.lower() for k in ["crore", "lakh"]):
            prize_money = clean_prize_to_pure_words(bracket_val)
        elif raw_num:
            prize_money = clean_prize_to_pure_words(raw_num)
    else:
        if "1 Crore" in full_text or "1 crore" in full_text or "1 CRORE" in full_text:
            prize_money = "1 CRORE"
        elif "80 Lakh" in full_text or "80 lakh" in full_text:
            prize_money = "80 LAKHS"
        elif "75 Lakh" in full_text or "75 lakh" in full_text:
            prize_money = "75 LAKHS"

    return lottery_name, code_str, d, m, y, prize_money


# -------------------------------------------------------------
# BOT EXPORT FUNCTION (CALLABLE DIRECTLY FROM APP.PY)
# -------------------------------------------------------------
def generate_tri_thumbnails(lottery_title: str, draw_date_str: str, out_dir: str, prize_money_str: str = "1 CRORE"):
    """
    Renders 3 Thumbnails (English, Malayalam, Tamil) for Telegram Bot integration.
    """
    date_match = re.search(r'(\d{2})[./-](\d{2})[./-](\d{4})', draw_date_str)
    if date_match:
        d, m, y = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
    else:
        now = datetime.datetime.now()
        d, m, y = now.day, now.month, now.year

    date_file_tag = f"{d:02d}-{m:02d}-{y}"

    lot_name_en = lottery_title.upper().strip()
    code_str = ""

    code_match = re.search(r'\b([A-Z]{1,3})[-.\s]*(\d{2,4})\b', lot_name_en)
    if code_match:
        code_str = f"{code_match.group(1)} {code_match.group(2)}"
        lot_name_en = lot_name_en.replace(code_match.group(0), "").strip()

    for name in LOTTERY_NAMES:
        if name in lot_name_en:
            lot_name_en = name
            break

    prize_en = clean_prize_to_pure_words(prize_money_str)

    # Background processing randomly from repo 'Lottery' folder
    cached_middle_rgb = None
    if os.path.exists(PICTURES_DIR):
        png_files = [f for f in os.listdir(PICTURES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if png_files:
            selected_png = random.choice(png_files)
            img_path = os.path.join(PICTURES_DIR, selected_png)
            photo_bgr = cv2.imread(img_path)
            if photo_bgr is not None:
                photo_resized = smart_resize_and_crop(photo_bgr, target_w=1280, target_h=300)
                hsv = cv2.cvtColor(photo_resized, cv2.COLOR_BGR2HSV).astype(np.float32)
                hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.25, 0, 255)
                enhanced_bgr = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
                kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
                sharpened_bgr = cv2.filter2D(enhanced_bgr, -1, kernel)
                cached_middle_rgb = cv2.cvtColor(sharpened_bgr, cv2.COLOR_BGR2RGB)

    # 1. English Setup
    en_text1 = f"{lot_name_en} {code_str}".strip()
    en_date = f"{d} {ENGLISH_MONTHS.get(m, 'AUGUST')} {y}"
    en_suffix = "RESULT"
    en_text3 = f"1ST PRIZE: ₹{prize_en}"
    en_text4 = "WATCH OFFICIAL FULL RESULT"
    font_en = get_font_path("en")

    # 2. Malayalam Setup
    ml_lot_name = LOTTERY_NAMES_MALAYALAM.get(lot_name_en, lot_name_en)
    ml_text1 = f"{ml_lot_name} {code_str}".strip()
    ml_date = f"{d} {MALAYALAM_MONTHS.get(m, 'ആഗസ്റ്റ്')} {y}"
    ml_suffix = "ഫലം"
    ml_text3 = f"ഒന്നാം സമ്മാനം: {convert_prize_to_malayalam(prize_en)}"
    ml_text4 = "ഔദ്യോഗിക ഫലം അറിയാം"
    font_ml = get_font_path("ml")

    # 3. Tamil Setup
    if lot_name_en in LOTTERY_NAMES_TAMIL:
        ta_lot_name = LOTTERY_NAMES_TAMIL[lot_name_en]
    else:
        ta_lot_name = transliterate_to_tamil(lot_name_en)
    ta_text1 = f"{ta_lot_name} {code_str}".strip()
    ta_date = f"{d} {TAMIL_MONTHS.get(m, 'ஆகஸ்ட்')} {y}"
    ta_suffix = "முடிவுகள்"
    ta_text3 = f"முதல் பரிசு: {convert_prize_to_tamil(prize_en)}"
    ta_text4 = "அதிகாரப்பூர்வ முடிவுகளைக் காண்க!"
    font_ta = get_font_path("ta")

    clean_lottery_tag = re.sub(r'[^A-Za-z0-9_-]', '_', en_text1)

    path_en = os.path.join(out_dir, f"thumbnail_EN_{clean_lottery_tag}_{date_file_tag}.png")
    path_ml = os.path.join(out_dir, f"thumbnail_ML_{clean_lottery_tag}_{date_file_tag}.png")
    path_ta = os.path.join(out_dir, f"thumbnail_TA_{clean_lottery_tag}_{date_file_tag}.png")

    out_en = render_thumbnail(en_text1, en_date, en_suffix, en_text3, en_text4, font_en, path_en, cached_middle_rgb)
    out_ml = render_thumbnail(ml_text1, ml_date, ml_suffix, ml_text3, ml_text4, font_ml, path_ml, cached_middle_rgb)
    out_ta = render_thumbnail(ta_text1, ta_date, ta_suffix, ta_text3, ta_text4, font_ta, path_ta, cached_middle_rgb)

    return {
        "en": out_en,
        "ml": out_ml,
        "ta": out_ta
    }


# -------------------------------------------------------------
# STANDALONE CLI RUNNER
# -------------------------------------------------------------
def main():
    os.system("clear")
    print("\033[96m╔══════════════════════════════════════════════════════════════════════╗\033[0m")
    print("\033[96m║     KERALA LOTTERY 3-LANGUAGE THUMBNAIL GENERATOR (EN / ML / TA)     ║\033[0m")
    print("\033[96m╚══════════════════════════════════════════════════════════════════════╝\033[0m\n")

    print("📡 Fetching latest lottery results from Blogger API...")
    feed_data = fetch_live_feed()
    if not feed_data or "feed" not in feed_data:
        print("\033[91m❌ Failed to parse feed payload.\033[0m")
        return

    raw_entries = feed_data["feed"].get("entry", [])
    valid_entries = []

    for entry in raw_entries:
        post_url = ""
        for link in entry.get("link", []):
            if link.get("rel") == "alternate":
                post_url = link.get("href", "")
                break

        if "today-kerala-lottery-result-live.html" in post_url:
            continue

        title = entry.get("title", {}).get("$t", "Untitled")
        content = entry.get("content", {}).get("$t", "") or entry.get("summary", {}).get("$t", "")

        lottery_name, code_str, d, m, y, prize_money = parse_lottery_entry(title, content)
        valid_entries.append({
            "lottery_name": lottery_name,
            "code_str": code_str,
            "day": d,
            "month": m,
            "year": y,
            "prize_money": prize_money,
            "title": title
        })

    if not valid_entries:
        print("\033[91m⚠️ No valid lottery results found.\033[0m")
        return

    print(f"\033[92m✅ Found {len(valid_entries)} recent lottery results:\033[0m\n")
    print("\033[94m" + "─" * 70 + "\033[0m")

    for i, item in enumerate(valid_entries, 1):
        lottery_full = f"{item['lottery_name']} {item['code_str']}".strip()
        date_display = f"{item['day']:02d}-{item['month']:02d}-{item['year']}"
        print(f"\033[1m[{i}]\033[0m \033[93m{lottery_full}\033[0m | 📅 \033[92m{date_display}\033[0m | 🏆 \033[95m₹{item['prize_money']}\033[0m")

    print("\033[94m" + "─" * 70 + "\033[0m\n")

    selected_idx = None
    while True:
        user_input = input(f"\033[1m👉 Select lottery number (1-{len(valid_entries)}) or 'q' to quit: \033[0m").strip()
        if user_input.lower() == 'q':
            print("Exiting.")
            sys.exit(0)
        if user_input.isdigit():
            val = int(user_input)
            if 1 <= val <= len(valid_entries):
                selected_idx = val - 1
                break
        print("\033[91mInvalid selection. Please enter a valid number.\033[0m")

    chosen = valid_entries[selected_idx]
    d, m, y = chosen["day"], chosen["month"], chosen["year"]
    lot_name_en = chosen["lottery_name"]
    code_str = chosen["code_str"]
    prize_en = chosen["prize_money"]
    date_file_tag = f"{d:02d}-{m:02d}-{y}"

    # 1. PROCESS BACKGROUND IMAGE FROM 'Lottery' REPO FOLDER
    cached_middle_rgb = None
    if os.path.exists(PICTURES_DIR):
        png_files = [f for f in os.listdir(PICTURES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if png_files:
            selected_png = random.choice(png_files)
            img_path = os.path.join(PICTURES_DIR, selected_png)
            photo_bgr = cv2.imread(img_path)
            if photo_bgr is not None:
                photo_resized = smart_resize_and_crop(photo_bgr, target_w=1280, target_h=300)
                hsv = cv2.cvtColor(photo_resized, cv2.COLOR_BGR2HSV).astype(np.float32)
                hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.25, 0, 255)
                enhanced_bgr = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
                kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
                sharpened_bgr = cv2.filter2D(enhanced_bgr, -1, kernel)
                cached_middle_rgb = cv2.cvtColor(sharpened_bgr, cv2.COLOR_BGR2RGB)

    # 2. ASSEMBLE TEXT FOR ALL 3 LANGUAGES
    en_text1 = f"{lot_name_en} {code_str}".strip()
    en_date = f"{d} {ENGLISH_MONTHS.get(m, 'AUGUST')} {y}"
    en_suffix = "RESULT"
    en_text3 = f"1ST PRIZE: ₹{prize_en}"
    en_text4 = "WATCH OFFICIAL FULL RESULT"
    font_en = get_font_path("en")

    ml_lot_name = LOTTERY_NAMES_MALAYALAM.get(lot_name_en, lot_name_en)
    ml_text1 = f"{ml_lot_name} {code_str}".strip()
    ml_date = f"{d} {MALAYALAM_MONTHS.get(m, 'ആഗസ്റ്റ്')} {y}"
    ml_suffix = "ഫലം"
    ml_text3 = f"ഒന്നാം സമ്മാനം: {convert_prize_to_malayalam(prize_en)}"
    ml_text4 = "ഔദ്യോഗിക ഫലം അറിയാം"
    font_ml = get_font_path("ml")

    if lot_name_en in LOTTERY_NAMES_TAMIL:
        ta_lot_name = LOTTERY_NAMES_TAMIL[lot_name_en]
    else:
        ta_lot_name = transliterate_to_tamil(lot_name_en)
    ta_text1 = f"{ta_lot_name} {code_str}".strip()
    ta_date = f"{d} {TAMIL_MONTHS.get(m, 'ஆகஸ்ட்')} {y}"
    ta_suffix = "முடிவுகள்"
    ta_text3 = f"முதல் பரிசு: {convert_prize_to_tamil(prize_en)}"
    ta_text4 = "அதிகாரப்பூர்வ முடிவுகளைக் காண்க!"
    font_ta = get_font_path("ta")

    clean_lottery_tag = re.sub(r'[^A-Za-z0-9_-]', '_', en_text1)

    path_en = os.path.join(DOWNLOAD_DIR, f"thumbnail_EN_{clean_lottery_tag}_{date_file_tag}.png")
    path_ml = os.path.join(DOWNLOAD_DIR, f"thumbnail_ML_{clean_lottery_tag}_{date_file_tag}.png")
    path_ta = os.path.join(DOWNLOAD_DIR, f"thumbnail_TA_{clean_lottery_tag}_{date_file_tag}.png")

    print("\n\033[96m🎨 Rendering Tri-Language Thumbnails...\033[0m")

    out_en = render_thumbnail(en_text1, en_date, en_suffix, en_text3, en_text4, font_en, path_en, cached_middle_rgb)
    out_ml = render_thumbnail(ml_text1, ml_date, ml_suffix, ml_text3, ml_text4, font_ml, path_ml, cached_middle_rgb)
    out_ta = render_thumbnail(ta_text1, ta_date, ta_suffix, ta_text3, ta_text4, font_ta, path_ta, cached_middle_rgb)

    print("\n\033[92m" + "═" * 72 + "\033[0m")
    print("\033[92m✨ SUCCESS! 3 Thumbnails Generated and Saved:\033[0m")
    if out_en:
        print(f"\033[93m🇬🇧 [English]   : {out_en}\033[0m")
    if out_ml:
        print(f"\033[93m🌴 [Malayalam] : {out_ml}\033[0m")
    if out_ta:
        print(f"\033[93m🛕 [Tamil]     : {out_ta}\033[0m")
    print("\033[92m" + "═" * 72 + "\033[0m\n")


if __name__ == "__main__":
    main()
