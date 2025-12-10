import google.generativeai as genai
import os

# Using the key from brain.py
GENAI_API_KEY = "AIzaSyAyq1urrux5d0amkeyQ-XycxD37mR8YizY"
genai.configure(api_key=GENAI_API_KEY)

try:
    print(f"Testing Gemini API with key: {GENAI_API_KEY[:5]}...{GENAI_API_KEY[-5:]}")
    model = genai.GenerativeModel('gemini-flash-latest')
    response = model.generate_content("Hello, can you hear me? Respond with 'Yes, I am working'.")
    print("\nSUCCESS! Gemini Responded:")
    print(response.text)
except Exception as e:
    print("\nFAILURE! Gemini API Error:")
    print(e)
