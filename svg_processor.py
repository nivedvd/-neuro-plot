"""
SVG Processor for Neuro Plot
Converts SVG vector graphics to plotter-compatible contours
"""

from svgpathtools import svg2paths, Path, Line, CubicBezier, QuadraticBezier, Arc
import numpy as np

def svg_to_contours(svg_path, resolution=1.0):
    """
    Convert an SVG file to contours compatible with the plotter.
    
    Args:
        svg_path: Path to the SVG file
        resolution: Sampling resolution in mm (smaller = more detailed)
    
    Returns:
        List of contours in OpenCV format: [[[x, y]], [[x, y]], ...]
    """
    try:
        paths, attributes = svg2paths(svg_path)
        contours = []
        
        for path in paths:
            contour = []
            
            for segment in path:
                # Sample the segment into points
                points = sample_segment(segment, resolution)
                contour.extend(points)
            
            if contour:
                # Convert to OpenCV contour format
                opencv_contour = [[[pt[0], pt[1]]] for pt in contour]
                contours.append(opencv_contour)
        
        return contours
    
    except Exception as e:
        print(f"[SVG] Error processing SVG: {e}")
        return []

def sample_segment(segment, resolution):
    """
    Sample a path segment into discrete points.
    
    Args:
        segment: SVG path segment (Line, CubicBezier, etc.)
        resolution: Distance between samples in mm
    
    Returns:
        List of (x, y) tuples
    """
    # Calculate segment length
    length = segment.length()
    
    if length == 0:
        return []
    
    # Number of samples based on resolution
    num_samples = max(2, int(length / resolution))
    
    points = []
    for i in range(num_samples):
        t = i / (num_samples - 1)  # Parameter from 0 to 1
        point = segment.point(t)
        points.append((point.real, point.imag))
    
    return points

def get_svg_bounds(svg_path):
    """
    Get the bounding box of an SVG file.
    
    Returns:
        (min_x, min_y, max_x, max_y) or None if error
    """
    try:
        paths, _ = svg2paths(svg_path)
        
        if not paths:
            return None
        
        all_points = []
        for path in paths:
            for segment in path:
                # Sample a few points to get bounds
                for t in np.linspace(0, 1, 10):
                    pt = segment.point(t)
                    all_points.append((pt.real, pt.imag))
        
        if not all_points:
            return None
        
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        
        return (min(xs), min(ys), max(xs), max(ys))
    
    except Exception as e:
        print(f"[SVG] Error getting bounds: {e}")
        return None
