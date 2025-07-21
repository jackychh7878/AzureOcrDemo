# Quick Setup Guide

## 1. Install Dependencies
```bash
pip install -r requirements.txt
```

## 2. Create Environment Variables File

Create a file named `.env` in the project root with the following content:

```bash
# Azure Document Intelligence Configuration
AZURE_DOC_INTEL_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOC_INTEL_KEY=your-64-character-api-key
DEBUG_MODE=false
```

**How to get your credentials:**
1. Go to [Azure Portal](https://portal.azure.com)
2. Create or find your "Document Intelligence" resource
3. Go to "Keys and Endpoint" section
4. Copy the **Endpoint** and **Key 1**
5. Replace the values in the `.env` file above

## 3. Test Setup (Optional)
```bash
python healthcheck.py
```

## 4. Run the Application
```bash
streamlit run app.py
```

## 5. Use the App
- The app will automatically load credentials from the `.env` file
- Upload a document (PDF, PNG, JPG, etc.)
- Select document type (Invoice, ID Card, Bank Statement)
- Click "Analyze Document"
- View results with visual annotations!

## Security Note
- The `.env` file contains sensitive credentials
- It's already excluded from git via `.gitignore`
- Never share or commit this file to version control 