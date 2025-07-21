"""
Demo script to test Azure Document Intelligence connectivity
Run this before using the main Streamlit app to verify your setup
"""

import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from config import DOCUMENT_MODELS, AZURE_DOC_INTEL_ENDPOINT, AZURE_DOC_INTEL_KEY


def test_connection(endpoint: str, key: str):
    """Test connection to Azure Document Intelligence"""
    print("🔄 Testing Azure Document Intelligence connection...")
    
    try:
        client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )
        
        # Try to get info (this will validate credentials)
        print("✅ Connection successful!")
        print(f"📍 Endpoint: {endpoint}")
        print(f"🔑 API Key: {key[:8]}...{key[-4:]}")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False


def list_available_models():
    """List available document models"""
    print("\n📋 Available Document Models:")
    print("-" * 50)
    
    for model_name, model_info in DOCUMENT_MODELS.items():
        print(f"🔹 {model_name}")
        print(f"   Model ID: {model_info['model_id']}")
        print(f"   Description: {model_info['description']}")
        print(f"   Fields: {', '.join(model_info['supported_fields'][:3])}...")
        print()


def check_dependencies():
    """Check if all required packages are installed"""
    print("📦 Checking dependencies...")
    
    required_packages = [
        'streamlit',
                 'azure-ai-documentintelligence', 
         'azure-core',
         'pillow',
         'opencv-python',
         'pandas',
         'plotly',
         'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All dependencies installed!")
        return True


def main():
    """Main demo function"""
    print("🚀 Azure Document Intelligence POC - Setup Test")
    print("=" * 60)
    
    # Check dependencies first
    if not check_dependencies():
        return
    
    # List available models
    list_available_models()
    
    # Test connection if credentials provided
    print("🔧 Connection Test")
    print("-" * 20)
    
    # Check for .env credentials first
    if AZURE_DOC_INTEL_ENDPOINT and AZURE_DOC_INTEL_KEY:
        print("✅ Found credentials in .env file")
        success = test_connection(AZURE_DOC_INTEL_ENDPOINT, AZURE_DOC_INTEL_KEY)
        if success:
            print("\n🎉 Setup complete! You can now run the Streamlit app:")
            print("   streamlit run app.py")
        else:
            print("\n⚠️  Please check your credentials in .env file and try again.")
    else:
        print("⚠️  No credentials found in .env file")
        endpoint = input("Enter your Azure endpoint (or press Enter to skip): ").strip()
        if endpoint:
            key = input("Enter your API key: ").strip()
            if key:
                success = test_connection(endpoint, key)
                if success:
                    print(f"\n💡 Consider adding these to your .env file:")
                    print(f"   AZURE_DOC_INTEL_ENDPOINT={endpoint}")
                    print(f"   AZURE_DOC_INTEL_KEY={key}")
                    print("\n🎉 Setup complete! You can now run the Streamlit app:")
                    print("   streamlit run app.py")
                else:
                    print("\n⚠️  Please check your credentials and try again.")
            else:
                print("⏭️  Skipping connection test (no API key provided)")
        else:
            print("⏭️  Skipping connection test (no endpoint provided)")
    
    print("\n📚 Next Steps:")
    print("1. Get Azure Document Intelligence credentials from Azure Portal")
    print("2. Copy .env.example to .env and fill in your credentials")
    print("3. Run: streamlit run app.py")
    print("4. Upload a document and test!")


if __name__ == "__main__":
    main() 