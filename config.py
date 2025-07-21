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

# Document Intelligence Models - simplified structure
DOCUMENT_MODELS = {
    "Invoice": "prebuilt-invoice",
    "Receipt": "prebuilt-receipt", 
    "ID Card": "prebuilt-idDocument",
    "Bank Statement": "prebuilt-layout",
    "Layout": "prebuilt-layout"
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
    "Invoice": 0.7,
    "Receipt": 0.7,
    "ID Card": 0.8,
    "Bank Statement": 0.5,
    "Layout": 0.5,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.0
} 