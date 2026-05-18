
# A simple vector font for generating handwriting-style strokes
FONT = {
    'A': [(0, 20), (5, -20), (5, 0), (5, 20), (-10, 0)],
    'B': [(0, 20), (5, -2.5), (2.5, -2.5), (-5, 0), (7.5, -5), (0, -10), (-10, 0)],
    'C': [(10, 20), (-10, 0), (0, -20), (10, 0)],
    'D': [(0, 20), (5, -5), (5, -10), (-10, 0), (0, 20)],
    'E': [(10, 20), (-10, 0), (0, -10), (5, 0), (-5, 0), (0, -10), (10, 0)],
    'F': [(10, 20), (-10, 0), (0, -10), (5, 0)],
    'G': [(10, 20), (-10, 0), (0, -20), (10, 0), (0, 5), (-5, 0)],
    'H': [(0, 20), (0, -10), (10, 0), (0, 10), (0, -20)],
    'I': [(0, 20), (0, -20)],
    'J': [(0, 20), (10, 0), (-5, -20), (-5, 0)],
    'K': [(0, 20), (0, -10), (10, 10), (-10, -10), (10, -10)],
    'L': [(0, 20), (0, -20), (10, 0)],
    'M': [(0, 20), (5, -10), (5, 10), (0, -20)],
    'N': [(0, 20), (10, -20), (0, 20)],
    'O': [(0, 20), (10, 0), (0, -20), (-10, 0)],
    'P': [(0, 20), (10, -5), (0, -5), (-10, 0)],
    'Q': [(0, 20), (10, 0), (0, -20), (-10, 0), (5, -5), (5, 5)],
    'R': [(0, 20), (10, -5), (0, -5), (-10, 0), (10, -10)],
    'S': [(10, 20), (-10, -5), (10, -5), (10, -10), (-10, 0)],
    'T': [(0, 20), (10, 0), (-20, 0), (10, 0), (0, -20)],
    'U': [(0, 20), (0, -20), (10, 0), (0, 20)],
    'V': [(0, 20), (5, -20), (5, 20)],
    'W': [(0, 20), (5, -20), (5, 20), (5, -20), (5, 20)],
    'X': [(0, 20), (10, -20), (-10, 0), (10, 20)],
    'Y': [(0, 20), (5, -10), (5, 10), (-10, 0), (5, -10)],
    'Z': [(10, 20), (-10, 0), (10, -20), (-10, 0)],
    ' ': [('MOVE', 15, 0)],
    # Numbers
    '0': [(0, 20), (10, 0), (0, -20), (-10, 0), (10, 20)],
    '1': [(5, 20), (-5, -5), (0, -15)],
    '2': [(0, 20), (10, 0), (0, -10), (-10, 0), (0, -10), (10, 0)],
    '3': [(0, 20), (10, -5), (-5, -5), (5, -5), (-10, -5)],
    '4': [(0, 20), (0, -10), (10, 0), (0, 10), (0, -20)],
    '5': [(10, 20), (-10, 0), (0, -10), (10, 0), (0, -10), (-10, 0)],
    '6': [(10, 20), (-10, 0), (0, -20), (10, 0), (0, 10), (-10, 0)],
    '7': [(0, 20), (10, 0), (-5, -20)],
    '8': [(5, 10), (5, -10), (-10, 0), (5, 10), (5, -10), (0, 20), (10, 0), (0, -20), (-10, 0)],
    '9': [(0, -20), (10, 0), (0, 20), (-10, 0), (0, -10), (10, 0)],
}

DEFAULT_CHAR = [(0, 20), (10, 0), (0, -20), (-10, 0)] # A box for unknown chars

def text_to_actions(text):
    """
    Convert text into a list of plotter actions using the vector font.
    
    Returns:
        List of actions: [('PEN_UP',), ('MOVE', dx, dy), ('PEN_DOWN',), ...]
    """
    actions = [('PEN_UP',)]
    
    # Logical pen position (where the pen currently IS)
    pen_x, pen_y = 0, 0
    
    # Cursor position (where the next character should START)
    # Start at Top-Left (Y=120) so we can wrap downwards without going negative
    cursor_x, cursor_y = 0, 120.0
    
    MAX_WIDTH = 130.0 
    LINE_HEIGHT = 16.0 # Compact line spacing (10mm text + 6mm gap)
    CHAR_SPACING = 8.0 
    SPACE_WIDTH = 6.0
    FONT_SCALE = 0.4

    for char in text.upper():
        if char == ' ':
            cursor_x += SPACE_WIDTH
            if cursor_x > MAX_WIDTH:
                cursor_x = 0
                cursor_y -= LINE_HEIGHT
            continue
        
        # Check wrapping
        if cursor_x > MAX_WIDTH:
            cursor_x = 0
            cursor_y -= LINE_HEIGHT
            
        strokes = FONT.get(char, DEFAULT_CHAR)
        if not strokes:
            continue
            
        # 1. Move to start
        move_to_start_x = cursor_x - pen_x
        move_to_start_y = cursor_y - pen_y
        
        if abs(move_to_start_x) > 0.01 or abs(move_to_start_y) > 0.01:
            actions.append(('MOVE', move_to_start_x, move_to_start_y))
            pen_x += move_to_start_x
            pen_y += move_to_start_y
            
        actions.append(('PEN_DOWN',))
        
        # 2. Draw strokes (SCALED)
        for dx, dy in strokes:
            if dx == 0 and dy == 0:
                actions.append(('PEN_UP',))
            else:
                # Apply Scale
                sdx = dx * FONT_SCALE
                sdy = dy * FONT_SCALE
                
                actions.append(('MOVE', sdx, sdy))
                pen_x += sdx
                pen_y += sdy
        
        actions.append(('PEN_UP',))
        
        # 3. Advance
        cursor_x += CHAR_SPACING
        
    return actions
