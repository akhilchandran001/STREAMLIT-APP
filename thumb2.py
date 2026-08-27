import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_thumbnail(lottery_title: str, draw_date: str, output_path: str):
    # --- 1. SETTINGS & PATHS ---
    logo_path = os.path.join(BASE_DIR, "Logo.png")
    font_anton = os.path.join(BASE_DIR, "Anton-Regular.ttf")
    font_montserrat = os.path.join(BASE_DIR, "Montserrat-Bold.ttf")

    width, height = 1280, 720

    # --- 2. GENERATE BACKGROUND (OPENCV) ---
    img_array = np.zeros((height, width, 3), dtype=np.uint8)
    
    # BGR Colors
    color_red_bgr = (30, 10, 250)
    color_white_bgr = (255, 255, 255)
    color_yellow_bgr = (0, 235, 255)

    # 4 Bands
    cv2.rectangle(img_array, (0, 0), (width, 140), color_red_bgr, -1)      
    cv2.rectangle(img_array, (0, 140), (width, 340), color_white_bgr, -1)  
    cv2.rectangle(img_array, (0, 340), (width, 540), color_red_bgr, -1)    
    cv2.rectangle(img_array, (0, 540), (width, 720), color_yellow_bgr, -1) 

    img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)

    # --- 3. ADD LOGO (TOP-LEFT WITH DROP SHADOW) ---
    logo_width_offset = 20
    try:
        logo = Image.open(logo_path).convert("RGBA")
        
        # High-quality resizing using LANCZOS
        logo_size = 130
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        
        # Soft blurred drop shadow behind the logo
        shadow = Image.new("RGBA", logo.size, (0, 0, 0, 0))
        shadow_mask = logo.split()[3]
        shadow.paste((0, 0, 0, 160), (0, 0), mask=shadow_mask)
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=4))
        
        logo_x, logo_y = 15, 5
        pil_img.paste(shadow, (logo_x + 3, logo_y + 3), shadow)
        pil_img.paste(logo, (logo_x, logo_y), logo)
        
        logo_width_offset = logo_x + logo_size + 15
    except FileNotFoundError:
        print(f"⚠️ Logo not found at {logo_path}. Skipping logo.")

    # --- 4. PREPARE TEXT & SHADOW HELPERS ---
    draw = ImageDraw.Draw(pil_img)
    today_date = datetime.now().strftime("%d/%m/%Y")
    current_day = datetime.now().strftime("%A").upper()

    text_white = (255, 255, 255)
    text_red = (250, 10, 30)
    text_black = (0, 0, 0)
    shadow_color = (0, 0, 0, 180)

    def auto_fit_font(text, font_path, max_width, max_size):
        try:
            current_size = max_size
            font = ImageFont.truetype(font_path, current_size)
            while True:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                if text_width <= max_width or current_size <= 20:
                    break
                current_size -= 2
                font = ImageFont.truetype(font_path, current_size)
            return font
        except OSError:
            return ImageFont.load_default()

    def draw_smart_text(text, font_path, color, y_center, x_start, x_end, max_start_size, shadow=True, shadow_offset=(3, 3)):
        max_width = (x_end - x_start) - 30
        font = auto_fit_font(text, font_path, max_width, max_start_size)
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = x_start + ((x_end - x_start - text_width) // 2)
        y = y_center - (text_height // 2) - bbox[1]
        
        if shadow:
            draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, fill=shadow_color, font=font)
        draw.text((x, y), text, fill=color, font=font)

    # --- 5. RENDER STANDARD TEXT LINES ---

    # Line 1: Top Red Stripe
    draw_smart_text("KERALA LOTTERY RESULT", font_montserrat, text_white, 
                    y_center=70, x_start=logo_width_offset, x_end=width, max_start_size=75, shadow=True)

    # Line 2: Middle White Stripe
    draw_smart_text(lottery_title.upper().strip(), font_anton, text_red, 
                    y_center=240, x_start=0, x_end=width, max_start_size=150, shadow=False)

    # Line 3: Middle Red Stripe
    draw_smart_text(today_date, font_montserrat, text_white, 
                    y_center=440, x_start=0, x_end=width, max_start_size=140, shadow=True)

    # Line 4: Top of Yellow Stripe (WATCH FULL RESULT)
    draw_smart_text("WATCH FULL RESULT", font_montserrat, text_black, 
                    y_center=590, x_start=0, x_end=width, max_start_size=55, shadow=False)

    # --- 6. RENDER CUSTOM LIVE ICON & DAY RESULT (LINE 5) ---
    y_center_line5 = 665
    day_text = f"{current_day} RESULT"
    
    # 6a. Measure text and icon dimensions
    day_font = auto_fit_font(day_text, font_montserrat, 800, 60)
    day_bbox = draw.textbbox((0, 0), day_text, font=day_font)
    day_w = day_bbox[2] - day_bbox[0]
    day_h = day_bbox[3] - day_bbox[1]

    icon_w = 140
    icon_h = 50
    spacing = 20
    total_w = icon_w + spacing + day_w
    
    start_x = (width - total_w) // 2
    
    # 6b. Draw Red LIVE Pill Badge
    icon_x = start_x
    icon_y = y_center_line5 - (icon_h // 2)
    # Red background for icon
    draw.rounded_rectangle([icon_x, icon_y, icon_x + icon_w, icon_y + icon_h], radius=12, fill=(230, 20, 20))
    
    # White pulsing dot
    dot_size = 14
    dot_x = icon_x + 15
    dot_y = icon_y + (icon_h - dot_size) // 2
    draw.ellipse([dot_x, dot_y, dot_x + dot_size, dot_y + dot_size], fill="white")
    
    # "LIVE" text inside pill
    try:
        live_font = ImageFont.truetype(font_montserrat, 28)
    except OSError:
        live_font = ImageFont.load_default()
        
    live_bbox = draw.textbbox((0, 0), "LIVE", font=live_font)
    live_y = icon_y + (icon_h - (live_bbox[3] - live_bbox[1])) // 2 - live_bbox[1]
    draw.text((dot_x + dot_size + 10, live_y), "LIVE", fill="white", font=live_font)
    
    # 6c. Draw "DAY RESULT" Text next to icon
    text_x = icon_x + icon_w + spacing
    text_y = y_center_line5 - (day_h // 2) - day_bbox[1]
    draw.text((text_x, text_y), day_text, fill=text_black, font=day_font)

    # --- 7. SAVE OUTPUT ---
    try:
        pil_img.save(output_path)
        print(f"✅ Masterpiece successfully generated and saved to: {output_path}")
    except PermissionError:
        print("❌ Permission Error: Ensure storage permissions are granted.")

    return output_path

if __name__ == "__main__":
    generate_thumbnail("SREE SAKTHI SS-534", "today", os.path.join(BASE_DIR, "thumbnail_final.png"))
