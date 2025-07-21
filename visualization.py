"""
Visualization utilities for drawing annotations on document images
"""

import io
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
from config import ANNOTATION_COLORS, CONFIDENCE_THRESHOLDS


class DocumentVisualizer:
    def __init__(self):
        self.colors = ANNOTATION_COLORS
        
    def draw_annotations(self, image_bytes: bytes, extracted_data: Dict[str, Any], 
                        selected_fields: List[str] = None) -> Image.Image:
        """
        Draw bounding boxes and annotations on the document image
        
        Args:
            image_bytes: Original image as bytes
            extracted_data: Extracted data with polygon coordinates
            selected_fields: List of field names to highlight (None for all)
            
        Returns:
            PIL Image with annotations
        """
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create a copy for annotation
        annotated_image = image.copy()
        draw = ImageDraw.Draw(annotated_image)
        
        # Get image dimensions
        img_width, img_height = image.size
        print(f"DEBUG: Image dimensions: {img_width} x {img_height}")
        
        # Get page dimensions from extracted data
        page_data = extracted_data.get("pages", [])
        if page_data and len(page_data) > 0:
            page = page_data[0]
            doc_width = page.get("width", img_width)
            doc_height = page.get("height", img_height)
            unit = page.get("unit", "pixel")
            print(f"DEBUG: Document dimensions: {doc_width} x {doc_height} ({unit})")
            
            # Handle different units - Azure typically uses inches or pixels
            if unit == "inch":
                # For Azure Document Intelligence, coordinates are usually in inches
                # Don't convert - use direct mapping
                doc_width_px = doc_width
                doc_height_px = doc_height
            else:
                # Assume already in correct coordinate system
                doc_width_px = doc_width
                doc_height_px = doc_height
        else:
            doc_width_px, doc_height_px = img_width, img_height
        
        # Calculate scaling factors - for Azure, often we need direct mapping
        scale_x = img_width / doc_width_px if doc_width_px > 0 else 1.0
        scale_y = img_height / doc_height_px if doc_height_px > 0 else 1.0
        print(f"DEBUG: Scale factors: x={scale_x:.3f}, y={scale_y:.3f}")
        
        # Draw field annotations
        fields = extracted_data.get("fields", [])
        print(f"DEBUG: Processing {len(fields)} total fields")
        
        annotations_drawn = 0
        for i, field in enumerate(fields):
            if selected_fields and field["name"] not in selected_fields:
                continue
                
            field_polygon = field.get("polygon", [])
            if field_polygon:
                print(f"DEBUG: Drawing field '{field['name']}' with {len(field_polygon)} points")
                print(f"DEBUG: First few points: {field_polygon[:2]}")
                success = self._draw_field_annotation(
                    draw, field, scale_x, scale_y, i, img_width, img_height
                )
                if success:
                    annotations_drawn += 1
            else:
                print(f"DEBUG: No polygon for field '{field['name']}'")
        
        print(f"DEBUG: Successfully drew {annotations_drawn} annotations")
        
        # Draw table annotations if no specific fields selected
        if not selected_fields:
            tables = extracted_data.get("tables", [])
            for table in tables:
                if table.get("polygon"):
                    self._draw_table_annotation(
                        draw, table, scale_x, scale_y
                    )
        
        return annotated_image
    
    def _draw_field_annotation(self, draw: ImageDraw.Draw, field: Dict[str, Any], 
                              scale_x: float, scale_y: float, index: int, img_width: int, img_height: int) -> bool:
        """Draw annotation for a single field"""
        polygon = field["polygon"]
        confidence = field.get("confidence", 0.0)
        field_name = field.get("name", "Unknown")
        field_value = str(field.get("value", ""))[:50]  # Truncate long values
        
        if not polygon or len(polygon) < 2:
            return False # Indicate failure
        
        print(f"DEBUG: Drawing '{field_name}' with confidence {confidence:.2f}")
        print(f"DEBUG: Raw polygon: {polygon}")
        
        # Analyze the coordinate format and convert appropriately
        scaled_polygon = self._convert_coordinates_intelligently(polygon, img_width, img_height, scale_x, scale_y)
        
        if len(scaled_polygon) < 2:
            print(f"DEBUG: Not enough valid points for field '{field_name}' - only got {len(scaled_polygon)}")
            return False # Indicate failure
        
        print(f"DEBUG: Final scaled polygon: {scaled_polygon}")
        
        # Get color based on confidence
        color = self._get_confidence_color(confidence)
        print(f"DEBUG: Using color: {color}")
        
        # Calculate bounding rectangle from polygon
        x_coords = [p[0] for p in scaled_polygon]
        y_coords = [p[1] for p in scaled_polygon]
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        # Ensure we have a visible area (minimum 15x15 pixels)
        if abs(max_x - min_x) < 15:
            center_x = (min_x + max_x) / 2
            min_x = center_x - 7
            max_x = center_x + 7
        
        if abs(max_y - min_y) < 15:
            center_y = (min_y + max_y) / 2
            min_y = center_y - 7
            max_y = center_y + 7
        
        print(f"DEBUG: Final bounding box: ({min_x:.1f}, {min_y:.1f}) to ({max_x:.1f}, {max_y:.1f})")
        
        # Draw visible bounding rectangle
        try:
            for thickness in range(3):  # Reduced from 8 to 3
                rect = [min_x - thickness, min_y - thickness, max_x + thickness, max_y + thickness]
                draw.rectangle(rect, outline=color, width=1)
            
            print(f"DEBUG: Successfully drew rectangle for '{field_name}'")
        except Exception as e:
            print(f"DEBUG: Error drawing rectangle: {e}")
            return False
        
        # Draw the polygon outline if we have enough points
        if len(scaled_polygon) > 2:
            try:
                draw.polygon(scaled_polygon, outline=color, width=2)  # Reduced from 5 to 2
                print(f"DEBUG: Successfully drew polygon for '{field_name}'")
            except Exception as e:
                print(f"DEBUG: Error drawing polygon: {e}")
                # Continue with just the rectangle
        
        # Create and position label
        label_text = field_name
        confidence_text = f"{confidence:.1%}"
        
        # Position label
        label_x = max(0, min_x)
        label_y = max(0, min_y - 30)
        
        # If label would be off-screen, place it below
        if label_y < 0:
            label_y = min(img_height - 30, max_y + 5)
        
        # Draw simple but visible label
        try:
            # Draw background rectangle for label
            label_bg = [label_x, label_y, label_x + 200, label_y + 25]
            draw.rectangle(label_bg, fill=color, outline=color)
            
            # Draw text
            label_full = f"{field_name} ({confidence_text})"
            draw.text((label_x + 5, label_y + 5), label_full, fill="white")
            print(f"DEBUG: Successfully drew label for '{field_name}'")
            
        except Exception as e:
            print(f"DEBUG: Error drawing label: {e}")
            # Try simple text without background
            try:
                draw.text((label_x, label_y), field_name, fill=color)
            except:
                pass  # Give up on labeling if everything fails
        
        return True # Indicate success
    
    def _convert_coordinates_intelligently(self, polygon, img_width: int, img_height: int, scale_x: float, scale_y: float):
        """Intelligently convert polygon coordinates based on their format"""
        scaled_polygon = []
        
        # First, analyze what kind of coordinates we have
        sample_points = polygon[:3]  # Look at first few points
        max_x = max(p[0] for p in sample_points) if sample_points else 0
        max_y = max(p[1] for p in sample_points) if sample_points else 0
        min_x = min(p[0] for p in sample_points) if sample_points else 0
        min_y = min(p[1] for p in sample_points) if sample_points else 0
        
        print(f"DEBUG: Coordinate analysis - X range: {min_x:.3f} to {max_x:.3f}, Y range: {min_y:.3f} to {max_y:.3f}")
        print(f"DEBUG: Image size: {img_width} x {img_height}")
        print(f"DEBUG: Scale factors: {scale_x:.3f} x {scale_y:.3f}")
        
        # Determine coordinate format based on Azure Document Intelligence response structure
        coordinate_format = "unknown"
        
        # Azure typically gives pixel coordinates that match the page dimensions
        if max_x > 1 and max_y > 1:
            if max_x <= img_width * 2 and max_y <= img_height * 2:
                # Coordinates are likely in document pixel space, need scaling
                coordinate_format = "document_pixels"
            elif max_x <= 1.0 and max_y <= 1.0 and min_x >= 0.0 and min_y >= 0.0:
                coordinate_format = "normalized"  # 0-1 range
            else:
                coordinate_format = "document_pixels"  # Default for Azure
        elif max_x <= 1.0 and max_y <= 1.0 and min_x >= 0.0 and min_y >= 0.0:
            coordinate_format = "normalized"  # 0-1 range
        else:
            coordinate_format = "document_pixels"  # Default assumption
        
        print(f"DEBUG: Detected coordinate format: {coordinate_format}")
        
        for point in polygon:
            try:
                if len(point) >= 2:
                    x, y = float(point[0]), float(point[1])
                    
                    if coordinate_format == "normalized":
                        # Coordinates are 0-1, scale to image size
                        scaled_x = x * img_width
                        scaled_y = y * img_height
                        print(f"DEBUG: Normalized: ({x:.3f}, {y:.3f}) -> ({scaled_x:.1f}, {scaled_y:.1f})")
                        
                    elif coordinate_format == "document_pixels":
                        # Coordinates are in document pixel space, scale to image pixels
                        # Use the scale factors calculated from page dimensions
                        scaled_x = x * scale_x
                        scaled_y = y * scale_y
                        print(f"DEBUG: Document pixels: ({x:.1f}, {y:.1f}) -> ({scaled_x:.1f}, {scaled_y:.1f})")
                        
                    else:
                        # Fallback - use scale factors
                        scaled_x = x * scale_x
                        scaled_y = y * scale_y
                        print(f"DEBUG: Fallback: ({x:.3f}, {y:.3f}) -> ({scaled_x:.1f}, {scaled_y:.1f})")
                    
                    # Clamp coordinates to image bounds
                    scaled_x = max(0, min(img_width - 1, scaled_x))
                    scaled_y = max(0, min(img_height - 1, scaled_y))
                    
                    scaled_polygon.append((scaled_x, scaled_y))
                    
            except (ValueError, TypeError) as e:
                print(f"DEBUG: Error converting point {point}: {e}")
                continue
        
        return scaled_polygon
    
    def _draw_table_annotation(self, draw: ImageDraw.Draw, table: Dict[str, Any], 
                              scale_x: float, scale_y: float):
        """Draw annotation for a table"""
        polygon = table["polygon"]
        
        # Scale polygon coordinates
        scaled_polygon = []
        for point in polygon:
            scaled_x = point[0] * scale_x
            scaled_y = point[1] * scale_y
            scaled_polygon.append((scaled_x, scaled_y))
        
        # Draw table outline
        if len(scaled_polygon) >= 3:
            draw.polygon(scaled_polygon, outline="#0000FF", width=3)
            
            # Draw table label
            if scaled_polygon:
                label_x, label_y = scaled_polygon[0]
                label_text = f"Table ({table['row_count']}x{table['column_count']})"
                
                # Draw text background
                bbox = draw.textbbox((label_x, label_y - 20), label_text)
                draw.rectangle(bbox, fill="#0000FF", outline="#0000FF")
                
                # Draw text
                draw.text((label_x, label_y - 20), label_text, fill="white")
        
        # Draw individual cells
        cells = table.get("cells", [])
        for cell in cells:
            if cell.get("polygon"):
                cell_polygon = []
                for point in cell["polygon"]:
                    scaled_x = point[0] * scale_x
                    scaled_y = point[1] * scale_y
                    cell_polygon.append((scaled_x, scaled_y))
                
                if len(cell_polygon) >= 3:
                    confidence = cell.get("confidence", 0.0)
                    color = self._get_confidence_color(confidence)
                    draw.polygon(cell_polygon, outline=color, width=1)
    
    def _get_confidence_color(self, confidence: float) -> str:
        """Get color based on confidence level"""
        if confidence >= CONFIDENCE_THRESHOLDS["high"]:
            return self.colors["high_confidence"]
        elif confidence >= CONFIDENCE_THRESHOLDS["medium"]:
            return self.colors["medium_confidence"]
        else:
            return self.colors["low_confidence"]
    
    def create_legend(self) -> str:
        """Create HTML legend for confidence colors"""
        return f"""
        <div style="margin: 10px 0;">
            <h4>Confidence Legend:</h4>
            <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                <span style="color: {self.colors['high_confidence']};">■ High (≥80%)</span>
                <span style="color: {self.colors['medium_confidence']};">■ Medium (50-79%)</span>
                <span style="color: {self.colors['low_confidence']};">■ Low (<50%)</span>
                <span style="color: #0000FF;">■ Tables</span>
            </div>
        </div>
        """


def create_confidence_chart(confidence_stats: Dict[str, int]) -> Dict[str, Any]:
    """Create data for confidence distribution chart"""
    labels = ['High (≥80%)', 'Medium (50-79%)', 'Low (<50%)']
    values = [confidence_stats['high'], confidence_stats['medium'], confidence_stats['low']]
    colors = ['#00FF00', '#FFA500', '#FF0000']
    
    return {
        'labels': labels,
        'values': values,
        'colors': colors
    } 