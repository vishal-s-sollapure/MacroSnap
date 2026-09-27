import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Read from secrets or environment
key = os.getenv("GEMINI_API_KEY")
if not key:
    try:
        key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        key = ""

print(f"Testing key starting with: {key[:8]}...")
try:
    genai.configure(api_key=key)
    print("Listing available models:")
    found = False
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name} (Methods: {m.supported_generation_methods})")
            found = True
    if not found:
        print("No generateContent models found.")
except Exception as e:
        print(f"Error listing models: {e}")
