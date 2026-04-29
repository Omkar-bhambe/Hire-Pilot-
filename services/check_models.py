import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load API key from your .env file
load_dotenv()

print("Attempting to list available Gemini models...")

try:
    # Configure the API with your key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file.")

    genai.configure(api_key=api_key)

    # List all models and check for the 'generateContent' method
    print("\n Found the following models that support content generation:")
    print("-" * 60)

    found_model = False
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(model.name)
            found_model = True

    if not found_model:
        print(
            "\n No models supporting 'generateContent' were found. Please check your API key and project permissions.")

except Exception as e:
    print(f"\n An error occurred: {e}")
    print("Please ensure your GOOGLE_API_KEY in the .env file is correct and your billing account is set up.")