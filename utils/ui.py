# --- 1. DESIGN THEME CONSTANTS ---
# Here we define the "Look and Feel" of the application.
# Think of these as the paint colors and materials we use for the house.
BG_COLOR = "#0c0e12"  # Deep charcoal background for the main screen
SIDEBAR_BG = "#11141a"  # Slightly lighter charcoal for the left menu
CARD_BG = "#161a21"  # The color of the boxes (cards) that hold information
TEXT_COLOR = "#e2e8f0"  # Off-white color to make text easy to read in the dark
METRIC_VALUE = "#ffffff"  # Bright white for important numbers (like money/credits)
BORDER_COLOR = "rgba(255, 255, 255, 0.08)"  # Subtle gray lines for borders
INPUT_BG = "#161a21"  # Background for text boxes where you type
CHART_BG = "rgba(0,0,0,0)"  # Transparent background for graphs
CHART_GRID = "rgba(255,255,255,0.05)"  # Very faint lines inside the graphs
SECONDARY_TEXT = "#94a3b8"  # Muted gray for less important labels

# Path to our company logo image
LOGO_PATH = "/Users/rohithp/Desktop/Agent_preneur/Streamlit_app/lyzr.png"

import streamlit as st
import base64
import os

# --- 2. IMAGE PROCESSING HELPERS ---
# These functions translate an image file into a format the website can understand.


def get_base64_of_bin_file(bin_file):
    """Converts a standard image file into a long string of characters (Base64)."""
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


def get_img_with_href(local_img_path):
    """Creates a 'web-ready' version of your local logo image."""
    if not os.path.exists(local_img_path):
        return ""
    img_format = local_img_path.split(".")[-1]
    bin_str = get_base64_of_bin_file(local_img_path)
    return f"data:image/{img_format};base64,{bin_str}"


# --- 3. THE MAGIC CSS (Styling Engine) ---
# This function sends a set of 'design rules' to the browser to make the app look premium.
# Non-technical explanation: This is like the interior design blueprint for the app.


def inject_custom_css():
    """Injects all premium CSS styling into the Streamlit app to create a 'Glassmorphism' look."""
    logo_base64 = get_img_with_href(LOGO_PATH)

    st.markdown(
        f"""
        <style>
        /* Import the modern 'Outfit' font from Google for a techy, professional look */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
        
        :root {{
            --primary-blue: #2563eb;
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-border: {BORDER_COLOR};
        }}

        /* --- OVERALL APP BODY --- */
        .stApp {{
            background-color: {BG_COLOR} !important;
            color: {TEXT_COLOR} !important;
            font-family: 'Outfit', sans-serif !important;
        }}

        /* Set font color for all headers and standard text */
        .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp span, .stApp label, .stApp div {{
            color: {TEXT_COLOR};
        }}

        /* --- THE LEFT SIDEBAR (compact, no vertical scroll) --- */
        [data-testid="stSidebar"] {{
            background-color: {SIDEBAR_BG} !important;
            border-right: 1px solid var(--glass-border) !important;
            padding: 0.6rem 0.75rem !important;
        }}
        
        /* Sidebar content container - tight spacing */
        [data-testid="stSidebar"] > div:first-child {{
            padding-top: 0 !important;
        }}
        
        [data-testid="stSidebar"] > div > div {{
            gap: 0.15rem !important;
        }}
        
        /* Logo container - compact */
        [data-testid="stSidebar"] .stMarkdown:has(img) {{
            margin-bottom: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            border-bottom: 1px solid var(--glass-border) !important;
        }}
        
        /* User info styling - compact */
        [data-testid="stSidebar"] .stMarkdown:has(strong) {{
            background: {CARD_BG} !important;
            padding: 0.4rem 0.6rem !important;
            border-radius: 8px !important;
            border: 1px solid var(--glass-border) !important;
            margin: 0.2rem 0 !important;
            font-size: 0.85rem !important;
        }}
        
        /* Metrics styling - compact */
        [data-testid="stSidebar"] [data-testid="stMetric"] {{
            background: {CARD_BG} !important;
            padding: 0.4rem 0.6rem !important;
            border-radius: 8px !important;
            border: 1px solid var(--glass-border) !important;
            margin: 0.25rem 0 !important;
        }}
        
        [data-testid="stSidebar"] [data-testid="stMetricLabel"] {{
            color: {SECONDARY_TEXT} !important;
            font-size: 0.68rem !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.04em !important;
        }}
        
        [data-testid="stSidebar"] [data-testid="stMetricValue"] {{
            color: {METRIC_VALUE} !important;
            font-size: 1.25rem !important;
            font-weight: 700 !important;
        }}
        
        /* Progress bar - compact */
        [data-testid="stSidebar"] [data-testid="stProgressBar"] {{
            margin: 0.25rem 0 !important;
            background-color: rgba(255, 255, 255, 0.05) !important;
            border-radius: 6px !important;
            overflow: hidden !important;
        }}
        
        [data-testid="stSidebar"] [data-testid="stProgressBar"] > div {{
            background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%) !important;
        }}
        
        /* Dividers - minimal gap */
        [data-testid="stSidebar"] hr {{
            margin: 0.4rem 0 !important;
            border-color: var(--glass-border) !important;
            opacity: 0.5 !important;
        }}
        
        /* Section captions - compact */
        [data-testid="stSidebar"] .stCaption {{
            color: {SECONDARY_TEXT} !important;
            font-size: 0.65rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
            margin-bottom: 0.3rem !important;
            margin-top: 0.2rem !important;
        }}
        
        /* Reduce default block gaps in sidebar so content fits without scroll */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
            gap: 0.15rem !important;
        }}
        
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {{
            padding: 0.1rem 0 !important;
        }}

        /* --- INFORMATION CARDS (The Boxes) --- */
        .metric-card {{
            background: {CARD_BG} !important;
            padding: 1.5rem;
            border-radius: 16px;
            border: 1px solid var(--glass-border) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            margin-bottom: 1rem;
        }}

        /* Make the box lift and highlight when you hover the mouse over it */
        .metric-card:hover {{
            border-color: #3b82f6 !important;
            transform: translateY(-2px);
        }}

        /* Style for the labels inside the boxes (e.g., 'Total Interactions') */
        .metric-title {{
            color: {SECONDARY_TEXT} !important;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.5rem;
        }}

        /* Style for the big numbers inside the boxes */
        .metric-value {{
            color: {METRIC_VALUE} !important;
            font-size: 2.25rem;
            font-weight: 700;
            margin: 0.25rem 0;
        }}

        /* The small blue pill-style badge (e.g., 'Active') */
        .status-badge {{
            display: inline-flex;
            padding: 4px 12px;
            border-radius: 8px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-top: 1rem;
            background-color: rgba(59, 130, 246, 0.1) !important;
            color: #3b82f6 !important;
        }}

        /* --- BUTTONS --- */
        .stButton>button {{
            width: 100%;
            background-color: {INPUT_BG} !important;
            color: {TEXT_COLOR} !important;
            border: 1px solid var(--glass-border) !important;
            border-radius: 8px !important;
            padding: 0.45rem 0.65rem !important;
            font-weight: 500 !important;
            font-size: 0.85rem !important;
            transition: all 0.2s ease !important;
            margin-bottom: 0.25rem !important;
            text-align: left !important;
        }}

        /* Highlight buttons when hovered */
        .stButton>button:hover {{
            background-color: rgba(59, 130, 246, 0.15) !important;
            color: #60a5fa !important;
            border-color: #3b82f6 !important;
            transform: translateX(4px) !important;
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2) !important;
        }}
        
        /* Active page button styling - applied via inline styles in app.py */
        .stButton>button:active {{
            background-color: rgba(59, 130, 246, 0.2) !important;
            border-color: #3b82f6 !important;
        }}
        
        [data-testid="stSidebar"] .stButton {{
            margin-bottom: 0.2rem !important;
        }}
        
        [data-testid="stSidebar"] .stButton>button {{
            justify-content: flex-start !important;
            gap: 0.35rem !important;
            font-size: 0.8rem !important;
        }}
        
        [data-testid="stSidebar"] .stButton>button:last-child {{
            margin-top: 0.25rem !important;
            border-color: rgba(239, 68, 68, 0.3) !important;
        }}
        
        [data-testid="stSidebar"] .stButton>button:last-child:hover {{
            background-color: rgba(239, 68, 68, 0.1) !important;
            border-color: rgba(239, 68, 68, 0.5) !important;
            color: #f87171 !important;
        }}
        
        [data-testid="stSidebar"] .stAlert {{
            padding: 0.4rem 0.6rem !important;
            border-radius: 6px !important;
            margin: 0.25rem 0 !important;
            font-size: 0.78rem !important;
        }}

        /* Styling for the Delete (Trash) button in history */
        div[data-testid="column"] .stButton > button:has(div:contains("🗑️")),
        div[data-testid="column"] .stButton > button:contains("🗑️") {{
            border-color: rgba(239, 68, 68, 0.2) !important;
            color: rgba(239, 68, 68, 0.6) !important;
            padding: 0.45rem 0 !important;
            text-align: center !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }}

        div[data-testid="column"] .stButton > button:has(div:contains("🗑️")):hover,
        div[data-testid="column"] .stButton > button:contains("🗑️"):hover {{
            background-color: rgba(239, 68, 68, 0.1) !important;
            border-color: rgba(239, 68, 68, 0.8) !important;
            color: #ef4444 !important;
            transform: scale(1.05) !important;
        }}

        /* --- INPUT FIELDS (Where you type) --- */
        .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input {{
            background-color: {INPUT_BG} !important;
            border: 1px solid var(--glass-border) !important;
            color: {TEXT_COLOR} !important;
            border-radius: 8px !important;
        }}

        /* Specifically style the chat box at the bottom */
        [data-testid="stChatInput"] textarea {{
            background-color: {INPUT_BG} !important;
            color: {TEXT_COLOR} !important;
            border: 1px solid var(--glass-border) !important;
        }}

        /* --- TABLES & DATA GRIDS --- */
        div[data-testid="stDataFrame"], div[data-testid="stTable"], .stTable {{
            background-color: {CARD_BG} !important;
            border-radius: 12px;
            border: 1px solid var(--glass-border) !important;
            overflow: hidden;
        }}
        
        .stTable td, .stTable th {{
            color: {TEXT_COLOR} !important;
        }}
        
        /* Style the table headers (top row) */
        thead tr th {{
            background-color: {SIDEBAR_BG} !important;
            color: {SECONDARY_TEXT} !important;
            font-weight: 600 !important;
        }}

        /* --- TABS & FORMS --- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
            background-color: transparent;
        }}
        
        /* Individual tab style */
        .stTabs [data-baseweb="tab"] {{
            height: 40px;
            border-radius: 8px 8px 0 0;
            border: 1px solid var(--glass-border);
            background-color: {SIDEBAR_BG} !important;
            color: {SECONDARY_TEXT} !important;
        }}
        
        /* Style for the currently active tab */
        .stTabs [aria-selected="true"] {{
            background-color: {CARD_BG} !important;
            border-bottom: 2px solid #3b82f6 !important;
            color: {METRIC_VALUE} !important;
        }}
        
        /* Main grouping box for settings and filters */
        div[data-testid="stForm"] {{
            border: 1px solid var(--glass-border) !important;
            background-color: {CARD_BG} !important;
            border-radius: 12px;
            padding: 2rem;
        }}

        /* --- LAYOUT FIXES --- */
        /* Enough top padding so the main heading (e.g. Lyzr AI Chat) is fully visible and not clipped */
        .block-container {{
            padding-top: 2rem !important;
            padding-bottom: 0rem !important;
        }}
        /* Ensure first heading in main area is not cut off */
        .block-container h3 {{
            padding-top: 0.25rem !important;
            margin-top: 0 !important;
            overflow: visible !important;
        }}

        /* Center the login screen header */
        .login-header-section {{
            text-align: center;
            margin-top: 10px;
            margin-bottom: 1.5rem;
        }}
        
        /* --- SIDEBAR SCROLLBAR --- */
        /* Make the scrollbar thin and sleek so it doesn't look clunky */
        [data-testid="stSidebar"] {{
            overflow-y: auto !important;
        }}
        [data-testid="stSidebar"]::-webkit-scrollbar {{
            width: 6px;
            background: transparent;
        }}
        [data-testid="stSidebar"]::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }}
        [data-testid="stSidebar"]:hover::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.2);
        }}
        
        /* Smooth scrolling */
        [data-testid="stSidebar"] {{
            scroll-behavior: smooth;
        }}
        </style>
    """,
        unsafe_allow_html=True,
    )


def get_logo_base64():
    """Simple way to get the company logo for reuse in other files."""
    return get_img_with_href(LOGO_PATH)
