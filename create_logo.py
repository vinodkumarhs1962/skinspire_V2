"""
Intelli-Clinic Logo Generator
Creates professional logos combining healthcare and intelligence themes
"""

from PIL import Image, ImageDraw, ImageFont
import math
import os

def create_intelli_clinic_logo():
    """Create multiple logo variations for Intelli-Clinic"""

    # Logo 1: Modern Icon with Brain + Medical Cross
    create_logo_variant_1()

    # Logo 2: Circuit/Neural Network style
    create_logo_variant_2()

    # Logo 3: Minimalist with IC monogram
    create_logo_variant_3()

    # Logo 4: Full horizontal logo with text
    create_logo_variant_4()

    print("All logo variants created successfully!")

def create_logo_variant_1():
    """Brain + Medical Cross - Intelligence meets Healthcare"""
    size = 800
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    center = size // 2

    # Colors
    primary_blue = (0, 120, 180)      # Healthcare blue
    accent_teal = (0, 180, 170)       # Intelligence teal
    dark_blue = (20, 60, 100)         # Text color

    # Draw outer circle (gradient effect with concentric circles)
    for i in range(20):
        r = 340 - i * 2
        alpha = 255 - i * 8
        color = (0, 120 + i * 3, 180 + i * 2, alpha)
        draw.ellipse([center - r, center - r, center + r, center + r],
                     fill=color, outline=None)

    # Inner white circle
    draw.ellipse([center - 280, center - 280, center + 280, center + 280],
                 fill=(255, 255, 255, 255))

    # Draw stylized brain outline (left hemisphere)
    brain_points_left = []
    for angle in range(90, 270):
        rad = math.radians(angle)
        # Create wavy brain-like shape
        wave = 15 * math.sin(angle * 0.15) + 10 * math.cos(angle * 0.25)
        r = 180 + wave
        x = center - 20 + r * math.cos(rad)
        y = center + r * math.sin(rad)
        brain_points_left.append((x, y))

    # Draw brain curves
    draw.line(brain_points_left, fill=primary_blue, width=8)

    # Brain folds (left)
    for i, offset in enumerate([-60, 0, 60]):
        start_y = center + offset
        curve_points = []
        for x in range(-100, 10, 5):
            wave = 20 * math.sin(x * 0.08)
            curve_points.append((center + x - 50, start_y + wave))
        draw.line(curve_points, fill=accent_teal, width=4)

    # Medical cross on right side (intelligence processing)
    cross_center_x = center + 80
    cross_center_y = center
    cross_size = 100
    cross_width = 35

    # Vertical bar of cross
    draw.rounded_rectangle([cross_center_x - cross_width//2, cross_center_y - cross_size,
                           cross_center_x + cross_width//2, cross_center_y + cross_size],
                          radius=10, fill=accent_teal)

    # Horizontal bar of cross
    draw.rounded_rectangle([cross_center_x - cross_size, cross_center_y - cross_width//2,
                           cross_center_x + cross_size, cross_center_y + cross_width//2],
                          radius=10, fill=accent_teal)

    # Neural connection dots
    dot_positions = [
        (center - 150, center - 100),
        (center - 180, center),
        (center - 150, center + 100),
        (center - 80, center - 150),
        (center - 80, center + 150),
    ]

    for pos in dot_positions:
        draw.ellipse([pos[0] - 12, pos[1] - 12, pos[0] + 12, pos[1] + 12],
                     fill=primary_blue)
        # Connection line to cross
        draw.line([pos, (cross_center_x - cross_size, cross_center_y)],
                  fill=(*primary_blue, 100), width=2)

    img.save('IntelliClinic_Logo_v1.png', 'PNG')
    print("Created: IntelliClinic_Logo_v1.png (Brain + Cross)")

def create_logo_variant_2():
    """Neural Network / Circuit Board style"""
    size = 800
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    center = size // 2

    # Colors
    primary = (0, 150, 180)       # Teal
    secondary = (100, 200, 220)   # Light teal
    accent = (255, 120, 80)       # Coral accent
    dark = (30, 60, 90)

    # Outer hexagon (tech feel)
    hex_radius = 350
    hex_points = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        x = center + hex_radius * math.cos(angle)
        y = center + hex_radius * math.sin(angle)
        hex_points.append((x, y))

    draw.polygon(hex_points, fill=(240, 250, 255), outline=primary)

    # Inner circle
    draw.ellipse([center - 250, center - 250, center + 250, center + 250],
                 fill=(255, 255, 255), outline=primary, width=4)

    # Central "IC" stylized as circuit
    # Draw I
    draw.rounded_rectangle([center - 100, center - 120, center - 50, center + 120],
                          radius=15, fill=primary)

    # Draw C with circuit nodes
    c_points = []
    for angle in range(45, 316):
        rad = math.radians(angle)
        r = 110
        x = center + 60 + r * math.cos(rad)
        y = center + r * math.sin(rad)
        c_points.append((x, y))

    draw.line(c_points, fill=primary, width=50)

    # Circuit nodes around
    node_positions = [
        (center - 200, center - 150, secondary),
        (center - 200, center + 150, secondary),
        (center + 220, center - 150, accent),
        (center + 220, center + 150, accent),
        (center, center - 220, primary),
        (center, center + 220, primary),
    ]

    for x, y, color in node_positions:
        # Node circle
        draw.ellipse([x - 20, y - 20, x + 20, y + 20], fill=color)
        draw.ellipse([x - 10, y - 10, x + 10, y + 10], fill=(255, 255, 255))

    # Connection lines (circuit traces)
    draw.line([(center - 200, center - 150), (center - 100, center - 80)], fill=secondary, width=3)
    draw.line([(center - 200, center + 150), (center - 100, center + 80)], fill=secondary, width=3)
    draw.line([(center + 220, center - 150), (center + 150, center - 80)], fill=accent, width=3)
    draw.line([(center + 220, center + 150), (center + 150, center + 80)], fill=accent, width=3)

    # Pulse/heartbeat line through center
    pulse_points = []
    for x in range(-180, 181, 10):
        if -30 < x < 30:
            # Heartbeat spike
            if x < 0:
                y = (x + 30) * -3
            else:
                y = (30 - x) * -3
        else:
            y = 10 * math.sin(x * 0.1)
        pulse_points.append((center + x, center + y))

    draw.line(pulse_points, fill=accent, width=4)

    img.save('IntelliClinic_Logo_v2.png', 'PNG')
    print("Created: IntelliClinic_Logo_v2.png (Circuit Style)")

def create_logo_variant_3():
    """Minimalist IC Monogram with Stethoscope hint"""
    size = 800
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    center = size // 2

    # Colors - Modern gradient feel
    primary = (0, 130, 170)      # Deep teal
    light = (80, 200, 210)       # Light teal

    # Background circle
    draw.ellipse([center - 350, center - 350, center + 350, center + 350],
                 fill=primary)

    # Inner lighter circle
    draw.ellipse([center - 300, center - 300, center + 300, center + 300],
                 fill=(255, 255, 255))

    # Stylized "i" - with dot as pulse indicator
    # Stem of i
    draw.rounded_rectangle([center - 130, center - 80, center - 70, center + 150],
                          radius=20, fill=primary)

    # Dot of i (pulsing circle - like a vital sign)
    draw.ellipse([center - 130, center - 180, center - 70, center - 120],
                 fill=light)
    draw.ellipse([center - 115, center - 165, center - 85, center - 135],
                 fill=primary)

    # Stylized "C" wrapping around - like a stethoscope
    # Main C curve
    c_width = 45
    for angle in range(30, 331):
        rad = math.radians(angle)
        r = 160
        x = center + 50 + r * math.cos(rad)
        y = center + r * math.sin(rad)
        draw.ellipse([x - c_width//2, y - c_width//2, x + c_width//2, y + c_width//2],
                     fill=primary)

    # Stethoscope earpieces (small circles at C ends)
    end_angle1 = math.radians(30)
    end_angle2 = math.radians(330)

    for angle in [end_angle1, end_angle2]:
        x = center + 50 + 160 * math.cos(angle)
        y = center + 160 * math.sin(angle)
        draw.ellipse([x - 25, y - 25, x + 25, y + 25], fill=light)
        draw.ellipse([x - 15, y - 15, x + 15, y + 15], fill=(255, 255, 255))

    # Small cross inside the i dot
    dot_center_x = center - 100
    dot_center_y = center - 150
    draw.line([(dot_center_x - 8, dot_center_y), (dot_center_x + 8, dot_center_y)],
              fill=(255, 255, 255), width=3)
    draw.line([(dot_center_x, dot_center_y - 8), (dot_center_x, dot_center_y + 8)],
              fill=(255, 255, 255), width=3)

    img.save('IntelliClinic_Logo_v3.png', 'PNG')
    print("Created: IntelliClinic_Logo_v3.png (Minimalist IC)")

def create_logo_variant_4():
    """Full horizontal logo with icon and text"""
    width = 1600
    height = 500
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Colors
    primary = (0, 130, 170)
    accent = (0, 190, 180)
    dark = (40, 60, 80)

    # Icon on left (simplified version of logo 3)
    icon_center_x = 200
    icon_center_y = height // 2
    icon_radius = 180

    # Icon background
    draw.ellipse([icon_center_x - icon_radius, icon_center_y - icon_radius,
                  icon_center_x + icon_radius, icon_center_y + icon_radius],
                 fill=primary)

    # Inner circle
    inner_r = 150
    draw.ellipse([icon_center_x - inner_r, icon_center_y - inner_r,
                  icon_center_x + inner_r, icon_center_y + inner_r],
                 fill=(255, 255, 255))

    # Simplified IC
    # I
    draw.rounded_rectangle([icon_center_x - 70, icon_center_y - 40,
                           icon_center_x - 40, icon_center_y + 80],
                          radius=10, fill=primary)
    draw.ellipse([icon_center_x - 70, icon_center_y - 90,
                  icon_center_x - 40, icon_center_y - 60],
                 fill=accent)

    # C
    c_r = 80
    for angle in range(45, 316):
        rad = math.radians(angle)
        x = icon_center_x + 30 + c_r * math.cos(rad)
        y = icon_center_y + c_r * math.sin(rad)
        draw.ellipse([x - 15, y - 15, x + 15, y + 15], fill=primary)

    # Text "Intelli-Clinic"
    # Try to use a system font
    try:
        # Try different font options
        font_paths = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        font = None
        font_bold = None
        for fp in font_paths:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, 100)
                font_bold = ImageFont.truetype(fp, 100)
                break
        if font is None:
            font = ImageFont.load_default()
            font_bold = font
    except:
        font = ImageFont.load_default()
        font_bold = font

    # Draw "Intelli" in primary color
    text_x = 420
    text_y = height // 2 - 60
    draw.text((text_x, text_y), "Intelli", fill=primary, font=font_bold)

    # Draw "-Clinic" in accent color
    # Measure "Intelli" width approximately
    draw.text((text_x + 320, text_y), "-Clinic", fill=accent, font=font)

    # Tagline
    try:
        small_font = ImageFont.truetype(font_paths[0] if os.path.exists(font_paths[0]) else font_paths[1], 32)
    except:
        small_font = ImageFont.load_default()

    draw.text((text_x, text_y + 120), "Intelligent Healthcare Management", fill=dark, font=small_font)

    img.save('IntelliClinic_Logo_Full.png', 'PNG')
    print("Created: IntelliClinic_Logo_Full.png (Full Logo with Text)")

    # Also create a simple square icon version
    create_app_icon()

def create_app_icon():
    """Create a simple square app icon"""
    size = 512
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    center = size // 2

    # Colors
    primary = (0, 130, 170)
    accent = (0, 190, 180)

    # Rounded square background
    draw.rounded_rectangle([20, 20, size - 20, size - 20], radius=80, fill=primary)

    # Inner white circle
    inner_r = 180
    draw.ellipse([center - inner_r, center - inner_r, center + inner_r, center + inner_r],
                 fill=(255, 255, 255))

    # IC monogram
    # I
    draw.rounded_rectangle([center - 80, center - 50, center - 45, center + 90],
                          radius=12, fill=primary)
    draw.ellipse([center - 80, center - 110, center - 45, center - 75], fill=accent)

    # Small cross in dot
    dot_cx, dot_cy = center - 62, center - 92
    draw.line([(dot_cx - 8, dot_cy), (dot_cx + 8, dot_cy)], fill=(255, 255, 255), width=3)
    draw.line([(dot_cx, dot_cy - 8), (dot_cx, dot_cy + 8)], fill=(255, 255, 255), width=3)

    # C
    c_r = 90
    for angle in range(40, 321):
        rad = math.radians(angle)
        x = center + 35 + c_r * math.cos(rad)
        y = center + c_r * math.sin(rad)
        draw.ellipse([x - 18, y - 18, x + 18, y + 18], fill=primary)

    img.save('IntelliClinic_AppIcon.png', 'PNG')
    print("Created: IntelliClinic_AppIcon.png (App Icon 512x512)")

if __name__ == "__main__":
    create_intelli_clinic_logo()
