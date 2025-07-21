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
        
        # Get page dimensions from extracted data
        page_data = extracted_data.get("pages", [])
        if page_data:
            doc_width = page_data[0].get("width", img_width)
            doc_height = page_data[0].get("height", img_height)
        else:
            doc_width, doc_height = img_width, img_height
        
        # Calculate scaling factors
        scale_x = img_width / doc_width
        scale_y = img_height / doc_height
        
        # Draw field annotations
        fields = extracted_data.get("fields", [])
        for i, field in enumerate(fields):
            if selected_fields and field["name"] not in selected_fields:
                continue
                
            if field.get("polygon"):
                self._draw_field_annotation(
                    draw, field, scale_x, scale_y, i
                )
        
        # Draw table annotations
        tables = extracted_data.get("tables", [])
        for table in tables:
            if table.get("polygon"):
                self._draw_table_annotation(
                    draw, table, scale_x, scale_y
                )
        
        return annotated_image
    
    def _draw_field_annotation(self, draw: ImageDraw.Draw, field: Dict[str, Any], 
                              scale_x: float, scale_y: float, index: int):
        """Draw annotation for a single field"""
        polygon = field["polygon"]
        confidence = field.get("confidence", 0.0)
        field_name = field.get("name", "Unknown")
        
        if not polygon:
            return
        
        # Scale polygon coordinates
        scaled_polygon = []
        for point in polygon:
            scaled_x = point[0] * scale_x
            scaled_y = point[1] * scale_y
            scaled_polygon.append((scaled_x, scaled_y))
        
        if len(scaled_polygon) < 2:
            return
        
        # Get color based on confidence
        color = self._get_confidence_color(confidence)
        
        # Calculate bounding box for the polygon
        if scaled_polygon:
            x_coords = [p[0] for p in scaled_polygon]
            y_coords = [p[1] for p in scaled_polygon]
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)
            
            # Draw filled rectangle with transparency effect (simulate with outline)
            # Draw multiple lines to create a thick border effect
            for i in range(3):
                if len(scaled_polygon) >= 3:
                    # Draw polygon outline
                    draw.polygon(scaled_polygon, outline=color, width=2+i)
                else:
                    # For lines, draw rectangle
                    draw.rectangle([min_x-i, min_y-i, max_x+i, max_y+i], outline=color, width=2)
            
            # Create label text
            label_text = f"{field_name}"
            confidence_text = f"{confidence:.1%}"
            
            # Calculate label position (above the field)
            label_x = min_x
            label_y = min_y - 30
            
            # Ensure label is within image bounds
            if label_y < 0:
                label_y = max_y + 5
            
            # Draw label background rectangle
            try:
                # Get text dimensions
                bbox = draw.textbbox((0, 0), label_text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                conf_bbox = draw.textbbox((0, 0), confidence_text)
                conf_width = conf_bbox[2] - conf_bbox[0]
                
                total_width = max(text_width, conf_width) + 10
                total_height = text_height * 2 + 10
                
                # Draw background rectangle
                bg_rect = [label_x, label_y, label_x + total_width, label_y + total_height]
                draw.rectangle(bg_rect, fill=color, outline=color)
                
                # Draw field name
                draw.text((label_x + 5, label_y + 2), label_text, fill="white")
                
                # Draw confidence
                draw.text((label_x + 5, label_y + text_height + 4), confidence_text, fill="white")
                
            except Exception as e:
                # Fallback to simple text if bbox calculation fails
                draw.text((label_x, label_y), f"{label_text} ({confidence_text})", fill=color)
    
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