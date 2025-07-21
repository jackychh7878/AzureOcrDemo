"""
Azure Document Intelligence processor for extracting data from documents
"""

import io
from typing import Dict, List, Tuple, Any, Optional
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
import streamlit as st
from config import DOCUMENT_MODELS, CONFIDENCE_THRESHOLDS


class DocumentProcessor:
    def __init__(self, endpoint: str, key: str):
        """Initialize the Document Intelligence client"""
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )
    
    def analyze_document(self, file_bytes: bytes, model_type: str) -> Dict[str, Any]:
        """
        Analyze document using specified model
        
        Args:
            file_bytes: Document file as bytes
            model_type: Type of document model to use
            
        Returns:
            Dictionary containing extracted data and metadata
        """
        try:
            model_id = DOCUMENT_MODELS[model_type]["model_id"]
            
            # Create analyze request
            analyze_request = AnalyzeDocumentRequest(bytes_source=file_bytes)
            
            # Start analysis
            poller = self.client.begin_analyze_document(
                model_id=model_id,
                analyze_request=analyze_request
            )
            
            # Get result
            result = poller.result()
            
            # Process and return structured data
            return self._process_analysis_result(result, model_type)
            
        except Exception as e:
            st.error(f"Error analyzing document: {str(e)}")
            return {}
    
    def _process_analysis_result(self, result: Any, model_type: str) -> Dict[str, Any]:
        """Process the analysis result into structured format"""
        processed_data = {
            "model_type": model_type,
            "fields": [],
            "tables": [],
            "pages": [],
            "confidence_stats": {"high": 0, "medium": 0, "low": 0}
        }
        
        # Process pages
        if hasattr(result, 'pages') and result.pages:
            for page in result.pages:
                page_data = {
                    "page_number": page.page_number,
                    "width": page.width,
                    "height": page.height,
                    "unit": page.unit,
                    "angle": getattr(page, 'angle', 0)
                }
                processed_data["pages"].append(page_data)
        
        # Process documents (main extracted data)
        if hasattr(result, 'documents') and result.documents:
            for doc in result.documents:
                if hasattr(doc, 'fields') and doc.fields:
                    for field_name, field_value in doc.fields.items():
                        field_data = self._extract_field_data(field_name, field_value)
                        if field_data:
                            processed_data["fields"].append(field_data)
                            self._update_confidence_stats(processed_data["confidence_stats"], field_data.get("confidence", 0))
        
        # Process tables
        if hasattr(result, 'tables') and result.tables:
            for table in result.tables:
                table_data = self._extract_table_data(table)
                processed_data["tables"].append(table_data)
        
        # For layout model, also process key-value pairs and text
        if model_type == "Bank Statement":
            processed_data = self._process_layout_specific_data(result, processed_data)
        
        return processed_data
    
    def _extract_field_data(self, field_name: str, field_value: Any) -> Optional[Dict[str, Any]]:
        """Extract structured data from a field"""
        if not field_value:
            return None
        
        field_data = {
            "name": field_name,
            "type": getattr(field_value, 'type', 'string'),
            "confidence": getattr(field_value, 'confidence', 0.0),
            "polygon": [],
            "page_number": 1
        }
        
        # Extract value based on type
        if hasattr(field_value, 'value'):
            if hasattr(field_value.value, 'value'):
                field_data["value"] = field_value.value.value
            else:
                field_data["value"] = field_value.value
        elif hasattr(field_value, 'content'):
            field_data["value"] = field_value.content
        else:
            field_data["value"] = str(field_value)
        
        # Extract bounding regions (polygons)
        if hasattr(field_value, 'bounding_regions') and field_value.bounding_regions:
            for region in field_value.bounding_regions:
                field_data["page_number"] = region.page_number
                if hasattr(region, 'polygon') and region.polygon:
                    # Convert polygon points to list of [x, y] coordinates
                    polygon_points = []
                    for point in region.polygon:
                        polygon_points.append([point.x, point.y])
                    field_data["polygon"] = polygon_points
                    break
        
        return field_data
    
    def _extract_table_data(self, table: Any) -> Dict[str, Any]:
        """Extract table data with cell polygons"""
        table_data = {
            "row_count": table.row_count,
            "column_count": table.column_count,
            "cells": [],
            "polygon": []
        }
        
        # Extract table bounding region
        if hasattr(table, 'bounding_regions') and table.bounding_regions:
            region = table.bounding_regions[0]
            if hasattr(region, 'polygon') and region.polygon:
                polygon_points = []
                for point in region.polygon:
                    polygon_points.append([point.x, point.y])
                table_data["polygon"] = polygon_points
        
        # Extract cells
        if hasattr(table, 'cells') and table.cells:
            for cell in table.cells:
                cell_data = {
                    "content": cell.content,
                    "row_index": cell.row_index,
                    "column_index": cell.column_index,
                    "confidence": getattr(cell, 'confidence', 0.0),
                    "polygon": []
                }
                
                # Extract cell polygon
                if hasattr(cell, 'bounding_regions') and cell.bounding_regions:
                    region = cell.bounding_regions[0]
                    if hasattr(region, 'polygon') and region.polygon:
                        polygon_points = []
                        for point in region.polygon:
                            polygon_points.append([point.x, point.y])
                        cell_data["polygon"] = polygon_points
                
                table_data["cells"].append(cell_data)
        
        return table_data
    
    def _process_layout_specific_data(self, result: Any, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process layout-specific data for bank statements"""
        # Process key-value pairs
        if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
            for kvp in result.key_value_pairs:
                key_content = kvp.key.content if kvp.key else "Unknown Key"
                value_content = kvp.value.content if kvp.value else "No Value"
                
                field_data = {
                    "name": key_content,
                    "value": value_content,
                    "type": "key_value_pair",
                    "confidence": getattr(kvp, 'confidence', 0.0),
                    "polygon": [],
                    "page_number": 1
                }
                
                # Get polygon from key or value
                if kvp.key and hasattr(kvp.key, 'bounding_regions') and kvp.key.bounding_regions:
                    region = kvp.key.bounding_regions[0]
                    if hasattr(region, 'polygon') and region.polygon:
                        polygon_points = []
                        for point in region.polygon:
                            polygon_points.append([point.x, point.y])
                        field_data["polygon"] = polygon_points
                        field_data["page_number"] = region.page_number
                
                processed_data["fields"].append(field_data)
                self._update_confidence_stats(processed_data["confidence_stats"], field_data["confidence"])
        
        return processed_data
    
    def _update_confidence_stats(self, stats: Dict[str, int], confidence: float):
        """Update confidence statistics"""
        if confidence >= CONFIDENCE_THRESHOLDS["high"]:
            stats["high"] += 1
        elif confidence >= CONFIDENCE_THRESHOLDS["medium"]:
            stats["medium"] += 1
        else:
            stats["low"] += 1
    
    @staticmethod
    def get_confidence_category(confidence: float) -> str:
        """Get confidence category for a given confidence score"""
        if confidence >= CONFIDENCE_THRESHOLDS["high"]:
            return "high"
        elif confidence >= CONFIDENCE_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low" 