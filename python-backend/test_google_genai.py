#!/usr/bin/env python3
"""
Test script to verify Google Generative AI SDK installation and basic functionality.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_imports():
    """Test that we can import the required modules."""
    try:
        from google import genai
        print("✓ Successfully imported google.genai")
        return True
    except ImportError as e:
        print(f"✗ Failed to import google.genai: {e}")
        return False

def test_client_initialization():
    """Test that we can initialize the Google Generative AI client."""
    try:
        from google import genai
        
        # Get API key from environment
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("✗ GOOGLE_API_KEY not found in environment variables")
            return False
            
        # Initialize client
        client = genai.Client(api_key=api_key)
        print("✓ Successfully initialized Google Generative AI client")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize Google Generative AI client: {e}")
        return False

def test_list_models():
    """Test that we can list available models."""
    try:
        from google import genai
        import os
        
        # Get API key from environment
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("✗ GOOGLE_API_KEY not found in environment variables")
            return False
            
        # Initialize client
        client = genai.Client(api_key=api_key)
        
        # List models (this will verify the API key works)
        models = client.models.list()
        print("✓ Successfully listed models:")
        for model in models:
            print(f"  - {model.name}")
        return True
    except Exception as e:
        print(f"✗ Failed to list models: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Google Generative AI SDK setup...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_client_initialization,
        test_list_models
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! The Google Generative AI SDK is properly configured.")
    else:
        print("❌ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()