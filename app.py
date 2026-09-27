import json
import os
import streamlit as st
from google import genai
from google.genai import types
from twilio.rest import Client as TwilioClient
from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE, SUMMARY_REQUEST_PROMPT

# ==========================================
# 1. Page Configuration & Setup
# ==========================================
st.set_page_config(
    page_title="MacroSnap - Snap it. Track it. Text yourself.",
    page_icon="🥗",
    layout="centered"
)

# Helper function to fetch secrets from st.secrets or os.environ
def get_secret(key_name: str, default: str = "") -> str:
    if hasattr(st, "secrets") and key_name in st.secrets:
        return st.secrets[key_name]
    return os.getenv(key_name, default)

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
TWILIO_ACCOUNT_SID = get_secret("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = get_secret("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = get_secret("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_CONTENT_SID = get_secret("TWILIO_CONTENT_SID")

# ==========================================
# 2. Cached Clients Factory (@st.cache_resource)
# ==========================================
@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_twilio_client():
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        return TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return None

gemini_client = get_gemini_client()
twilio_client = get_twilio_client()

# Model resolution with fallback options
MODEL_NAMES = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro"]

def get_working_model():
    """Finds the first available working Gemini model for the API key."""
    try:
        models = [m.name.replace("models/", "") for m in gemini_client.models.list()]
        for m in MODEL_NAMES:
            if m in models:
                return m
    except Exception:
        pass
    return "gemini-1.5-flash"

MODEL_NAME = get_working_model()

# ==========================================
# 3. WhatsApp Messaging Helper
# ==========================================
def clean_whatsapp_text(text):
    if not text:
        return "No nutrition summary available."
    text = " ".join(text.split())
    return text[:1500] + "..." if len(text) > 1500 else text

def send_whatsapp(to_number, user_name, summary):
    if not twilio_client:
        return False, "Twilio credentials missing in secrets."
    try:
        content_variables = json.dumps(
            {"1": user_name, "2": clean_whatsapp_text(summary)}, ensure_ascii=False
        )
        if TWILIO_CONTENT_SID and len(TWILIO_CONTENT_SID) > 5 and TWILIO_CONTENT_SID != "your_content_sid_here":
            message = twilio_client.messages.create(
                from_=TWILIO_WHATSAPP_FROM,
                to=f"whatsapp:{to_number}",
                content_sid=TWILIO_CONTENT_SID,
                content_variables=content_variables,
            )
        else:
            message = twilio_client.messages.create(
                from_=TWILIO_WHATSAPP_FROM,
                to=f"whatsapp:{to_number}",
                body=f"🥗 MacroSnap Summary for {user_name}:\n\n{summary}"
            )
        return True, message.sid
    except Exception as error:
        return False, str(error)

# ==========================================
# 4. Chat Rendering & Session State Helpers
# ==========================================
def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])

def add_message(role, kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])

def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(parts).text
    except Exception as error:
        try:
            fallback_model = "gemini-1.5-flash"
            st.session_state.chat = gemini_client.chats.create(
                model=fallback_model,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            return st.session_state.chat.send_message(parts).text
        except Exception as err:
            return f"Sorry, something went wrong: {err}"

# ==========================================
# 5. STEP 1: Onboarding Screen (User Name & WhatsApp)
# ==========================================
if 'onboarded' not in st.session_state:
    st.title("🥗 MacroSnap")
    st.caption("Snap it. Track it. Text yourself the results.")

    with st.form("onboarding_form"):
        name = st.text_input("Your name")
        whatsapp_number = st.text_input(
            "WhatsApp number (with country code)",
            placeholder="+91XXXXXXXXXX",
            help="This is the number MacroSnap will text your summary to.",
        )

        submitted = st.form_submit_button("Let's go 🚀")

    if submitted:
        if not name.strip() or not whatsapp_number.strip():
            st.warning("Please fill in both your name and WhatsApp number.")
        else:
            st.session_state.name = name.strip()
            st.session_state.whatsapp_number = whatsapp_number.strip()
            # Activate AI chat session
            st.session_state.chat = gemini_client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            st.session_state.messages = []
            st.session_state.onboarded = True
            st.rerun()
    st.stop()

# ==========================================
# 6. Main Chat Interface
# ==========================================
header_col, button_col = st.columns([5, 2], vertical_alignment="center")

with header_col:
    st.title("🥗 MacroSnap")

with button_col:
    send_disabled = len(st.session_state.messages) <= 1
    if st.button("📤 Send to WhatsApp", disabled=send_disabled, use_container_width=True):
        with st.spinner("Summarizing your day..."):
            summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
        success, info = send_whatsapp(st.session_state.whatsapp_number, st.session_state.name, summary)
        if success:
            st.success("Sent! Check your WhatsApp 📲")
        else:
            st.error(f"Couldn't send that: {info}")

st.caption(f"Logged in as {st.session_state.name} - updates go to {st.session_state.whatsapp_number}")

if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)

# Chat Input supporting text & photo attachment
user_input = st.chat_input(
    "Ask a question, or attach a photo of your meal",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts = []

    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append("What is this meal? Give me the calories and macros.")

    with st.spinner("Crunching the numbers..."):
        answer = ask_gemini(parts)
    add_message("assistant", "text", answer)
