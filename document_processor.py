"""
Azure Document Intelligence processor for extracting data from documents
"""

import io
from typing import Dict, List, Tuple, Any, Optional
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
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
        Analyze a document using Azure Document Intelligence
        
        Args:
            file_bytes: Document content as bytes
            model_type: Type of document model to use
            
        Returns:
            Dictionary containing extracted data and metadata
        """
        try:
            # Get the model ID from the configuration
            model_id = DOCUMENT_MODELS.get(model_type)
            if not model_id:
                raise ValueError(f"Unknown model type: {model_type}")

            receiptUrl = "https://tflowpoc.blob.core.windows.net/ocr-demo/passport_sample.jpg?sv=2023-01-03&st=2025-07-21T03%3A35%3A52Z&se=2026-07-22T03%3A35%3A00Z&sr=b&sp=r&sig=li5MUnFwAo4VVyWVEcid2Crhlh%2FskaEWA1UU5k5aWj8%3D"
            # Begin analysis - pass document bytes directly
            poller = self.client.begin_analyze_document(
                model_id=model_id,
                body=AnalyzeDocumentRequest(url_source=receiptUrl),
                locale="en-US"
            )
            result = poller.result()
            
            # Convert to dictionary for processing
            return self._process_analysis_result(result, model_type)
            
        except Exception as e:
            st.error(f"Error analyzing document: {str(e)}")
            return {}
    
    def _process_analysis_result(self, result, model_type: str) -> Dict[str, Any]:
        """Process the analysis result and extract relevant information"""
        processed_result = {
            'model_type': model_type,
            'confidence_threshold': CONFIDENCE_THRESHOLDS.get(model_type, 0.5),
            'pages': [],
            'documents': [],
            'tables': [],
            'key_value_pairs': [],
            'fields': [],  # Add fields at top level for display
            'confidence_stats': {'high': 0, 'medium': 0, 'low': 0}  # Add confidence stats
        }
        
        # Process pages
        if hasattr(result, 'pages') and result.pages:
            for page in result.pages:
                page_info = {
                    'page_number': page.page_number,
                    'width': page.width,
                    'height': page.height,
                    'unit': page.unit,
                    'lines': [],
                    'words': []
                }
                
                # Extract lines
                if hasattr(page, 'lines') and page.lines:
                    for line in page.lines:
                        line_info = {
                            'content': line.content,
                            'bounding_box': self._convert_polygon(line.polygon) if hasattr(line, 'polygon') else []
                        }
                        page_info['lines'].append(line_info)
                
                # Extract words
                if hasattr(page, 'words') and page.words:
                    for word in page.words:
                        word_info = {
                            'content': word.content,
                            'confidence': word.confidence,
                            'bounding_box': self._convert_polygon(word.polygon) if hasattr(word, 'polygon') else []
                        }
                        page_info['words'].append(word_info)
                
                processed_result['pages'].append(page_info)
        
        # Process documents (for prebuilt models)
        if hasattr(result, 'documents') and result.documents:
            for doc in result.documents:
                doc_info = {
                    'doc_type': doc.doc_type,
                    'confidence': doc.confidence,
                    'fields': {}
                }
                
                if hasattr(doc, 'fields') and doc.fields:
                    for field_name, field_value in doc.fields.items():
                        if field_value is not None:
                            # Extract field information
                            field_info = {
                                'name': field_name,
                                'value': self._extract_field_value(field_value),
                                'confidence': getattr(field_value, 'confidence', 0.0),
                                'type': getattr(field_value, 'type', 'string'),
                                'polygon': self._extract_field_polygon(field_value),
                                'page_number': 1  # Default to page 1
                            }
                            
                            # Add to top-level fields for display
                            processed_result['fields'].append(field_info)
                            
                            # Update confidence stats
                            confidence = field_info['confidence']
                            if confidence >= CONFIDENCE_THRESHOLDS['high']:
                                processed_result['confidence_stats']['high'] += 1
                            elif confidence >= CONFIDENCE_THRESHOLDS['medium']:
                                processed_result['confidence_stats']['medium'] += 1
                            else:
                                processed_result['confidence_stats']['low'] += 1
                            
                            doc_info['fields'][field_name] = {
                                'content': field_info['value'],
                                'confidence': confidence,
                                'value': field_info['value']
                            }
                
                processed_result['documents'].append(doc_info)
        
        # Process tables
        if hasattr(result, 'tables') and result.tables:
            for table in result.tables:
                table_info = {
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'cells': [],
                    'polygon': self._convert_polygon(table.bounding_regions[0].polygon) if hasattr(table, 'bounding_regions') and table.bounding_regions else []
                }
                
                if hasattr(table, 'cells') and table.cells:
                    for cell in table.cells:
                        cell_info = {
                            'content': cell.content,
                            'row_index': cell.row_index,
                            'column_index': cell.column_index,
                            'row_span': getattr(cell, 'row_span', 1),
                            'column_span': getattr(cell, 'column_span', 1),
                            'polygon': self._convert_polygon(cell.bounding_regions[0].polygon) if hasattr(cell, 'bounding_regions') and cell.bounding_regions else [],
                            'confidence': getattr(cell, 'confidence', 0.0)
                        }
                        table_info['cells'].append(cell_info)
                
                processed_result['tables'].append(table_info)
        
        # Process key-value pairs
        if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
            for kvp in result.key_value_pairs:
                kvp_info = {
                    'key': kvp.key.content if kvp.key else '',
                    'value': kvp.value.content if kvp.value else '',
                    'confidence': kvp.confidence
                }
                processed_result['key_value_pairs'].append(kvp_info)
        
        return processed_result
    
    def _extract_field_value(self, field_value) -> str:
        """Extract the actual value from a field"""
        if hasattr(field_value, 'value') and field_value.value is not None:
            return str(field_value.value)
        elif hasattr(field_value, 'content') and field_value.content is not None:
            return str(field_value.content)
        else:
            return str(field_value) if field_value is not None else ''
    
    def _extract_field_polygon(self, field_value) -> List[Tuple[float, float]]:
        """Extract polygon coordinates from a field"""
        try:
            if hasattr(field_value, 'bounding_regions') and field_value.bounding_regions:
                polygon = field_value.bounding_regions[0].polygon
                return self._convert_polygon(polygon)
        except (AttributeError, IndexError):
            pass
        return []
    
    def _convert_polygon(self, polygon) -> List[Tuple[float, float]]:
        """Convert polygon format to list of tuples"""
        if not polygon:
            return []
        
        try:
            # Handle different polygon formats
            if hasattr(polygon, '__iter__'):
                coords = []
                for point in polygon:
                    if hasattr(point, 'x') and hasattr(point, 'y'):
                        coords.append((point.x, point.y))
                    elif isinstance(point, (list, tuple)) and len(point) >= 2:
                        coords.append((float(point[0]), float(point[1])))
                return coords
        except Exception:
            pass
        
        return []
    
    def extract_key_fields(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key fields based on document type"""
        model_type = analysis_result.get('model_type', 'layout')
        key_fields = {}
        
        if analysis_result.get('documents'):
            doc = analysis_result['documents'][0]
            fields = doc.get('fields', {})
            
            if model_type == 'Invoice':
                key_fields = {
                    'vendor_name': fields.get('VendorName', {}).get('content', ''),
                    'customer_name': fields.get('CustomerName', {}).get('content', ''),
                    'invoice_date': fields.get('InvoiceDate', {}).get('content', ''),
                    'invoice_total': fields.get('InvoiceTotal', {}).get('content', ''),
                    'due_date': fields.get('DueDate', {}).get('content', '')
                }
            elif model_type == 'Receipt':
                key_fields = {
                    'merchant_name': fields.get('MerchantName', {}).get('content', ''),
                    'transaction_date': fields.get('TransactionDate', {}).get('content', ''),
                    'total': fields.get('Total', {}).get('content', ''),
                    'subtotal': fields.get('Subtotal', {}).get('content', '')
                }
            elif model_type == 'ID Card':
                key_fields = {
                    'first_name': fields.get('FirstName', {}).get('content', ''),
                    'last_name': fields.get('LastName', {}).get('content', ''),
                    'document_number': fields.get('DocumentNumber', {}).get('content', ''),
                    'date_of_birth': fields.get('DateOfBirth', {}).get('content', ''),
                    'date_of_expiration': fields.get('DateOfExpiration', {}).get('content', '')
                }
        
        return key_fields 