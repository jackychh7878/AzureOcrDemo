"""
Configuration settings for Azure Document Intelligence POC
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Azure Document Intelligence Configuration
AZURE_DOC_INTEL_ENDPOINT = os.getenv("AZURE_DOC_INTEL_ENDPOINT", "")
AZURE_DOC_INTEL_KEY = os.getenv("AZURE_DOC_INTEL_KEY", "")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Document Intelligence Models
DOCUMENT_MODELS = {
    "Invoice": {
        "model_id": "prebuilt-invoice",
        "description": "Extract structured data from invoices including vendor, customer, items, totals, etc.",
        "supported_fields": ["VendorName", "CustomerName", "InvoiceTotal", "DueDate", "InvoiceDate", "Items"]
    },
    "ID Card": {
        "model_id": "prebuilt-idDocument",
        "description": "Extract data from identity documents like driver's licenses, passports, etc.",
        "supported_fields": ["FirstName", "LastName", "DocumentNumber", "DateOfBirth", "DateOfExpiration", "Address"]
    },
    "Bank Statement": {
        "model_id": "prebuilt-layout",
        "description": "Extract layout and text from bank statements and financial documents",
        "supported_fields": ["Tables", "Text", "KeyValuePairs", "SelectionMarks"]
    }
}

# Supported file types
SUPPORTED_FILE_TYPES = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp"]

# UI Configuration
ANNOTATION_COLORS = {
    "default": "#FF0000",
    "high_confidence": "#00FF00",
    "medium_confidence": "#FFA500", 
    "low_confidence": "#FF0000"
}

CONFIDENCE_THRESHOLDS = {
    "high": 0.8,
    "medium": 0.5,
    "low": 0.0
} 