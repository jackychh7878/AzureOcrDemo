"""
Azure Document Intelligence POC - Streamlit Application
Supports Invoice, Bank Statement, and ID Card analysis with visual annotations
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from config import DOCUMENT_MODELS, SUPPORTED_FILE_TYPES, AZURE_DOC_INTEL_ENDPOINT, AZURE_DOC_INTEL_KEY
from document_processor import DocumentProcessor
from visualization import DocumentVisualizer, create_confidence_chart


def init_session_state():
    """Initialize session state variables"""
    if 'extracted_data' not in st.session_state:
        st.session_state.extracted_data = None
    if 'original_image' not in st.session_state:
        st.session_state.original_image = None
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = "Invoice"


def setup_sidebar():
    """Setup the sidebar with configuration options"""
    st.sidebar.title("🔧 Configuration")
    
    # Azure credentials
    st.sidebar.subheader("Azure Document Intelligence")
    
    # Check if credentials are in .env file
    env_endpoint = AZURE_DOC_INTEL_ENDPOINT
    env_key = AZURE_DOC_INTEL_KEY
    
    if env_endpoint and env_key:
        st.sidebar.success("✅ Credentials loaded from .env file")
        endpoint = env_endpoint
        key = env_key
        st.sidebar.info(f"Endpoint: {endpoint[:30]}...")
        st.sidebar.info(f"API Key: {key[:8]}...{key[-4:]}")
    else:
        st.sidebar.warning("⚠️ No credentials in .env file")
        endpoint = st.sidebar.text_input(
            "Endpoint",
            value=env_endpoint,
            placeholder="https://your-resource.cognitiveservices.azure.com/",
            help="Your Azure Document Intelligence endpoint"
        )
        key = st.sidebar.text_input(
            "API Key",
            value=env_key,
            type="password",
            placeholder="Enter your API key",
            help="Your Azure Document Intelligence API key"
        )
    
    # Model selection
    st.sidebar.subheader("Document Model")
    selected_model = st.sidebar.selectbox(
        "Select Document Type",
        options=list(DOCUMENT_MODELS.keys()),
        index=list(DOCUMENT_MODELS.keys()).index(st.session_state.selected_model),
        help="Choose the type of document to analyze"
    )
    
    # Display model information
    model_id = DOCUMENT_MODELS[selected_model]
    st.sidebar.info(f"**Model**: {model_id}")
    
    # Add descriptions for each model type
    model_descriptions = {
        "Invoice": "Extract structured data from invoices including vendor, customer, items, totals, etc.",
        "Receipt": "Extract data from receipts including merchant name, transaction date, items, and totals",
        "ID Card": "Extract data from identity documents like driver's licenses, passports, etc.",
        "Bank Statement": "Extract layout and text from bank statements and financial documents",
        "Layout": "Extract text, tables, and layout information from any document"
    }
    
    st.sidebar.info(f"**Description**: {model_descriptions.get(selected_model, 'Document analysis')}")
    
    # Supported fields for each model type
    supported_fields = {
        "Invoice": ["VendorName", "CustomerName", "InvoiceTotal", "DueDate", "InvoiceDate", "Items"],
        "Receipt": ["MerchantName", "TransactionDate", "Total", "Subtotal", "Items"],
        "ID Card": ["FirstName", "LastName", "DocumentNumber", "DateOfBirth", "DateOfExpiration", "Address"],
        "Bank Statement": ["Tables", "Text", "KeyValuePairs", "SelectionMarks"],
        "Layout": ["Tables", "Text", "Lines", "Words", "SelectionMarks"]
    }
    
    # Supported fields
    with st.sidebar.expander("Supported Fields"):
        for field in supported_fields.get(selected_model, []):
            st.write(f"• {field}")
    
    st.session_state.selected_model = selected_model
    
    return endpoint, key, selected_model


def upload_file():
    """Handle file upload"""
    uploaded_file = st.file_uploader(
        "Upload Document",
        type=SUPPORTED_FILE_TYPES,
        help=f"Supported formats: {', '.join(SUPPORTED_FILE_TYPES).upper()}"
    )
    
    if uploaded_file is not None:
        # Display file information
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Name", uploaded_file.name)
        with col2:
            st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
        with col3:
            st.metric("File Type", uploaded_file.type)
        
        return uploaded_file.read()
    
    return None


def process_document(file_bytes, endpoint, key, model_type):
    """Process document with Azure Document Intelligence"""
    if not endpoint or not key:
        st.error("Please provide Azure Document Intelligence endpoint and API key in the sidebar.")
        return None
    
    try:
        with st.spinner("🔍 Analyzing document..."):
            processor = DocumentProcessor(endpoint, key)
            extracted_data = processor.analyze_document(file_bytes, model_type)
        
        if extracted_data:
            st.success("✅ Document analysis completed!")
            return extracted_data
        else:
            st.error("❌ Failed to analyze document. Please check your credentials and try again.")
            return None
            
    except Exception as e:
        st.error(f"❌ Error processing document: {str(e)}")
        return None


def display_results(extracted_data, file_bytes):
    """Display analysis results with annotations and extracted data"""
    if not extracted_data:
        return
    
    # Create visualizer
    visualizer = DocumentVisualizer()
    
    # Create main layout columns
    col1, col2 = st.columns([1.2, 0.8])
    
    with col1:
        st.subheader("📄 Document with Annotations")
        
        # Field filter
        all_fields = [field["name"] for field in extracted_data.get("fields", [])]
        if all_fields:
            selected_fields = st.multiselect(
                "Filter Fields to Display",
                options=all_fields,
                default=all_fields[:10],  # Show first 10 by default
                help="Select which fields to highlight on the document"
            )
        else:
            selected_fields = []
        
        # Draw annotations
        annotated_image = visualizer.draw_annotations(file_bytes, extracted_data, selected_fields)
        st.image(annotated_image, caption="Document with Extracted Fields", use_container_width=True)
        
        # Display legend
        st.markdown(visualizer.create_legend(), unsafe_allow_html=True)
    
    with col2:
        st.subheader("📊 Extracted Data")
        
        # Confidence statistics
        confidence_stats = extracted_data.get("confidence_stats", {"high": 0, "medium": 0, "low": 0})
        chart_data = create_confidence_chart(confidence_stats)
        
        fig = go.Figure(data=[go.Pie(
            labels=chart_data['labels'],
            values=chart_data['values'],
            marker_colors=chart_data['colors'],
            hole=0.4
        )])
        fig.update_layout(
            title="Confidence Distribution",
            height=300,
            margin=dict(t=50, b=0, l=0, r=0)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary metrics
        total_fields = sum(confidence_stats.values())
        if total_fields > 0:
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Total Fields", total_fields)
            with col_b:
                high_percentage = (confidence_stats["high"] / total_fields) * 100
                st.metric("High Confidence", f"{high_percentage:.1f}%")


def display_detailed_results(extracted_data):
    """Display detailed extracted data in expandable sections"""
    st.subheader("🔍 Detailed Results")
    
    # Fields section
    fields = extracted_data.get("fields", [])
    if fields:
        with st.expander(f"📝 Extracted Fields ({len(fields)})", expanded=True):
            # Create DataFrame for better display
            field_data = []
            for field in fields:
                field_data.append({
                    "Field Name": field["name"],
                    "Value": str(field["value"])[:100] + "..." if len(str(field["value"])) > 100 else str(field["value"]),
                    "Confidence": f"{field['confidence']:.2%}",
                    "Type": field.get("type", "string"),
                    "Page": field.get("page_number", 1)
                })
            
            df_fields = pd.DataFrame(field_data)
            st.dataframe(df_fields, use_container_width=True)
            
            # Detailed field view
            selected_field = st.selectbox(
                "View Field Details",
                options=[field["name"] for field in fields],
                help="Select a field to view detailed information"
            )
            
            if selected_field:
                field_detail = next(field for field in fields if field["name"] == selected_field)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Confidence", f"{field_detail['confidence']:.2%}")
                with col2:
                    st.metric("Type", field_detail.get("type", "string"))
                with col3:
                    st.metric("Page", field_detail.get("page_number", 1))
                
                st.text_area("Full Value", field_detail["value"], height=100)
                
                if field_detail.get("polygon"):
                    st.json({"coordinates": field_detail["polygon"]})
    
    # Tables section
    tables = extracted_data.get("tables", [])
    if tables:
        with st.expander(f"📊 Tables ({len(tables)})"):
            for i, table in enumerate(tables):
                st.subheader(f"Table {i+1} ({table['row_count']}x{table['column_count']})")
                
                # Create table DataFrame
                cells = table.get("cells", [])
                if cells:
                    # Initialize empty table
                    table_array = [["" for _ in range(table['column_count'])] for _ in range(table['row_count'])]
                    
                    # Fill table with cell content
                    for cell in cells:
                        row_idx = cell["row_index"]
                        col_idx = cell["column_index"]
                        if row_idx < len(table_array) and col_idx < len(table_array[0]):
                            table_array[row_idx][col_idx] = cell["content"]
                    
                    # Convert to DataFrame
                    df_table = pd.DataFrame(table_array)
                    st.dataframe(df_table, use_container_width=True)
                
                st.json({"table_metadata": {
                    "rows": table['row_count'],
                    "columns": table['column_count'],
                    "total_cells": len(cells)
                }})


def main():
    """Main application"""
    st.set_page_config(
        page_title="Azure Document Intelligence POC",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Main title
    st.title("📄 Azure Document Intelligence POC")
    st.markdown("""
    **Analyze invoices, bank statements, and ID cards with AI-powered document understanding**
    
    Upload a document, select the appropriate model, and get structured data extraction with visual annotations.
    """)
    
    # Setup sidebar
    endpoint, key, selected_model = setup_sidebar()
    
    # File upload
    st.subheader("📤 Upload Document")
    file_bytes = upload_file()
    
    if file_bytes:
        # Store original image
        st.session_state.original_image = file_bytes
        
        # Process button
        if st.button("🚀 Analyze Document", type="primary"):
            extracted_data = process_document(file_bytes, endpoint, key, selected_model)
            st.session_state.extracted_data = extracted_data
        
        # Display results if available
        if st.session_state.extracted_data:
            st.divider()
            display_results(st.session_state.extracted_data, file_bytes)
            st.divider()
            display_detailed_results(st.session_state.extracted_data)
        
        # Download results
        if st.session_state.extracted_data:
            st.subheader("💾 Export Results")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Export as JSON
                import json
                json_data = json.dumps(st.session_state.extracted_data, indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"extracted_data_{selected_model.lower().replace(' ', '_')}.json",
                    mime="application/json"
                )
            
            with col2:
                # Export fields as CSV
                fields = st.session_state.extracted_data.get("fields", [])
                if fields:
                    df = pd.DataFrame([{
                        "field_name": f["name"],
                        "value": f["value"],
                        "confidence": f["confidence"],
                        "type": f.get("type", "string")
                    } for f in fields])
                    
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"extracted_fields_{selected_model.lower().replace(' ', '_')}.csv",
                        mime="text/csv"
                    )
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>Built with Streamlit and Azure Document Intelligence</p>
        <p>Supports Invoice, Bank Statement, and ID Card analysis</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main() 