"""
Azure Document Intelligence processor for extracting data from documents
"""

import io
from typing import Dict, List, Tuple, Any, Optional
from azure.ai.documentintelligence import DocumentIntelligenceClient
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
            
            # Begin analysis - pass document bytes directly
            poller = self.client.begin_analyze_document(
                model_id=model_id,
                document=file_bytes
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
            'key_value_pairs': []
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
                            'bounding_box': line.polygon if hasattr(line, 'polygon') else []
                        }
                        page_info['lines'].append(line_info)
                
                # Extract words
                if hasattr(page, 'words') and page.words:
                    for word in page.words:
                        word_info = {
                            'content': word.content,
                            'confidence': word.confidence,
                            'bounding_box': word.polygon if hasattr(word, 'polygon') else []
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
                        if hasattr(field_value, 'content'):
                            doc_info['fields'][field_name] = {
                                'content': field_value.content,
                                'confidence': field_value.confidence,
                                'value': field_value.value if hasattr(field_value, 'value') else field_value.content
                            }
                
                processed_result['documents'].append(doc_info)
        
        # Process tables
        if hasattr(result, 'tables') and result.tables:
            for table in result.tables:
                table_info = {
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'cells': []
                }
                
                if hasattr(table, 'cells') and table.cells:
                    for cell in table.cells:
                        cell_info = {
                            'content': cell.content,
                            'row_index': cell.row_index,
                            'column_index': cell.column_index,
                            'row_span': cell.row_span if hasattr(cell, 'row_span') else 1,
                            'column_span': cell.column_span if hasattr(cell, 'column_span') else 1
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
    
    def extract_key_fields(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key fields based on document type"""
        model_type = analysis_result.get('model_type', 'layout')
        key_fields = {}
        
        if analysis_result.get('documents'):
            doc = analysis_result['documents'][0]
            fields = doc.get('fields', {})
            
            if model_type == 'invoice':
                key_fields = {
                    'vendor_name': fields.get('VendorName', {}).get('content', ''),
                    'customer_name': fields.get('CustomerName', {}).get('content', ''),
                    'invoice_date': fields.get('InvoiceDate', {}).get('content', ''),
                    'invoice_total': fields.get('InvoiceTotal', {}).get('content', ''),
                    'due_date': fields.get('DueDate', {}).get('content', '')
                }
            elif model_type == 'receipt':
                key_fields = {
                    'merchant_name': fields.get('MerchantName', {}).get('content', ''),
                    'transaction_date': fields.get('TransactionDate', {}).get('content', ''),
                    'total': fields.get('Total', {}).get('content', ''),
                    'subtotal': fields.get('Subtotal', {}).get('content', '')
                }
            elif model_type == 'identity':
                key_fields = {
                    'first_name': fields.get('FirstName', {}).get('content', ''),
                    'last_name': fields.get('LastName', {}).get('content', ''),
                    'document_number': fields.get('DocumentNumber', {}).get('content', ''),
                    'date_of_birth': fields.get('DateOfBirth', {}).get('content', ''),
                    'date_of_expiration': fields.get('DateOfExpiration', {}).get('content', '')
                }
        
        return key_fields 