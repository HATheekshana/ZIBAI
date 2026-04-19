from PIL import Image
import io
from services.char_card import characters_card

async def team_card(uid, char_ids):
    # Original dimensions of your individual character card
    CARD_W, CARD_H = 1875, 890
    
    # 1. Fetch individual character images
    char_images = []
    for cid in char_ids:
        # Assuming characters_card returns a BytesIO object
        img_buffer = await characters_card(uid, cid, None)
        if img_buffer:
            if isinstance(img_buffer, bytes):
                img_buffer = io.BytesIO(img_buffer)
            img = Image.open(img_buffer)
            char_images.append(img)
    
    if not char_images:
        return None

    # 2. Determine grid layout (2x2)
    cols = 2
    rows = (len(char_images) + 1) // 2 
    
    # 3. Create canvas (Black background)
    canvas_w = CARD_W * cols
    canvas_h = CARD_H * rows
    combined_img = Image.new('RGB', (canvas_w, canvas_h), (0, 0, 0))
    
    # 4. Paste cards into grid
    for i, img in enumerate(char_images):
        col = i % cols
        row = i // cols
        combined_img.paste(img, (col * CARD_W, row * CARD_H))
    
    # 5. Resize for Telegram (Scale down to 50% for smaller file size)
    # 50% of (3750x1780) = 1875x890 (Very easy to send!)
    new_w = combined_img.width // 2
    new_h = combined_img.height // 2
    combined_img = combined_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # 6. Save to buffer
    output = io.BytesIO()
    combined_img.save(output, format="PNG", optimize=True, quality=85)
    output.seek(0)
    
    return output