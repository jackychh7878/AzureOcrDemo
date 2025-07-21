"""
Azure Document Intelligence processor for extracting data from documents
"""

import io
import os
import tempfile
from typing import Dict, List, Tuple, Any, Optional
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
import streamlit as st
from config import DOCUMENT_MODELS, CONFIDENCE_THRESHOLDS
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import uuid


def azure_upload_file_and_get_sas_url(file_path, blob_name, expiry_date: timedelta = timedelta(hours=1)):
    """
    Uploads a file to Azure Blob Storage and generates a temporary SAS URL.

    :param expiry_date: Expiry date for the SAS url
    :param file_path: Path to the local file to be uploaded.
    :param blob_name: Name for the blob in Azure Storage.

    :return: SAS URL string for the uploaded blob.
    """
    try:
        container_name = os.getenv('AZURE_CONTAINER_NAME')
        account_name = os.getenv('AZURE_ACCOUNT_NAME')
        account_key = os.getenv('AZURE_ACCOUNT_KEY')

        # Construct the BlobServiceClient using the account URL and account key
        account_url = f"https://{account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(account_url=account_url, credential=account_key)

        # Get the container client
        container_client = blob_service_client.get_container_client(container_name)

        # Upload the file
        with open(file_path, "rb") as data:
            blob_client = container_client.upload_blob(name=blob_name, data=data, overwrite=True)

        # Set the SAS token expiration time (e.g., 1 hour from now)
        sas_expiry = datetime.now() + expiry_date

        # Generate the SAS token with read permissions
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=sas_expiry
        )

        # Construct the full URL with the SAS token
        sas_url = f"{account_url}/{container_name}/{blob_name}?{sas_token}"
        return sas_url

    except Exception as e:
        print(f"An error occurred: {e}")
        return None



class DocumentProcessor:
    def __init__(self, endpoint: str, key: str):
        """Initialize the Document Intelligence client"""
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )
    
    def analyze_document(self, file_bytes: bytes, model_type: str, filename: str = None) -> Dict[str, Any]:
        """
        Analyze a document using Azure Document Intelligence
        
        Args:
            file_bytes: Document content as bytes
            model_type: Type of document model to use
            filename: Original filename to determine file extension
            
        Returns:
            Dictionary containing extracted data and metadata
        """
        try:
            # Get the model ID from the configuration
            model_id = DOCUMENT_MODELS.get(model_type)
            if not model_id:
                raise ValueError(f"Unknown model type: {model_type}")

            # Create a temporary file to upload
            temp_file_path = None
            sas_url = None
            
            try:
                # Determine file extension from filename or default to pdf
                file_extension = ".pdf"  # Default to PDF for document processing
                if filename:
                    file_extension = os.path.splitext(filename.lower())[1]
                    if not file_extension:
                        # Try to detect from file content
                        if file_bytes.startswith(b'%PDF'):
                            file_extension = ".pdf"
                        elif file_bytes.startswith(b'\xff\xd8\xff'):
                            file_extension = ".jpg"
                        elif file_bytes.startswith(b'\x89PNG'):
                            file_extension = ".png"
                        else:
                            file_extension = ".pdf"  # Default fallback
                
                # Generate a unique blob name with proper extension
                timestamp = int(datetime.now().timestamp())
                blob_name = f"temp_document_{uuid.uuid4().hex}_{timestamp}{file_extension}"
                
                # Create temporary file from bytes with proper extension
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                    temp_file.write(file_bytes)
                    temp_file_path = temp_file.name
                
                # Upload to Azure Blob Storage and get SAS URL
                sas_url = azure_upload_file_and_get_sas_url(
                    file_path=temp_file_path,
                    blob_name=blob_name,
                    expiry_date=timedelta(hours=2)  # Give enough time for processing
                )
                
                if not sas_url:
                    raise Exception("Failed to upload file to Azure Blob Storage")
                
                # Begin analysis using the SAS URL
                poller = self.client.begin_analyze_document(
                    model_id=model_id,
                    body=AnalyzeDocumentRequest(url_source=sas_url),
                    locale="en-US"
                )
                result = poller.result()
                
                # Convert to dictionary for processing
                processed_result = self._process_analysis_result(result, model_type)
                
                # Add file type information for visualization
                processed_result['file_type'] = file_extension.lower()
                processed_result['filename'] = filename
                
                return processed_result
                
            finally:
                # Clean up temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as cleanup_error:
                        print(f"Warning: Could not delete temporary file {temp_file_path}: {cleanup_error}")
            
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
                    'width': getattr(page, 'width', 8.5),  # Default letter size
                    'height': getattr(page, 'height', 11.0),
                    'unit': getattr(page, 'unit', 'inch'),
                    'lines': [],
                    'words': []
                }
                
                # Extract lines
                if hasattr(page, 'lines') and page.lines:
                    for line in page.lines:
                        line_polygon = []
                        if hasattr(line, 'polygon') and line.polygon:
                            line_polygon = self._convert_polygon(line.polygon)
                        
                        line_info = {
                            'content': getattr(line, 'content', ''),
                            'bounding_box': line_polygon
                        }
                        page_info['lines'].append(line_info)
                
                # Extract words
                if hasattr(page, 'words') and page.words:
                    for word in page.words:
                        word_polygon = []
                        if hasattr(word, 'polygon') and word.polygon:
                            word_polygon = self._convert_polygon(word.polygon)
                        
                        word_info = {
                            'content': getattr(word, 'content', ''),
                            'confidence': getattr(word, 'confidence', 0.0),
                            'bounding_box': word_polygon
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
                for region in field_value.bounding_regions:
                    if hasattr(region, 'polygon') and region.polygon:
                        polygon = self._convert_polygon(region.polygon)
                        if polygon:  # Return first valid polygon
                            return polygon
        except (AttributeError, IndexError):
            pass
        return []
    
    def _convert_polygon(self, polygon) -> List[Tuple[float, float]]:
        """Convert polygon format to list of tuples"""
        if not polygon:
            return []
        
        try:
            coords = []
            
            # Handle Azure Document Intelligence polygon format
            if isinstance(polygon, (list, tuple)):
                # Check if it's a flat array [x1, y1, x2, y2, ...]
                if len(polygon) >= 4 and all(isinstance(x, (int, float)) for x in polygon):
                    # Convert flat array to coordinate pairs
                    for i in range(0, len(polygon), 2):
                        if i + 1 < len(polygon):
                            x = float(polygon[i])
                            y = float(polygon[i + 1])
                            coords.append((x, y))
                    print(f"DEBUG: Converted flat polygon {polygon} to {coords}")
                    return coords
                
                # Handle array of point objects or tuples
                for point in polygon:
                    if hasattr(point, 'x') and hasattr(point, 'y'):
                        # Azure Document Intelligence Point object
                        coords.append((float(point.x), float(point.y)))
                    elif isinstance(point, dict) and 'x' in point and 'y' in point:
                        # Dictionary format
                        coords.append((float(point['x']), float(point['y'])))
                    elif isinstance(point, (list, tuple)) and len(point) >= 2:
                        # List/tuple format
                        coords.append((float(point[0]), float(point[1])))
                    elif hasattr(point, '__getitem__') and len(point) >= 2:
                        # Array-like object
                        coords.append((float(point[0]), float(point[1])))
            
            # Validate that we have at least 2 points for a valid shape
            if len(coords) >= 2:
                print(f"DEBUG: Successfully converted polygon to {len(coords)} points")
                return coords
                
        except (AttributeError, ValueError, TypeError, IndexError) as e:
            print(f"Error converting polygon: {e}")
            print(f"Polygon data: {polygon}")
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