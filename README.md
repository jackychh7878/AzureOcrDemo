# Azure Document Intelligence POC

A Streamlit-based proof-of-concept application for Azure Document Intelligence that analyzes invoices, bank statements, and ID cards with visual annotations.

## Features

🔍 **Multi-Document Support**
- **Invoices**: Extract vendor, customer, items, totals, dates
- **ID Cards**: Extract names, document numbers, dates, addresses  
- **Bank Statements**: Extract layout, tables, key-value pairs

📊 **Visual Analysis**
- Interactive document viewer with bounding box annotations
- Color-coded confidence levels (High ≥80%, Medium 50-79%, Low <50%)
- Field filtering and selection
- Confidence distribution charts

🎯 **Rich Data Extraction**
- Structured field extraction with confidence scores
- Table detection and cell-level analysis
- Polygon coordinates for precise location mapping
- Export results as JSON or CSV

## Prerequisites

- Python 3.8+
- Azure Document Intelligence resource
- Streamlit

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
git clone <your-repo>
cd OcrDemo
pip install -r requirements.txt
```

### 2. Environment Variables Setup

1. **Create .env file**:
   ```bash
   # Create .env file from template
   cp .env.example .env
   ```

2. **Get Azure Credentials**:
   - Go to [Azure Portal](https://portal.azure.com)
   - Create a new "Document Intelligence" resource
   - Choose your subscription, resource group, and region
   - Select pricing tier (F0 free tier available)
   - Navigate to "Keys and Endpoint"
   - Copy the **Endpoint** and **Key 1**

3. **Configure .env file**:
   ```bash
   # Edit .env file and add your credentials
   AZURE_DOC_INTEL_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
   AZURE_DOC_INTEL_KEY=your-64-character-api-key
   DEBUG_MODE=false
   ```

### 3. Run the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## Usage Guide

### 1. Configure Azure Credentials

**Option A: Using .env file (Recommended)**
- Credentials are automatically loaded from `.env` file
- Green checkmark appears in sidebar when detected
- More secure than manual entry

**Option B: Manual entry in sidebar**
- If no `.env` file is found, enter credentials manually
- Enter your Azure Document Intelligence **Endpoint**
- Enter your **API Key**
- Select the document type you want to analyze

### 2. Upload Document

- Click "Upload Document" 
- Supported formats: PDF, PNG, JPG, JPEG, TIFF, BMP
- Maximum file size depends on your Azure tier

### 3. Analyze Document

- Click "🚀 Analyze Document" 
- Wait for processing (usually 5-30 seconds)
- View results with annotations and extracted data

### 4. Explore Results

**Left Panel - Annotated Document**:
- Document image with colored bounding boxes
- Filter fields to display specific extractions
- Confidence legend showing color coding

**Right Panel - Extracted Data**:
- Confidence distribution chart
- Summary metrics
- Detailed field listings with values

### 5. Export Results

- Download extracted data as JSON
- Export field data as CSV
- Save for further processing

## Document Models

### Invoice Model (`prebuilt-invoice`)
- **Fields**: VendorName, CustomerName, InvoiceTotal, DueDate, InvoiceDate, Items
- **Use Cases**: Accounts payable automation, expense management
- **Accuracy**: High for standard invoice formats

### ID Document Model (`prebuilt-idDocument`)  
- **Fields**: FirstName, LastName, DocumentNumber, DateOfBirth, DateOfExpiration, Address
- **Use Cases**: Identity verification, KYC processes
- **Supported**: Driver's licenses, passports, ID cards

### Bank Statement Model (`prebuilt-layout`)
- **Fields**: Tables, Text, KeyValuePairs, SelectionMarks  
- **Use Cases**: Financial analysis, transaction extraction
- **Capabilities**: Table detection, text recognition, layout analysis

## Configuration

### Model Settings (`config.py`)

```python
DOCUMENT_MODELS = {
    "Invoice": {
        "model_id": "prebuilt-invoice",
        "description": "Extract structured data from invoices",
        "supported_fields": [...]
    }
    # ... other models
}
```

### Confidence Thresholds

- **High**: ≥80% confidence (Green)
- **Medium**: 50-79% confidence (Orange)  
- **Low**: <50% confidence (Red)

### Annotation Colors

```python
ANNOTATION_COLORS = {
    "high_confidence": "#00FF00",    # Green
    "medium_confidence": "#FFA500",  # Orange  
    "low_confidence": "#FF0000",     # Red
}
```

## Architecture

```
app.py                 # Main Streamlit application
├── config.py          # Configuration and model settings
├── document_processor.py  # Azure Document Intelligence integration
├── visualization.py   # Image annotation and charts
├── demo.py           # Setup testing script
├── .env              # Environment variables (create from .env.example)
├── .env.example      # Environment variables template
└── requirements.txt   # Python dependencies
```

## Key Components

### DocumentProcessor
- Handles Azure API communication
- Processes analysis results
- Extracts structured data with coordinates

### DocumentVisualizer  
- Draws bounding boxes on images
- Creates confidence-based color coding
- Generates interactive charts

### Streamlit App
- File upload and processing
- Interactive UI with filtering
- Results display and export

## API Usage Limits

**Free Tier (F0)**:
- 500 pages/month
- 20 calls/minute
- 2MB file size limit

**Standard Tier (S0)**:  
- Pay per transaction
- Higher rate limits
- Larger file support

## Troubleshooting

### Common Issues

1. **Invalid Credentials**
   - Verify endpoint URL format: `https://your-resource.cognitiveservices.azure.com/`
   - Check API key is correct (64-character string)
   - Ensure resource is not suspended

2. **File Upload Errors**
   - Check file format is supported
   - Verify file size under limits
   - Ensure file is not corrupted

3. **Analysis Failures**
   - Document quality may be too low
   - Unsupported language or format
   - Rate limiting (wait and retry)

### Debug Mode

Enable debug information:
```bash
# In .env file
DEBUG_MODE=true
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Resources

- [Azure Document Intelligence Documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Azure Python SDK](https://docs.microsoft.com/en-us/python/api/overview/azure/)

## Support

For issues and questions:
- Check the troubleshooting section
- Review Azure Document Intelligence limits
- Open an issue in this repository 