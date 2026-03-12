"""
Create Equifidy iOS app icon from the logo colors.
The logo features a purple-orange-pink gradient swirl on black background.
"""
from PIL import Image, ImageDraw, ImageFont
import math

SIZE = 1024
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
draw = ImageDraw.Draw(img)

cx, cy = SIZE // 2, SIZE // 2 - 20  # Slightly above center

# ── Draw the stylized 'e' swirl matching the Equifidy logo ──
# The logo has a circular swirl with purple (top-left), orange (top-right),
# pink/magenta (bottom), with a gap creating an 'e' shape

def gradient_color(t):
    """Purple → Orange → Pink gradient (0 to 1)."""
    if t < 0.33:
        s = t / 0.33
        return (
            int(130 * (1-s) + 245 * s),  # purple R → orange R
            int(50 * (1-s) + 150 * s),   # purple G → orange G
            int(200 * (1-s) + 60 * s),   # purple B → orange B
        )
    elif t < 0.66:
        s = (t - 0.33) / 0.33
        return (
            int(245 * (1-s) + 255 * s),  # orange R → pink R
            int(150 * (1-s) + 60 * s),   # orange G → pink G
            int(60 * (1-s) + 160 * s),   # orange B → pink B
        )
    else:
        s = (t - 0.66) / 0.34
        return (
            int(255 * (1-s) + 130 * s),  # pink R → purple R
            int(60 * (1-s) + 50 * s),    # pink G → purple G
            int(160 * (1-s) + 200 * s),  # pink B → purple B
        )

# Draw outer ring (the circle part of the 'e')
outer_r = 340
ring_width = 100

for angle_deg in range(0, 360):
    if 330 <= angle_deg or angle_deg <= 300:  # Gap for the 'e' opening
        angle = math.radians(angle_deg)
        t = angle_deg / 360.0
        r, g, b = gradient_color(t)

        for dr in range(-ring_width//2, ring_width//2):
            radius = outer_r + dr
            x = int(cx + radius * math.cos(angle))
            y = int(cy + radius * math.sin(angle))
            if 0 <= x < SIZE and 0 <= y < SIZE:
                # Anti-aliasing at edges
                edge_dist = abs(dr) - (ring_width//2 - 2)
                if edge_dist > 0:
                    alpha = max(0, 255 - edge_dist * 80)
                else:
                    alpha = 255
                existing = img.getpixel((x, y))
                if alpha >= existing[3]:
                    img.putpixel((x, y), (r, g, b, alpha))

# Draw inner spiral (the curved part inside the 'e')
inner_r = 180
inner_width = 80

for angle_deg in range(180, 420):  # Wraps around
    actual_deg = angle_deg % 360
    angle = math.radians(actual_deg)
    t = actual_deg / 360.0
    r, g, b = gradient_color(t)

    # Spiral: radius decreases as angle increases
    progress = (angle_deg - 180) / 240.0
    radius = inner_r + progress * 60

    for dr in range(-inner_width//2, inner_width//2):
        cur_r = radius + dr
        x = int(cx + cur_r * math.cos(angle))
        y = int(cy + cur_r * math.sin(angle))
        if 0 <= x < SIZE and 0 <= y < SIZE:
            edge_dist = abs(dr) - (inner_width//2 - 2)
            alpha = max(0, 255 - max(0, edge_dist) * 80)
            existing = img.getpixel((x, y))
            if alpha >= existing[3]:
                img.putpixel((x, y), (r, g, b, alpha))

# Draw bottom-right square/rectangle (the pink-orange block in the logo)
block_left = cx - 20
block_top = cy + 80
block_right = cx + 280
block_bottom = cy + 380

for y in range(max(0, block_top), min(SIZE, block_bottom)):
    for x in range(max(0, block_left), min(SIZE, block_right)):
        ty = (y - block_top) / (block_bottom - block_top)
        tx = (x - block_left) / (block_right - block_left)
        t = (tx + ty) / 2
        # Orange top → Pink bottom
        r = int(245 * (1-t) + 255 * t)
        g = int(160 * (1-t) + 50 * t)
        b = int(60 * (1-t) + 160 * t)

        # Round bottom-left corner
        corner_r = 60
        dx = x - (block_left + corner_r)
        dy = y - (block_bottom - corner_r)
        if dx < 0 and dy > 0:
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > corner_r:
                continue

        # Don't overwrite the ring
        existing = img.getpixel((x, y))
        dist_from_center = math.sqrt((x - cx)**2 + (y - cy)**2)
        if dist_from_center < outer_r - ring_width//2 or dist_from_center > outer_r + ring_width//2:
            img.putpixel((x, y), (r, g, b, 255))

# Convert and save
img_rgb = img.convert("RGB")
base_path = "/Users/iamadarsha/Documents/breakoutscan/AntigravityScreener/AntigravityScreener/Assets.xcassets/AppIcon.appiconset"

img_rgb.save(f"{base_path}/icon_1024.png", "PNG")

sizes = [20, 29, 40, 58, 60, 76, 80, 87, 120, 152, 167, 180, 1024]
for s in sizes:
    resized = img_rgb.resize((s, s), Image.LANCZOS)
    resized.save(f"{base_path}/icon_{s}.png", "PNG")

# Also save for web (as favicon)
img_rgb.resize((192, 192), Image.LANCZOS).save("/Users/iamadarsha/Documents/breakoutscan/web/app/icon.png", "PNG")
img_rgb.resize((32, 32), Image.LANCZOS).save("/Users/iamadarsha/Documents/breakoutscan/web/app/favicon.ico", "PNG")

print(f"Generated {len(sizes)} iOS icon sizes + web favicon")
