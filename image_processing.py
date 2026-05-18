import cv2
import numpy as np

def process_image(path):
    """
    Loads image, processes it for plotting (resize, edge detect, simplify, sort).
    Returns a list of optimized contours.
    """
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Image not found or could not be opened.")

    # 1. Resize/Pad to canvas (keep 200 as base logical unit for now)
    # Higher res here = better details before simplification
    CANVAS_SIZE = 400 # Increased from 200 for better precision
    h, w = img.shape
    scale = min(CANVAS_SIZE / w, CANVAS_SIZE / h)
    new_w, new_h = int(w * scale), int(h * scale)
    
    if new_w == 0 or new_h == 0: return []

    resized_img = cv2.resize(img, (new_w, new_h))
    
    # Pad to center
    top = (CANVAS_SIZE - new_h) // 2
    bottom = CANVAS_SIZE - new_h - top
    left = (CANVAS_SIZE - new_w) // 2
    right = CANVAS_SIZE - new_w - left
    
    padded_img = cv2.copyMakeBorder(
        resized_img, top, bottom, left, right,
        cv2.BORDER_CONSTANT, value=255
    )

    # 2. Pre-process (Blur to reduce noise)
    blurred = cv2.GaussianBlur(padded_img, (3, 3), 0)

    # 3. Edge Detection (Auto-tune or safer thresholds)
    # Using wide hysteresis for cleaner lines
    edges = cv2.Canny(blurred, 80, 200)

    # 4. Find Contours
    # RETR_LIST gets all curves. RETR_EXTERNAL only gets outer boundary.
    # Use RETR_LIST for detailed drawings.
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # 5. Optimize Contours
    optimized_contours = []
    
    for cnt in contours:
        # A. Filter small noise (e.g. length < 1% of canvas)
        if cv2.arcLength(cnt, False) < (CANVAS_SIZE * 0.02):
            continue
            
        # B. Simplify (Douglas-Peucker)
        # Epsilon is error tolerance. Higher = simpler shapes.
        epsilon = 0.002 * cv2.arcLength(cnt, False) # Adaptive epsilon
        approx = cv2.approxPolyDP(cnt, epsilon, False)
        
        # C. Re-scale back to 200 reference if needed?
        # Main.py assumes 200? The scaling factor in main.py is calculated based on canvas?
        # Wait, main.py splits bounds. If I change CANVAS_SIZE to 400, I must scale back to 200
        # to match main.py's expected coordinates logic (if it assumes 0-200).
        # Let's scale back to ensure compatibility.
        
        scaled_cnt = (approx * (200.0 / CANVAS_SIZE)).astype(np.int32)
        optimized_contours.append(scaled_cnt)

    # 6. Sort Paths (Simple Traveling Salesperson)
    # Minimize air-travel distance
    if not optimized_contours:
        return []
        
    sorted_contours = []
    curr_pos = np.array([0, 0]) # Pen starts at 0,0
    
    # Simple greedy sort
    # Copy listing to consume
    pool = optimized_contours[:]
    
    while pool:
        # Find nearest start point
        nearest_idx = 0
        min_dist = float('inf')
        
        for i, cnt in enumerate(pool):
            # Start of contour
            start_pt = cnt[0][0] # [[x,y]] -> [x,y]
            dist = np.linalg.norm(curr_pos - start_pt)
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i
        
        # Move to that contour
        best_cnt = pool.pop(nearest_idx)
        sorted_contours.append(best_cnt)
        # Update current pos to END of that contour
        curr_pos = best_cnt[-1][0]

    return sorted_contours