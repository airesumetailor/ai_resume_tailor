import os
import re
import io
import json
import zipfile
import asyncio
import base64
import mimetypes
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

try:
    from streamlit_pdf_viewer import pdf_viewer
    HAS_PDF_VIEWER = True
except ImportError:
    HAS_PDF_VIEWER = False

from ai_generator import generate_application_data

# ==============================================================================
# CONFIGURATION & GLOBAL SETUP
# ==============================================================================
AUTH_TOKEN = "123"  # Replace with your actual security token
INPUT_DIR = Path("input")
INPUT_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="AI Resume Tailor", 
    page_icon=":material/auto_awesome:",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# PROFESSIONAL NAVY BLUE CUSTOM CSS & TOOLTIP REMOVAL SCRIPT
# ==============================================================================
st.markdown("""
<style>
    /* Global Styling */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }

    /* Navy Blue Header Banner */
    .app-header {
        background: linear-gradient(135deg, #0b192c 0%, #1e3e62 100%);
        padding: 1.8rem 2rem;
        border-radius: 10px;
        color: #ffffff;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(11, 25, 44, 0.15);
    }
    .app-header h1 {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.75rem !important;
        margin: 0 0 0.25rem 0 !important;
        letter-spacing: -0.02em;
    }
    .app-header p {
        color: #93c5fd !important;
        font-size: 0.95rem !important;
        margin: 0 !important;
    }

    /* Cards & Containers */
    .stCard {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }

    /* Input Fields */
    div[data-baseweb="input"] > div, 
    div[data-baseweb="textarea"] > div {
        border-color: #cbd5e1 !important;
        border-radius: 6px !important;
    }

    div[data-baseweb="input"]:focus-within > div, 
    div[data-baseweb="textarea"]:focus-within > div {
        border-color: #0b192c !important;
        box-shadow: 0 0 0 1px #0b192c !important;
    }

    /* Remove Streamlit Form Tooltips & Popovers */
    div[data-testid="stFormSubmitTooltip"],
    div[data-testid="stTooltipHoverTarget"],
    div[data-baseweb="popover"],
    div[data-baseweb="tooltip"],
    div[role="tooltip"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    button[data-testid="stFormSubmitButton"]::after,
    button[data-testid="stFormSubmitButton"]::before,
    div[data-testid="stFormSubmitButton"] *::after,
    div[data-testid="stFormSubmitButton"] *::before {
        display: none !important;
        content: "" !important;
        opacity: 0 !important;
    }

    input[type="password"]::-ms-reveal,
    input[type="password"]::-ms-clear,
    input[type="password"]::-webkit-contacts-auto-fill-button,
    input[type="password"]::-webkit-credentials-auto-fill-button {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }

    *:focus {
        outline-color: #0b192c !important;
    }

    /* Tables */
    div[data-testid="stTable"], table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        font-size: 0.9rem;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
    th {
        background-color: #0b192c !important;
        color: #ffffff !important;
        font-weight: 600;
        text-align: left;
        padding: 10px 14px;
    }
    td {
        padding: 10px 14px;
        border-bottom: 1px solid #e2e8f0;
        color: #1e293b;
    }
    tr:nth-child(even) {
        background-color: #f8fafc;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: transparent !important;
        padding: 4px 0px;
        border-bottom: 2px solid #e2e8f0;
    }

    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 6px 6px 0px 0px;
        padding: 0 16px;
        font-weight: 500;
        font-size: 0.875rem;
        color: #475569;
        border: none !important;
        background-color: transparent !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0b192c !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #0b192c !important;
    }

    /* Buttons */
    .stButton>button, div[data-testid="stFormSubmitButton"]>button {
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.875rem;
        padding: 0.5rem 1.25rem;
        transition: all 0.15s ease-in-out;
    }

    div[data-testid="stButton"] button[kind="primary"], 
    div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stDownloadButton"] button {
        background-color: #0b192c !important;
        border-color: #0b192c !important;
        color: #ffffff !important;
    }
    
    div[data-testid="stButton"] button[kind="primary"]:hover, 
    div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stDownloadButton"] button:hover {
        background-color: #1e3e62 !important;
        border-color: #1e3e62 !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>

<script>
    const removeFormTooltips = () => {
        const targets = document.querySelectorAll('button[data-testid="stFormSubmitButton"], div[data-testid="stFormSubmitButton"] *, div[data-testid="stTooltipHoverTarget"]');
        targets.forEach(el => {
            if (el.hasAttribute('title')) {
                el.removeAttribute('title');
            }
        });
    };

    const observer = new MutationObserver(removeFormTooltips);
    observer.observe(document.body, { childList: true, subtree: true });
    removeFormTooltips();
</script>
""", unsafe_allow_html=True)

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def sanitize_folder_name(name: str) -> str:
    if not name:
        return "General"
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return cleaned.replace(" ", "_") or "General"


def build_file_name(prefix_type: str) -> str:
    """
    Constructs filenames using the user name from Tab 1.
    If no name is provided, returns 'Resume.pdf' or 'Cover_Letter.pdf'.
    If name is provided, returns '{Name}_Resume.pdf' or '{Name}_Cover_Letter.pdf'.
    """
    raw_name = st.session_state.get("user_full_name", "").strip()
    if raw_name:
        sanitized = re.sub(r'[\\/*?:"<>|]', "", raw_name).strip().replace(" ", "_")
        if sanitized:
            return f"{sanitized}_{prefix_type}.pdf"
    return f"{prefix_type}.pdf"


def render_html_str(data, context_key, photo_path, template_filename):
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template(template_filename)
    
    photo_data_uri = None
    if photo_path and Path(photo_path).exists():
        p = Path(photo_path)
        mime_type, _ = mimetypes.guess_type(p)
        mime_type = mime_type or "image/png"
        img_bytes = p.read_bytes()
        encoded = base64.b64encode(img_bytes).decode("utf-8")
        photo_data_uri = f"data:{mime_type};base64,{encoded}"

    context = {
        context_key: data,
        "photo_path": photo_data_uri
    }
    return template.render(**context)


async def convert_html_str_to_pdf_bytes(html_content: str, scale: float = 1.0) -> bytes:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            scale=scale,
            margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"}
        )
        await browser.close()
        return pdf_bytes


def compile_documents(resume_data, cover_data, resume_scale=1.15, cover_scale=1.00):
    """Helper to render HTML and compile PDFs with specified scale values."""
    recipient_dict = cover_data.get("recipient", {}) if isinstance(cover_data, dict) else {}
    company_name_raw = (
        recipient_dict.get("company_name")
        or recipient_dict.get("company")
        or "General"
    )
    company_folder = sanitize_folder_name(company_name_raw)
    current_photo_path = st.session_state.get("photo_path")

    resume_html = render_html_str(resume_data, "resume", current_photo_path, "resume_template.html")
    cover_html = render_html_str(cover_data, "cover_letter", None, "cover_letter_template.html")

    resume_pdf_bytes = asyncio.run(convert_html_str_to_pdf_bytes(resume_html, scale=resume_scale))
    cover_pdf_bytes = asyncio.run(convert_html_str_to_pdf_bytes(cover_html, scale=cover_scale))

    st.session_state["resume_html"] = resume_html
    st.session_state["cover_html"] = cover_html
    st.session_state["resume_pdf_bytes"] = resume_pdf_bytes
    st.session_state["cover_pdf_bytes"] = cover_pdf_bytes

    # Dynamic file names
    resume_filename = build_file_name("Resume")
    cover_filename = build_file_name("Cover_Letter")

    # Package files into ZIP archive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(f"{company_folder}/{resume_filename}", resume_pdf_bytes)
        zip_file.writestr(f"{company_folder}/{cover_filename}", cover_pdf_bytes)
        zip_file.writestr(f"{company_folder}/resume.html", resume_html.encode("utf-8"))
        zip_file.writestr(f"{company_folder}/cover_letter.html", cover_html.encode("utf-8"))

    zip_buffer.seek(0)
    st.session_state["zip_data"] = zip_buffer.getvalue()
    st.session_state["zip_filename"] = f"{company_folder}_Application.zip"


# ==============================================================================
# AUTHENTICATION
# ==============================================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def authenticate():
    token_input = st.session_state.get("token_input_field", "")
    if token_input == AUTH_TOKEN:
        st.session_state.authenticated = True
        st.session_state.auth_error = False
    else:
        st.session_state.auth_error = True

if not st.session_state.authenticated:
    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="stCard" style="text-align: center;">
            <h2 style="margin-bottom: 0.5rem; color: #0b192c;">AI Resume Tailor</h2>
            <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 1.5rem;">Sign in with your access token</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.text_input(
            "Access Token", 
            type="password", 
            placeholder="Enter your authentication token",
            key="token_input_field",
            on_change=authenticate
        )
        
        submit = st.button("Sign In", use_container_width=True, type="primary", on_click=authenticate)
        
        if st.session_state.get("auth_error", False):
            st.error("Invalid Access Token.")

    st.stop()


# ==============================================================================
# MAIN APPLICATION DASHBOARD
# ==============================================================================
st.markdown("""
<div class="app-header">
    <h1>AI Resume Tailor</h1>
    <p>Tailor high-impact resumes and cover letters backed by AI generation.</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "**1. Basic Details**", 
    "**2. Base Resume**", 
    "**3. Base Cover Letter**", 
    "**4. Job Description & Tailor**", 
    "**5. Review & Edit**",
    "**6. Preview & Export**"
])

# ------------------------------------------------------------------------------
# TAB 1: BASIC DETAILS & PHOTO
# ------------------------------------------------------------------------------
with tab1:
    st.markdown("### Profile & Personal Details")
    st.caption("Configure personal details and profile picture.")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        c1, c2 = st.columns(2)
        with c1:
            full_name = st.text_input("Full Name", value=st.session_state.get("user_full_name", ""))
            email = st.text_input("Email Address", value=st.session_state.get("user_email", ""))
        with c2:
            phone = st.text_input("Phone Number", value=st.session_state.get("user_phone", ""))
            location = st.text_input("Location", value=st.session_state.get("user_location", ""))
        
        st.session_state["user_full_name"] = full_name
        st.session_state["user_email"] = email
        st.session_state["user_phone"] = phone
        st.session_state["user_location"] = location

    with col_right:
        uploaded_photo = st.file_uploader("Upload Profile Photo", type=["jpg", "jpeg", "png"])
        if uploaded_photo:
            photo_ext = uploaded_photo.name.split(".")[-1]
            photo_save_path = INPUT_DIR / f"profile_photo.{photo_ext}"
            photo_save_path.write_bytes(uploaded_photo.getvalue())
            st.session_state["photo_path"] = str(photo_save_path.resolve())
            st.image(uploaded_photo, caption="Uploaded Photo Preview", width=120)
        else:
            if "photo_path" not in st.session_state:
                st.session_state["photo_path"] = None

# ------------------------------------------------------------------------------
# TAB 2: BASE RESUME
# ------------------------------------------------------------------------------
with tab2:
    col_header, col_btn = st.columns([3, 1], vertical_alignment="bottom")
    with col_header:
        st.markdown("### Base Resume Data")
        st.caption("Manage your master resume JSON schema.")
    with col_btn:
        save_resume_clicked = st.button("Save Base Resume JSON", type="primary", use_container_width=True)

    resume_file = st.file_uploader("Import Resume JSON", type=["json"], key="resume_uploader")
    
    default_resume_path = INPUT_DIR / "base_resume.json"
    initial_resume_str = "{}"
    if resume_file is not None:
        initial_resume_str = resume_file.getvalue().decode("utf-8")
    elif default_resume_path.exists():
        initial_resume_str = default_resume_path.read_text(encoding="utf-8")

    base_resume_text = st.text_area(
        "Base Resume JSON Configuration:", 
        value=initial_resume_str, 
        height=380
    )
    
    if save_resume_clicked:
        try:
            parsed = json.loads(base_resume_text)
            default_resume_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
            st.toast("Successfully updated base resume configuration!", icon="✅")
        except Exception as e:
            st.toast(f"JSON Parsing Error: {e}", icon="🚨")

# ------------------------------------------------------------------------------
# TAB 3: BASE COVER LETTER
# ------------------------------------------------------------------------------
with tab3:
    col_header, col_btn = st.columns([3, 1], vertical_alignment="bottom")
    with col_header:
        st.markdown("### Base Cover Letter Data")
        st.caption("Manage your master cover letter JSON template.")
    with col_btn:
        save_cover_clicked = st.button("Save Base Cover Letter JSON", type="primary", use_container_width=True)

    cover_file = st.file_uploader("Import Cover Letter JSON", type=["json"], key="cover_uploader")
    
    default_cover_path = INPUT_DIR / "cover_letter_content.json"
    initial_cover_str = "{}"
    if cover_file is not None:
        initial_cover_str = cover_file.getvalue().decode("utf-8")
    elif default_cover_path.exists():
        initial_cover_str = default_cover_path.read_text(encoding="utf-8")

    base_cover_text = st.text_area(
        "Base Cover Letter JSON Configuration:", 
        value=initial_cover_str, 
        height=380
    )
    
    if save_cover_clicked:
        try:
            parsed = json.loads(base_cover_text)
            default_cover_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
            st.toast("Successfully updated base cover letter configuration!", icon="✅")
        except Exception as e:
            st.toast(f"JSON Parsing Error: {e}", icon="🚨")

# ------------------------------------------------------------------------------
# TAB 4: JOB DESCRIPTION & TAILOR
# ------------------------------------------------------------------------------
with tab4:
    col_header, col_btn = st.columns([3, 1], vertical_alignment="bottom")
    with col_header:
        st.markdown("### Target Job Description")
        st.caption("Paste the target role description to generate tailored content.")
    with col_btn:
        tailor_clicked = st.button("Tailor Application Content", type="primary", use_container_width=True)

    jd_input = st.text_area(
        "Job Description Text", 
        height=300, 
        placeholder="Paste role responsibilities, qualifications, and requirements...",
        label_visibility="collapsed"
    )
    
    if tailor_clicked:
        if not jd_input.strip():
            st.toast("Please paste a target Job Description before processing.", icon="⚠️")
        else:
            jd_path = INPUT_DIR / "jd.txt"
            base_resume_path = INPUT_DIR / "base_resume.json"
            
            jd_path.write_text(jd_input, encoding="utf-8")
            if not base_resume_path.exists():
                base_resume_path.write_text(base_resume_text, encoding="utf-8")

            # Non-blocking top-right toast notification
            st.toast("Analyzing requirements and generating optimized copy via Gemini AI...", icon="🤖")
            
            try:
                tailored_resume, tailored_cover = generate_application_data(
                    str(base_resume_path), str(jd_path)
                )
                
                if isinstance(tailored_resume, dict):
                    if "user_full_name" in st.session_state:
                        tailored_resume["name"] = st.session_state["user_full_name"]
                    if "contact" in tailored_resume and isinstance(tailored_resume["contact"], dict):
                        if "user_email" in st.session_state:
                            tailored_resume["contact"]["email"] = st.session_state["user_email"]
                        if "user_phone" in st.session_state:
                            tailored_resume["contact"]["phone"] = st.session_state["user_phone"]
                        if "user_location" in st.session_state:
                            tailored_resume["contact"]["location"] = st.session_state["user_location"]

                if isinstance(tailored_cover, dict):
                    sender_dict = tailored_cover.setdefault("sender", {})
                    if isinstance(sender_dict, dict):
                        if "user_full_name" in st.session_state:
                            sender_dict["name"] = st.session_state["user_full_name"]
                        if "user_email" in st.session_state:
                            sender_dict["email"] = st.session_state["user_email"]
                        if "user_phone" in st.session_state:
                            sender_dict["phone"] = st.session_state["user_phone"]

                st.session_state["tailored_resume"] = tailored_resume
                st.session_state["tailored_cover"] = tailored_cover
                st.toast("Generation complete! Proceed to Review & Edit.", icon="✨")
            except Exception as e:
                st.toast(f"AI Generation Failed: {e}", icon="🚨")

# ------------------------------------------------------------------------------
# TAB 5: REVIEW & EDIT
# ------------------------------------------------------------------------------
with tab5:
    col_header, col_btn = st.columns([3, 1], vertical_alignment="bottom")
    with col_header:
        st.markdown("### Fine-tune Payload")
        st.caption("Review and edit JSON payloads before document compilation.")
    with col_btn:
        build_docs_clicked = st.button("Build Documents & Compile PDFs", type="primary", use_container_width=True)

    if "tailored_resume" not in st.session_state or "tailored_cover" not in st.session_state:
        st.info("No generated session data found. Run tailoring in Tab 4 to generate documents.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### Tailored Resume Payload")
            edited_resume_str = st.text_area(
                "Resume JSON Editor", 
                value=json.dumps(st.session_state["tailored_resume"], indent=2),
                height=360,
                label_visibility="collapsed"
            )

        with col2:
            st.markdown("##### Tailored Cover Letter Payload")
            edited_cover_str = st.text_area(
                "Cover Letter JSON Editor", 
                value=json.dumps(st.session_state["tailored_cover"], indent=2),
                height=360,
                label_visibility="collapsed"
            )

        if build_docs_clicked:
            try:
                final_resume_data = json.loads(edited_resume_str)
                final_cover_data = json.loads(edited_cover_str)
                st.session_state["tailored_resume"] = final_resume_data
                st.session_state["tailored_cover"] = final_cover_data

                # Non-blocking top-right toast notification
                st.toast("Rendering HTML and producing print-ready PDFs...", icon="⚙️")

                resume_scale = st.session_state.get("resume_scale_input", 1.15)
                cover_scale = st.session_state.get("cover_scale_input", 1.00)

                compile_documents(
                    final_resume_data, 
                    final_cover_data, 
                    resume_scale=resume_scale, 
                    cover_scale=cover_scale
                )

                st.toast("Documents compiled successfully! Switch to Preview & Export.", icon="🚀")
            except Exception as e:
                st.toast(f"Compilation Failed: {e}", icon="🚨")

# ------------------------------------------------------------------------------
# TAB 6: PREVIEW & EXPORT
# ------------------------------------------------------------------------------
with tab6:
    st.markdown("### Document Preview & Package Export")

    if "zip_data" not in st.session_state:
        st.info("No compiled documents found. Click 'Build Documents & Compile PDFs' in Tab 5 first.")
    else:
        # Scale Controls & Export Actions
        col_controls, col_export = st.columns([2, 1], vertical_alignment="bottom")
        
        with col_controls:
            st.markdown("##### PDF Render Scaling")
            sc1, sc2, sc3 = st.columns([1, 1, 1], vertical_alignment="bottom")
            with sc1:
                r_scale = st.number_input(
                    "Resume Scale", 
                    min_value=0.5, 
                    max_value=2.0, 
                    value=st.session_state.get("resume_scale_input", 1.12), 
                    step=0.05,
                    key="resume_scale_input"
                )
            with sc2:
                c_scale = st.number_input(
                    "Cover Letter Scale", 
                    min_value=0.5, 
                    max_value=2.0, 
                    value=st.session_state.get("cover_scale_input", 1.00), 
                    step=0.05,
                    key="cover_scale_input"
                )
            with sc3:
                recompile = st.button("Re-compile PDFs", type="secondary", use_container_width=True)

        with col_export:
            st.download_button(
                label="Download ZIP Package",
                data=st.session_state["zip_data"],
                file_name=st.session_state["zip_filename"],
                mime="application/zip",
                type="primary",
                use_container_width=True
            )

        if recompile:
            st.toast("Re-rendering PDFs with updated scale factors...", icon="⚙️")
            try:
                compile_documents(
                    st.session_state["tailored_resume"], 
                    st.session_state["tailored_cover"], 
                    resume_scale=r_scale, 
                    cover_scale=c_scale
                )
                st.toast("PDFs re-compiled successfully!", icon="✅")
                st.rerun()
            except Exception as e:
                st.toast(f"Re-compilation Failed: {e}", icon="🚨")

        st.markdown("---")

        preview_tab1, preview_tab2 = st.tabs(["Resume Document", "Cover Letter Document"])

        with preview_tab1:
            view_type = st.radio("Display Format", ["PDF Document", "HTML Page"], horizontal=True, key="res_fmt_6")
            if view_type == "PDF Document":
                if HAS_PDF_VIEWER:
                    pdf_viewer(input=st.session_state["resume_pdf_bytes"], width=800)
                else:
                    base64_pdf = base64.b64encode(st.session_state["resume_pdf_bytes"]).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                components.html(st.session_state["resume_html"], height=800, scrolling=True)

        with preview_tab2:
            view_type_cl = st.radio("Display Format", ["PDF Document", "HTML Page"], horizontal=True, key="cl_fmt_6")
            if view_type_cl == "PDF Document":
                if HAS_PDF_VIEWER:
                    pdf_viewer(input=st.session_state["cover_pdf_bytes"], width=800)
                else:
                    base64_pdf = base64.b64encode(st.session_state["cover_pdf_bytes"]).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                components.html(st.session_state["cover_html"], height=800, scrolling=True)