import os
import json
import streamlit as st
from PIL import Image
import google.generativeai as genai
from twilio.rest import Client
from dotenv import load_dotenv
import prompts

# Load environment variables
load_dotenv()

# ==========================================
# 1. Page Configuration & Modern Styling
# ==========================================
st.set_page_config(
    page_title="MacroSnap - Snap it. Track it. Text yourself.",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Gradient Title */
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10b981 0%, #059669 50%, #047857 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    
    /* Welcome Message Box */
    .welcome-card {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 1.25rem;
        color: #166534;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Secret & Config Helper
# ==========================================
def get_secret(key_name: str, group: str = None) -> str:
    """Safely fetch keys from st.secrets or os.environ."""
    if hasattr(st, "secrets"):
        if group and group in st.secrets and key_name in st.secrets[group]:
            return st.secrets[group][key_name]
        elif key_name in st.secrets:
            return st.secrets[key_name]
    return os.getenv(key_name, "")

gemini_key = get_secret("GEMINI_API_KEY")
twilio_sid = get_secret("ACCOUNT_SID", group="twilio") or get_secret("TWILIO_ACCOUNT_SID")
twilio_auth = get_secret("AUTH_TOKEN", group="twilio") or get_secret("TWILIO_AUTH_TOKEN")
twilio_from = get_secret("WHATSAPP_NUMBER", group="twilio") or get_secret("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
twilio_content_sid = get_secret("CONTENT_SID", group="twilio") or get_secret("TWILIO_CONTENT_SID")

# ==========================================
# 3. Dynamic Model Resolution & Cached Model Factory
# ==========================================
def get_best_model_name(api_key: str) -> str:
    """Queries Google AI API to dynamically find available models for the user's key."""
    try:
        genai.configure(api_key=api_key)
        available_models = [
            m.name.replace("models/", "") 
            for m in genai.list_models() 
            if "generateContent" in m.supported_generation_methods
        ]
        
        priority_list = [
            "gemini-2.0-flash-lite-preview-02-05",
            "gemini-2.0-flash-lite-preview",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash-8b",
            "gemini-1.5-flash-lite",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-pro"
        ]
        
        for priority in priority_list:
            if priority in available_models:
                return priority
                
        if available_models:
            return available_models[0]
    except Exception:
        pass
        
    return "gemini-2.0-flash-lite"

@st.cache_resource
def get_gemini_model(api_key: str, system_instruction: str, model_name: str):
    """Factory for cached Gemini API model."""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_instruction
    )

def send_whatsapp_summary(account_sid, auth_token, from_number, to_number, text_summary, content_sid=None):
    """Sends WhatsApp message using Twilio Content Template or direct message."""
    client = Client(account_sid, auth_token)
    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"
        
    if content_sid and content_sid != "your_content_sid_here" and len(content_sid) > 5:
        msg = client.messages.create(
            from_=from_number,
            to=to_number,
            content_sid=content_sid,
            content_variables=json.dumps({"1": text_summary})
        )
    else:
        msg = client.messages.create(
            from_=from_number,
            to=to_number,
            body=text_summary
        )
    return msg.sid

# ==========================================
# 4. Session State Initialization
# ==========================================
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_whatsapp" not in st.session_state:
    st.session_state.user_whatsapp = ""
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# ==========================================
# 5. Sidebar: Settings & Key Override
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Settings & Secrets")
    
    api_key_input = st.text_input(
        "Gemini API Key",
        value=gemini_key,
        type="password"
    )
    active_gemini_key = api_key_input if api_key_input else gemini_key

    if active_gemini_key:
        detected_model = get_best_model_name(active_gemini_key)
        st.caption(f"🤖 Active Model: `{detected_model}`")

    if st.session_state.onboarded:
        st.markdown("---")
        st.markdown("### 👤 User Profile")
        st.write(f"**Name:** {st.session_state.user_name}")
        st.write(f"**WhatsApp:** `{st.session_state.user_whatsapp}`")
        if st.button("Reset Session / Re-onboard"):
            st.cache_resource.clear()
            st.session_state.onboarded = False
            st.session_state.messages = []
            st.session_state.chat_session = None
            st.rerun()

    st.markdown("---")
    st.markdown("### 💡 Sandbox Tip")
    st.caption("If WhatsApp fails to deliver, resend `join <sandbox-code>` to **+1 415 523 8886** on WhatsApp.")

# ==========================================
# 6. STEP 5/8: Onboarding Screen
# ==========================================
if not st.session_state.onboarded:
    st.markdown("<h1 class='main-title' style='text-align: center;'>👋 Welcome to MacroSnap</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title' style='text-align: center;'>Snap it. Track it. Text yourself the results.</p>", unsafe_allow_html=True)
    
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown("### 1️⃣ Onboarding: Enter your details")
        with st.form("onboarding_form"):
            name_val = st.text_input("Full Name", placeholder="e.g. Jane Doe")
            phone_val = st.text_input("WhatsApp Phone Number", placeholder="+14155238886")
            submit_btn = st.form_submit_button("Start Tracking 🚀", use_container_width=True)
            
            if submit_btn:
                if not name_val or not phone_val:
                    st.error("Please enter both your name and WhatsApp number to continue.")
                elif not active_gemini_key:
                    st.error("Missing Gemini API key in secrets!")
                else:
                    st.cache_resource.clear()
                    st.session_state.user_name = name_val
                    st.session_state.user_whatsapp = phone_val
                    st.session_state.onboarded = True
                    
                    target_model = get_best_model_name(active_gemini_key)
                    model = get_gemini_model(active_gemini_key, prompts.SYSTEM_PROMPT, target_model)
                    st.session_state.chat_session = model.start_chat(history=[])
                    st.rerun()

# ==========================================
# 7. STEPS 6/8 & 7/8: Main Chat & Send Summary Interface
# ==========================================
else:
    title_col, summary_btn_col = st.columns([3, 1])
    has_chat_history = len(st.session_state.messages) > 0
    
    with title_col:
        st.markdown("<h1 class='main-title'>🥗 MacroSnap AI</h1>", unsafe_allow_html=True)
        st.markdown(f"<p class='sub-title'>Logged as <b>{st.session_state.user_name}</b> ({st.session_state.user_whatsapp})</p>", unsafe_allow_html=True)
        
    with summary_btn_col:
        st.write("")
        send_summary_clicked = st.button(
            "📲 Send details to WhatsApp",
            disabled=not has_chat_history,
            type="primary" if has_chat_history else "secondary",
            use_container_width=True,
            help="Greyed out until you have a meal conversation to send!"
        )

    # Action when Send WhatsApp Summary is clicked
    if send_summary_clicked:
        if not active_gemini_key:
            st.error("Missing Gemini API Key!")
        else:
            with st.spinner("Asking Gemini to summarize your food log for WhatsApp..."):
                try:
                    target_model = get_best_model_name(active_gemini_key)
                    summary_model = get_gemini_model(active_gemini_key, prompts.SUMMARY_REQUEST_PROMPT, target_model)
                    chat_transcript = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                    
                    recap_response = summary_model.generate_content(
                        f"User Name: {st.session_state.user_name}\nSummarize this conversation into a clean WhatsApp recap:\n{chat_transcript}"
                    )
                    recap_text = recap_response.text
                    
                    if twilio_sid and twilio_auth:
                        sid = send_whatsapp_summary(
                            account_sid=twilio_sid,
                            auth_token=twilio_auth,
                            from_number=twilio_from,
                            to_number=st.session_state.user_whatsapp,
                            text_summary=recap_text,
                            content_sid=twilio_content_sid
                        )
                        st.balloons()
                        st.success(f"🎉 Summary sent to **{st.session_state.user_whatsapp}** via Twilio! (SID: `{sid}`)")
                    else:
                        st.warning("Twilio API credentials missing in secrets. Here is your generated WhatsApp summary:")
                        st.code(recap_text, language="text")
                        
                except Exception as e:
                    st.error(f"Error sending WhatsApp summary: {str(e)}")

    # Welcome Card
    welcome_text = prompts.WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.get("user_name", "there"))
    st.markdown(f"<div class='welcome-card'>{welcome_text}</div>", unsafe_allow_html=True)

    # Replay chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if "image" in msg and msg["image"]:
                st.image(msg["image"], use_container_width=True)
            st.markdown(msg["content"])

    # Chat Input & Photo Uploader
    col_img, col_txt = st.columns([1, 2])
    with col_img:
        uploaded_image = st.file_uploader("📷 Attach Meal Photo (Optional)", type=["jpg", "jpeg", "png", "webp"])
        img_obj = Image.open(uploaded_image) if uploaded_image else None
        if img_obj:
            st.image(img_obj, caption="Attached Meal Photo", width=240)

    with col_txt:
        user_input = st.chat_input("Ask a question or log your meal...")

    # Process message when user enters text OR uploads an image
    if user_input or img_obj:
        prompt_text = user_input if user_input else "Analyze this meal photo and break down the estimated calories and macros (protein, carbs, fat)."

        if active_gemini_key:
            user_msg_data = {"role": "user", "content": prompt_text}
            if img_obj:
                user_msg_data["image"] = img_obj
            st.session_state.messages.append(user_msg_data)
            
            with st.chat_message("user"):
                if img_obj:
                    st.image(img_obj, use_container_width=True)
                st.markdown(prompt_text)

            with st.chat_message("assistant"):
                with st.spinner("MacroSnap is calculating your macros & calories..."):
                    try:
                        target_model = get_best_model_name(active_gemini_key)
                        
                        if st.session_state.chat_session is None:
                            model = get_gemini_model(active_gemini_key, prompts.SYSTEM_PROMPT, target_model)
                            st.session_state.chat_session = model.start_chat(history=[])

                        if img_obj:
                            res = st.session_state.chat_session.send_message([prompt_text, img_obj])
                        else:
                            res = st.session_state.chat_session.send_message(prompt_text)
                            
                        assistant_text = res.text
                        st.markdown(assistant_text)
                        st.session_state.messages.append({"role": "assistant", "content": assistant_text})
                        
                    except Exception as e:
                        try:
                            st.cache_resource.clear()
                            genai.configure(api_key=active_gemini_key)
                            fallback_name = get_best_model_name(active_gemini_key)
                            fallback_model = genai.GenerativeModel(fallback_name, system_instruction=prompts.SYSTEM_PROMPT)
                            st.session_state.chat_session = fallback_model.start_chat(history=[])
                            
                            if img_obj:
                                res = st.session_state.chat_session.send_message([prompt_text, img_obj])
                            else:
                                res = st.session_state.chat_session.send_message(prompt_text)
                                
                            assistant_text = res.text
                            st.markdown(assistant_text)
                            st.session_state.messages.append({"role": "assistant", "content": assistant_text})
                        except Exception as err:
                            st.error(f"Chat generation error: {str(err)}")
