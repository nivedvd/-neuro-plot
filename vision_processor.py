"""
Gemini Vision Processor for Handwriting Analysis
Analyzes handwriting samples and generates custom vector fonts
"""
import google.generativeai as genai
from PIL import Image
import json
import re

class VisionProcessor:
    def __init__(self, api_key):
        """Initialize Gemini Vision processor."""
        genai.configure(api_key=api_key)
        # Use vision-capable model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def analyze_handwriting(self, image_path):
        """
        Analyze a handwriting sample image using Gemini Vision.
        
        Args:
            image_path: Path to handwriting sample image
            
        Returns:
            dict: Analysis results with style parameters
        """
        try:
            # Load image
            img = Image.open(image_path)
            
            # Create analysis prompt
            prompt = """Analyze this handwriting sample and extract the following characteristics:

1. **Slant**: Describe the angle (upright, forward slant, backward slant)
2. **Spacing**: Character spacing (tight, normal, wide)
3. **Stroke Weight**: Line thickness (thin, medium, bold)
4. **Style**: Overall style (print, cursive, mixed)
5. **Letter Heights**: Relative heights of uppercase vs lowercase
6. **Distinctive Features**: Any unique characteristics

Provide your analysis in JSON format:
{
    "slant": "forward/upright/backward",
    "spacing": "tight/normal/wide",
    "stroke_weight": "thin/medium/bold",
    "style": "print/cursive/mixed",
    "uppercase_height": 1.5,
    "distinctive_features": ["feature1", "feature2"]
}"""
            
            # Generate analysis
            response = self.model.generate_content([prompt, img])
            
            # Extract JSON from response
            text = response.text
            json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
            
            if json_match:
                analysis = json.loads(json_match.group())
                return analysis
            else:
                # Fallback to default analysis
                return {
                    "slant": "upright",
                    "spacing": "normal",
                    "stroke_weight": "medium",
                    "style": "print",
                    "uppercase_height": 1.5,
                    "distinctive_features": ["Standard handwriting"]
                }
        
        except Exception as e:
            print(f"[ERROR] Vision analysis failed: {e}")
            return None
    
    def generate_custom_font(self, analysis, sample_text="ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        """
        Generate a custom vector font based on handwriting analysis.
        
        Args:
            analysis: Analysis dict from analyze_handwriting
            sample_text: Text to generate font for
            
        Returns:
            dict: Custom font dictionary compatible with handwriting.py
        """
        if not analysis:
            return None
        
        try:
            # Create prompt for font generation
            prompt = f"""Based on this handwriting analysis:
- Slant: {analysis.get('slant', 'upright')}
- Spacing: {analysis.get('spacing', 'normal')}
- Stroke Weight: {analysis.get('stroke_weight', 'medium')}
- Style: {analysis.get('style', 'print')}

Generate vector stroke paths for the letters: {sample_text}

For each letter, provide relative (dx, dy) movements as a list of tuples.
Format as Python dict:
{{
    'A': [(dx1, dy1), (dx2, dy2), ...],
    'B': [(dx1, dy1), (dx2, dy2), ...],
    ...
}}

Each stroke should:
- Start at (0, 0)
- Use relative movements
- Scale to fit in approximately 10x20 units
- Reflect the analyzed handwriting style"""
            
            response = self.model.generate_content(prompt)
            
            # Try to extract Python dict from response
            text = response.text
            
            # Look for dict pattern
            dict_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
            
            if dict_match:
                # Try to evaluate as Python dict
                font_dict = eval(dict_match.group())
                return font_dict
            else:
                print("[WARNING] Could not extract font dict from response")
                return None
                
        except Exception as e:
            print(f"[ERROR] Font generation failed: {e}")
            return None
    
    def analyze_and_generate(self, image_path):
        """
        Complete workflow: analyze handwriting and generate custom font.
        
        Args:
            image_path: Path to handwriting sample
            
        Returns:
            tuple: (analysis_dict, font_dict)
        """
        print("[VISION] Analyzing handwriting sample...")
        analysis = self.analyze_handwriting(image_path)
        
        if not analysis:
            return None, None
        
        print(f"[VISION] Analysis complete: {analysis}")
        print("[VISION] Generating custom font...")
        
        font = self.generate_custom_font(analysis)
        
        if font:
            print(f"[VISION] Generated font with {len(font)} characters")
        
        return analysis, font
