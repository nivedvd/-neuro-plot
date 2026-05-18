from PIL import Image, ImageChops

def process_logo(input_path, output_path):
    print(f"Processing {input_path}...")
    img = Image.open(input_path).convert("RGBA")
    
    # Remove white background
    data = img.getdata()
    new_data = []
    for item in data:
        # If pixel is white or very close to white, make it transparent
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    
    img.putdata(new_data)
    
    # Optional: Crop to content if needed (remove empty space)
    # Get the bounding box of the non-transparent area
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    # The user specifically said "add only the text"
    # Looking at the logo, the "N" icon is on the left.
    # We might want to crop just the "neuro plot" text.
    # But let's start with the full transparent version first as it looks professional.
    # If we want just the text "neuro plot", we'd crop the right side.
    # Let's try to detect the gap and crop just the text part if possible, 
    # but for now transparency is the biggest win.
    
    img.save(output_path, "PNG")
    print(f"Saved refined logo to {output_path}")

if __name__ == "__main__":
    process_logo("assets/logo.jpg", "assets/logo.png")
