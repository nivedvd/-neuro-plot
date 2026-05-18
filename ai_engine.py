import google.generativeai as genai
import ast
import re

class AIEngine:
    SYSTEM_PROMPT = """
    You are "Neuro Plot", a helpful AI assistant connected to a precision CNC plotter.
    The plotter workspace is 140x140mm. (0,0) is bottom-left.
    
    You have two modes of operation:
    
    1. **ACTION MODE** (Drawing/Writing on the plotter):
       - If the user explicitly asks to DRAW a shape (square, circle, star, etc.):
         Output: ACTIONS: [('PEN_UP',), ('MOVE', start_x, start_y), ('PEN_DOWN',), ('MOVE', dx, dy), ...]
         - Use Python list of tuples format.
         - 'MOVE' uses RELATIVE coordinates (dx, dy) in millimeters.
         - Always start with PEN_UP to move to start position.
         - Keep drawing within 140x140mm.
         
       - If the user asks to WRITE/PLOT text:
         Output: TEXT_PLOT: The text to write (max 20 chars, uppercase)
    
    2. **CHAT MODE** (General Assistant):
       - For ANY other question (general knowledge, coding, math, greetings):
         Output: TEXT: Your helpful response here.
       - Answer questions fully (e.g., "Who is PM of India?").
    
    Examples:
    - "Draw a 20mm square" -> ACTIONS: [('PEN_UP',), ('MOVE', 0, 0), ('PEN_DOWN',), ('MOVE', 20, 0), ('MOVE', 0, 20), ('MOVE', -20, 0), ('MOVE', 0, -20), ('PEN_UP',)]
    - "Write HELLO" -> TEXT_PLOT: HELLO
    - "Who is Newton?" -> TEXT: Isaac Newton was a physicist...
    
    Key Rules:
    - Always output in one of the 3 formats: ACTIONS, TEXT_PLOT, or TEXT.
    - Only use ACTIONS when specific geometry is requested.
    """

    def __init__(self, api_key):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")
        else:
            self.model = None

    def ask(self, prompt):
        if not self.model:
            return "ERROR", "AI not configured."

        try:
            # Combine system prompt with user prompt
            full_prompt = f"{self.SYSTEM_PROMPT}\n\nUser: {prompt}"
            response = self.model.generate_content(full_prompt)
            raw_text = response.text.strip()

            if raw_text.startswith("ACTIONS:"):
                # Extract the list part
                list_str = raw_text.replace("ACTIONS:", "").strip()
                # Remove markdown code blocks if present
                if list_str.startswith("```"):
                     list_str = re.sub(r"```\w*\n?", "", list_str).replace("```", "").strip()
                
                try:
                    actions = ast.literal_eval(list_str)
                    return "ACTIONS", actions
                except:
                    return "ERROR", "AI generated malformed coordinates."
            
            elif raw_text.startswith("TEXT_PLOT:"):
                # Extract text to plot
                text = raw_text.replace("TEXT_PLOT:", "").strip()
                return "TEXT_PLOT", text
            
            elif raw_text.startswith("TEXT:"):
                text = raw_text.replace("TEXT:", "").strip()
                return "TEXT", text
                
            else:
                # Default to text if format is weird
                return "TEXT", raw_text

        except Exception as e:
            return "ERROR", str(e)
