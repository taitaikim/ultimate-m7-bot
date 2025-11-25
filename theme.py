import streamlit as st
from datetime import datetime
import base64
import os

def get_base64_image(image_path):
    """Get base64 encoding of an image"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return None

def apply_premium_theme():
    """Apply premium Wall Street-style dark theme"""
    
    # Load background image
    bg_path = os.path.join("assets", "background.png")
    bg_base64 = get_base64_image(bg_path)
    
    bg_style = f"""
        background-image: linear-gradient(rgba(15, 20, 25, 0.85), rgba(26, 31, 46, 0.95)), url("data:image/png;base64,{bg_base64}");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
    """ if bg_base64 else "background: linear-gradient(135deg, #0F1419 0%, #1A1F2E 100%);"

    st.markdown(f"""
    <style>
    /* ============================================
       1. GLOBAL STYLES
       ============================================ */
    
    /* Font imports */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    /* App background */
    .stApp {{
        {bg_style}
        color: #E5E7EB;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    
    /* Main container */
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }}
    
    /* ============================================
       2. TYPOGRAPHY
       ============================================ */
    
    h1 {{
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 2.5rem;
        background: linear-gradient(135deg, #FFB800 0%, #FF8C00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
    }}
    
    h2 {{
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 1.75rem;
        color: #FFFFFF;
        margin-top: 2rem;
        margin-bottom: 1rem;
        letter-spacing: -0.01em;
        text-shadow: 0 2px 4px rgba(0,0,0,0.8);
    }}
    
    h3 {{
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1.25rem;
        color: #FFFFFF;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.8);
    }}
    
    /* ============================================
       3. METRIC CARDS
       ============================================ */
    
    [data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        color: #FFFFFF;
        text-shadow: 0 0 10px rgba(255, 184, 0, 0.3);
    }}
    
    [data-testid="stMetricLabel"] {{
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        font-weight: 500;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    
    [data-testid="stMetricDelta"] {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 1rem;
        font-weight: 600;
    }}
    
    [data-testid="metric-container"] {{
        background: rgba(28, 30, 34, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    
    [data-testid="metric-container"]:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4), 
                    0 0 0 1px rgba(255, 184, 0, 0.3);
        background: rgba(28, 30, 34, 0.8);
    }}
    
    /* ============================================
       4. DATA TABLES
       ============================================ */
    
    [data-testid="stDataFrame"] {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.875rem;
    }}
    
    [data-testid="stDataFrame"] thead tr th {{
        background: linear-gradient(135deg, #252930 0%, #2D3139 100%) !important;
        color: #FFB800 !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.75rem !important;
        border-bottom: 2px solid rgba(255, 184, 0, 0.3) !important;
    }}
    
    [data-testid="stDataFrame"] tbody tr {{
        background: rgba(28, 30, 34, 0.4) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
        transition: background 0.2s ease;
    }}
    
    [data-testid="stDataFrame"] tbody tr:hover {{
        background: rgba(255, 184, 0, 0.1) !important;
    }}
    
    /* ============================================
       5. TABS
       ============================================ */
    
    [data-baseweb="tab-list"] {{
        gap: 1rem;
        background: transparent;
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
    }}
    
    [data-baseweb="tab"] {{
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1rem;
        color: #9CA3AF !important;
        background: transparent !important;
        border: none !important;
        padding: 1rem 1.5rem;
        transition: all 0.3s ease;
    }}
    
    [data-baseweb="tab"]:hover {{
        color: #FFB800 !important;
        background: rgba(255, 184, 0, 0.05) !important;
    }}
    
    [aria-selected="true"] {{
        color: #FFB800 !important;
        border-bottom: 3px solid #FFB800 !important;
    }}
    
    /* ============================================
       6. BUTTONS
       ============================================ */
    
    .stButton > button {{
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.875rem;
        color: #0F1419;
        background: linear-gradient(135deg, #FFB800 0%, #FF8C00 100%);
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        box-shadow: 0 4px 6px rgba(255, 184, 0, 0.3);
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(255, 184, 0, 0.4);
        background: linear-gradient(135deg, #FFC933 0%, #FFA500 100%);
    }}
    
    .stButton > button:active {{
        transform: translateY(0);
    }}
    
    /* ============================================
       7. INPUT FIELDS
       ============================================ */
    
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {{
        font-family: 'Inter', sans-serif;
        background: rgba(37, 41, 48, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px;
        color: #FFFFFF !important;
        padding: 0.75rem;
        transition: all 0.3s ease;
        backdrop-filter: blur(4px);
    }}
    
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {{
        border-color: #FFB800 !important;
        box-shadow: 0 0 0 3px rgba(255, 184, 0, 0.1) !important;
        background: rgba(37, 41, 48, 1) !important;
    }}
    
    /* ============================================
       8. SIDEBAR
       ============================================ */
    
    [data-testid="stSidebar"] {{
        background: rgba(28, 30, 34, 0.95);
        border-right: 1px solid rgba(255, 184, 0, 0.1);
        backdrop-filter: blur(10px);
    }}
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {{
        color: #FFB800;
    }}
    
    /* ============================================
       9. ALERTS
       ============================================ */
    
    .stSuccess {{
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%) !important;
        border-left: 4px solid #10B981 !important;
        color: #10B981 !important;
        padding: 1rem;
        border-radius: 8px;
        backdrop-filter: blur(4px);
    }}
    
    .stError {{
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%) !important;
        border-left: 4px solid #EF4444 !important;
        color: #EF4444 !important;
        padding: 1rem;
        border-radius: 8px;
        backdrop-filter: blur(4px);
    }}
    
    .stWarning {{
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(245, 158, 11, 0.05) 100%) !important;
        border-left: 4px solid #F59E0B !important;
        color: #F59E0B !important;
        padding: 1rem;
        border-radius: 8px;
        backdrop-filter: blur(4px);
    }}
    
    .stInfo {{
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%) !important;
        border-left: 4px solid #3B82F6 !important;
        color: #3B82F6 !important;
        padding: 1rem;
        border-radius: 8px;
        backdrop-filter: blur(4px);
    }}
    
    /* ============================================
       10. SCROLLBAR
       ============================================ */
    
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: #1C1E22;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: linear-gradient(135deg, #FFB800 0%, #FF8C00 100%);
        border-radius: 5px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: linear-gradient(135deg, #FFC933 0%, #FFA500 100%);
    }}
    
    /* ============================================
       11. ANIMATIONS
       ============================================ */
    
    @keyframes fadeIn {{
        from {{
            opacity: 0;
            transform: translateY(10px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    
    @keyframes float {{
        0% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-10px); }}
        100% {{ transform: translateY(0px); }}
    }}
    
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(255, 184, 0, 0.4); }}
        70% {{ box-shadow: 0 0 0 10px rgba(255, 184, 0, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(255, 184, 0, 0); }}
    }}
    
    .main .block-container > div {{
        animation: fadeIn 0.5s ease-out;
    }}
    
        background: rgba(255, 184, 0, 0.1) !important;
    }}
    
    /* ============================================
    /* ============================================
       4. COMPONENT OVERRIDES
       ============================================ */
    
    /* Alerts (st.info, st.success, etc.) */
    div[data-testid="stAlert"] {{
        background-color: rgba(28, 30, 34, 0.8) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #E5E7EB !important;
    }}
    div[data-testid="stAlert"] p {{
        color: #E5E7EB !important;
    }}

    /* Global Widget Labels */
    /* Global Widget Labels */
    div[data-testid="stWidgetLabel"] p,
    div[data-testid="stWidgetLabel"] label,
    label[data-baseweb="checkbox"] div,
    .stSelectbox label,
    .stNumberInput label,
    .stSlider label {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }}
    
    /* Inputs (Selectbox, NumberInput, TextInput) */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"] {{
        background-color: rgba(28, 30, 34, 0.5) !important;
        color: #E5E7EB !important;
        border-color: rgba(255, 255, 255, 0.1) !important;
    }}
    
    /* Input Text Color */
    input {{
        color: #E5E7EB !important;
    }}
    
    /* Dropdown Menu - Comprehensive Targeting */
    ul[data-baseweb="menu"],
    div[data-baseweb="popover"] ul,
    ul[role="listbox"],
    div[role="listbox"] {{
        background-color: #1C1E22 !important;
        border: 1px solid rgba(255, 184, 0, 0.3) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5) !important;
    }}
    
    /* Popover container */
    div[data-baseweb="popover"] {{
        background-color: transparent !important;
    }}
    
    /* Menu items */
    li[data-baseweb="menu-item"],
    li[role="option"],
    div[role="option"] {{
        color: #E5E7EB !important;
        background-color: #1C1E22 !important;
    }}
    
    /* Menu items hover */
    li[data-baseweb="menu-item"]:hover,
    li[role="option"]:hover,
    div[role="option"]:hover {{
        background-color: rgba(255, 184, 0, 0.15) !important;
        color: #FFB800 !important;
    }}
    
    /* Selected dropdown item */
    li[data-baseweb="menu-item"][aria-selected="true"],
    li[role="option"][aria-selected="true"],
    div[role="option"][aria-selected="true"] {{
        background-color: rgba(255, 184, 0, 0.1) !important;
        color: #FFB800 !important;
        font-weight: 600;
    }}
    
    /* Sliders */
    div[data-baseweb="slider"] div[role="slider"] {{
        background-color: #FFB800 !important;
        box-shadow: 0 0 10px rgba(255, 184, 0, 0.5) !important;
    }}
    div[data-baseweb="slider"] div[data-testid="stTickBar"] > div {{
        background-color: rgba(255, 255, 255, 0.2) !important;
    }}
    /* Hide top slider value (ThumbValue) to prevent duplicates */
    div[data-baseweb="slider"] div[data-testid="stThumbValue"] {{
        display: none !important;
    }}
    
    /* Force bottom slider labels (min/max/ticks) to be visible and white */
    div[data-baseweb="slider"] div[data-testid="stTickBar"] div,
    div[data-baseweb="slider"] div[data-testid="stTickBar"] p {{
        color: #FFFFFF !important;
        visibility: visible !important;
    }}

    /* Expander */
    .streamlit-expanderHeader,
    div[data-testid="stExpander"] details > summary {{
        background-color: transparent !important;
        color: #E5E7EB !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }}
    
    div[data-testid="stExpander"] details > summary:hover {{
        color: #FFB800 !important;
        border-color: #FFB800 !important;
    }}
    
    div[data-testid="stExpander"] {{
        background-color: transparent !important;
        color: #E5E7EB !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: #FFB800 !important;
        border-color: #FFB800 !important;
    }}
    
    /* ============================================
       5. TABS
       ============================================ */
    
    [data-baseweb="tab-list"] {{
        gap: 1rem;
        background: transparent;
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
    }}
    
    [data-baseweb="tab"] {{
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1rem;
        color: #9CA3AF !important;
        background: transparent !important;
        border: none !important;
        padding: 1rem 1.5rem;
        transition: all 0.3s ease;
    }}
    
    [data-baseweb="tab"]:hover {{
        color: #FFB800 !important;
        background: rgba(255, 184, 0, 0.05) !important;
    }}
    
    [aria-selected="true"] {{
        color: #FFB800 !important;
        border-bottom: 3px solid #FFB800 !important;
    }}
    
    /* ============================================
       6. BUTTONS
       ============================================ */
    
    .stButton > button {{
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.875rem;
        color: #0F1419;
        background: linear-gradient(135deg, #FFB800 0%, #FF8C00 100%);
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        box-shadow: 0 4px 6px rgba(255, 184, 0, 0.3);
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(255, 184, 0, 0.4);
        background: linear-gradient(135deg, #FFC933 0%, #FFA500 100%);
    }}
    
    .stButton > button:active {{
        transform: translateY(0);
    }}
    
    /* ============================================
       7. INPUT FIELDS
       ============================================ */
    
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {{
        font-family: 'Inter', sans-serif;
        background: rgba(37, 41, 48, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px;
        color: #FFFFFF !important;
        padding: 0.75rem;
        transition: all 0.3s ease;
        backdrop-filter: blur(4px);
    }}
    
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {{
        border-color: #FFB800 !important;
        box-shadow: 0 0 0 3px rgba(255, 184, 0, 0.1) !important;
        background: rgba(37, 41, 48, 1) !important;
    }}
    
    /* ============================================
       8. SIDEBAR
       ============================================ */
    
    [data-testid="stSidebar"] {{
        background: rgba(28, 30, 34, 0.95);
        border-right: 1px solid rgba(255, 184, 0, 0.1);
        backdrop-filter: blur(10px);
    }}
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {{
        color: #FFB800;
    }}
    
    /* ============================================
       9. ALERTS
       ============================================ */
    
    .stSuccess {{
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%) !important;
        border-left: 4px solid #10B981 !important;
        color: #10B981 !important;
        padding: 1rem;
        border-radius: 8px;
        backdrop-filter: blur(4px);
    }}
    
    .stError {{
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%) !important;
        border-left: 4px solid #EF4444 !important;
        color: #EF4444 !important;
        padding: 1rem;
        border-radius: 8px;
        backdrop-filter: blur(4px);
    }}
    
    .stWarning {{
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(245, 158, 11, 0.05) 100%) !important;
        border-left: 4px solid #F59E0B !important;
        color: #F59E0B !important;
        padding: 1rem;
        border-radius: 8px;
        backdrop-filter: blur(4px);
    }}
    
    .stInfo {{
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%) !important;
        border-left: 4px solid #3B82F6 !important;
        color: #3B82F6 !important;
        padding: 1rem;
        border-radius: 8px;
        backdrop-filter: blur(4px);
    }}
    
    /* ============================================
       10. SCROLLBAR
       ============================================ */
    
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: #1C1E22;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: linear-gradient(135deg, #FFB800 0%, #FF8C00 100%);
        border-radius: 5px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: linear-gradient(135deg, #FFC933 0%, #FFA500 100%);
    }}
    
    /* ============================================
       11. ANIMATIONS
       ============================================ */
    
    @keyframes fadeIn {{
        from {{
            opacity: 0;
            transform: translateY(10px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    
    @keyframes float {{
        0% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-10px); }}
        100% {{ transform: translateY(0px); }}
    }}
    
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(255, 184, 0, 0.4); }}
        70% {{ box-shadow: 0 0 0 10px rgba(255, 184, 0, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(255, 184, 0, 0); }}
    }}
    
    .main .block-container > div {{
        animation: fadeIn 0.5s ease-out;
    }}
    
    .floating-icon {{
        animation: float 3s ease-in-out infinite;
    }}
    
    /* ============================================
       12. LOADING SPINNER
       ============================================ */
    
    .stSpinner > div {{
        border-top-color: #FFB800 !important;
    }}
    
    /* ============================================
       13. EXPANDABLE SECTIONS
       ============================================ */
    
    [data-testid="stExpander"] {{
        background: rgba(28, 30, 34, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        backdrop-filter: blur(4px);
    }}
    
    [data-testid="stExpander"] summary {{
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: #FFB800;
    }}
    
    /* ============================================
       14. RESPONSIVE
       ============================================ */
    
    /* ============================================
       15. HEADER & DECORATION
       ============================================ */
    
    /* Hide the default Streamlit header decoration */
    header[data-testid="stHeader"] {{
        background: transparent !important;
        visibility: hidden !important;
    }}
    
    /* Adjust top padding since header is hidden */
    .main .block-container {{
        padding-top: 1rem !important;
    }}
    
    /* ============================================
       16. SIDEBAR TEXT VISIBILITY
       ============================================ */
       
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label {{
        color: #E5E7EB !important;
    }}
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {{
        color: #FFB800 !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }}
    
    </style>
    """, unsafe_allow_html=True)


def render_premium_header():
    """Render premium header with logo and timestamp"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Load rocket icon
    icon_path = os.path.join("assets", "rocket_icon.png")
    icon_base64 = get_base64_image(icon_path)
    
    icon_html = f'<img src="data:image/png;base64,{icon_base64}" style="width: 80px; height: auto;" class="floating-icon">' if icon_base64 else '<div style="font-size: 3rem;">🚀</div>'
    
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 2rem;
        margin-bottom: 2rem;
        padding: 2rem;
        background: linear-gradient(135deg, rgba(28, 30, 34, 0.8) 0%, rgba(37, 41, 48, 0.9) 100%);
        backdrop-filter: blur(20px);
        border-radius: 24px;
        border: 1px solid rgba(255, 184, 0, 0.2);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3), 
                    0 0 0 1px rgba(255, 184, 0, 0.1);
    ">
        <div style="
            filter: drop-shadow(0 0 20px rgba(255, 184, 0, 0.3));
        ">
            {icon_html}
        </div>
        <div style="flex: 1;">
            <h1 style="
                margin: 0;
                font-size: 2.5rem;
                background: linear-gradient(135deg, #FFB800 0%, #FF8C00 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
            ">AntiGravity M7 & ETF</h1>
            <p style="
                margin: 0.5rem 0 0 0;
                color: #9CA3AF;
                font-size: 1rem;
                font-family: 'Inter', sans-serif;
                font-weight: 500;
            ">Professional Trading Dashboard · Powered by Bloomberg-style Analytics</p>
        </div>
        <div style="
            text-align: right;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.875rem;
            color: #6B7280;
            background: rgba(0,0,0,0.2);
            padding: 0.75rem 1.25rem;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.05);
        ">
            <div style="color: #FFB800; font-weight: 600; margin-bottom: 0.25rem;">📊 Live Market Data</div>
            <div>{current_time}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_premium_metric(label, value, delta=None, icon="📊"):
    """Render a premium-styled metric card with glassmorphism effect"""
    delta_color = "#10B981" if delta and delta >= 0 else "#EF4444"
    delta_symbol = "▲" if delta and delta >= 0 else "▼"
    
    # Always render delta div to maintain consistent height
    if delta is not None:
        delta_html = f'<div style="font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem; color: {delta_color}; margin-top: 0.25rem; font-weight: 600; text-align: center;">{delta_symbol} {delta:+.2f}%</div>'
    else:
        # Invisible placeholder to maintain height
        delta_html = '<div style="font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem; margin-top: 0.25rem; font-weight: 600; visibility: hidden; text-align: center;">▲ +0.00%</div>'
    
    html_content = f"""
    <div style="background: linear-gradient(135deg, rgba(28, 30, 34, 0.9) 0%, rgba(37, 41, 48, 0.9) 100%); backdrop-filter: blur(10px); border: 1px solid rgba(255, 184, 0, 0.3); border-radius: 12px; padding: 1rem; height: 130px; display: flex; flex-direction: column; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3), 0 0 20px rgba(255, 184, 0, 0.15); transition: all 0.3s ease;">
        <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem; margin-bottom: 0.4rem; flex-shrink: 0;">
            <div style="font-size: 1.1rem; filter: drop-shadow(0 0 8px rgba(255, 184, 0, 0.4));">{icon}</div>
            <div style="font-family: 'Inter', sans-serif; font-size: 0.65rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.08em;">{label}</div>
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: #FFFFFF; text-shadow: 0 0 20px rgba(255, 184, 0, 0.3); flex-grow: 1; word-wrap: break-word; line-height: 1.2; text-align: center; display: flex; align-items: center; justify-content: center;">{value}</div>
        {delta_html}
    </div>
    """
    
    st.markdown(html_content, unsafe_allow_html=True)


def render_premium_table(df, highlight_columns=None):
    """Apply premium styling to DataFrame and return HTML"""
    # Custom CSS for the table
    table_style = """
<style>
.premium-table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; color: #E5E7EB; background: rgba(28, 30, 34, 0.5); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); margin-bottom: 1rem; }
.premium-table thead tr { background: linear-gradient(135deg, #252930 0%, #2D3139 100%); border-bottom: 2px solid rgba(255, 184, 0, 0.3); }
.premium-table th { padding: 1rem; text-align: left; font-weight: 600; color: #FFB800; text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.75rem; }
.premium-table td { padding: 0.75rem 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); vertical-align: middle; }
.premium-table tbody tr:hover { background: rgba(255, 184, 0, 0.05); }
.rsi-bar-bg { width: 100px; height: 6px; background: rgba(255, 255, 255, 0.1); border-radius: 3px; overflow: hidden; display: inline-block; vertical-align: middle; margin-right: 8px; }
.rsi-bar-fill { height: 100%; border-radius: 3px; }
</style>
"""
    
    # Create a copy to avoid modifying the original dataframe
    display_df = df.copy()
    
    # Format RSI column with progress bar if it exists
    if 'RSI' in display_df.columns:
        def format_rsi(val):
            try:
                rsi_val = float(val)
                color = "#EF4444" if rsi_val > 70 else "#10B981" if rsi_val < 30 else "#3B82F6"
                return f'<div class="rsi-bar-bg"><div class="rsi-bar-fill" style="width: {rsi_val}%; background-color: {color};"></div></div>{rsi_val:.1f}'
            except:
                return val
        display_df['RSI'] = display_df['RSI'].apply(format_rsi)

    # Format other numeric columns (simple formatting)
    for col in display_df.columns:
        if col != 'RSI':
            display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}" if isinstance(x, (float, int)) and not str(x).endswith('%') else x)

    # Convert DataFrame to HTML with custom classes
    html = display_df.to_html(classes="premium-table", index=False, escape=False)
    
    # Apply conditional formatting logic for text colors (Red/Green)
    # Since we are using escape=False, we can inject span tags for colors
    def colorize_text(html_str):
        # Simple regex to find negative numbers and color them red, positive green
        # This is a heuristic; for perfect accuracy we should have formatted in the dataframe step.
        # But let's rely on the previous logic of highlighting specific columns if needed.
        pass
    
    # Better approach: Pre-format the dataframe content with span tags for colors
    # We already converted to HTML, so let's just return the styled HTML
    
    return table_style + html
