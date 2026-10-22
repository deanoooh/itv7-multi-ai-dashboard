import re
import pandas as pd
import numpy as np
import streamlit as st

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Multi-AI Racing Consensus & Audit Engine",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for High Contrast & Modern UI
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .metric-card {
        background-color: #1e222d;
        border: 1px solid #2d313e;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
    
    /* HIGH CONTRAST BLACK TEXT FOR PASTE BOXES */
    .stTextArea textarea {
        font-family: 'Courier New', Courier, monospace !important;
        font-size: 0.9rem !important;
        color: #000000 !important;             /* Pure Black Text */
        background-color: #f8f9fa !important;  /* Light Off-White Background */
        font-weight: 600 !important;          /* Bold/Semi-bold readability */
        border: 2px solid #4a5568 !important;   /* Defined Border */
    }
    
    /* High contrast labels above text boxes */
    .stTextArea label {
        color: #ffffff !important;
        font-size: 1rem !important;
        font-weight: bold !important;
    }

    .badge-unanimous {
        background-color: #1b5e20;
        color: #81c784;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-majority {
        background-color: #0d47a1;
        color: #64b5f6;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-split {
        background-color: #e65100;
        color: #ffb74d;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DEFAULT DEMO DATA (FOR ONE-CLICK TESTING)
# ==========================================
DEMO_AI1 = """17:15 Wolverhampton - 6 Lorna B (28/1)
17:45 Wolverhampton - 1 Asmen Warrior (17/2)
18:15 Wolverhampton - 1 Dark Cloud Rising (5/1)
18:45 Wolverhampton - 4 A Lott Of Kane (11/4)
19:15 Wolverhampton - 2 Sea The Light (14/1)
19:45 Wolverhampton - 3 Lethimfly (4/1)
20:15 Wolverhampton - 2 Call Margot (11/2)"""

DEMO_AI2 = """17:15 Wolverhampton - 8 Star Of Mali (4/1)
17:45 Wolverhampton - 1 Asmen Warrior (17/2)
18:15 Wolverhampton - 8 Kind Touch (10/3)
18:45 Wolverhampton - 5 Macarone (11/1)
19:15 Wolverhampton - 9 The Anthony Gover (9/2)
19:45 Wolverhampton - 5 Invincible Crown (3/1)
20:15 Wolverhampton - 3 Got The Booty (8/11)"""

DEMO_AI3 = """17:15 Wolverhampton - 9 Powder Monkey (2/1)
17:45 Wolverhampton - 2 Meydaan (15/8)
18:15 Wolverhampton - 1 Dark Cloud Rising (5/1)
18:45 Wolverhampton - 5 Macarone (11/1)
19:15 Wolverhampton - 2 Sea The Light (14/1)
19:45 Wolverhampton - 3 Lethimfly (4/1)
20:15 Wolverhampton - 2 Call Margot (11/2)"""

DEMO_AI4 = """17:15 Wolverhampton - 9 Powder Monkey (2/1)
17:45 Wolverhampton - 2 Meydaan (15/8)
18:15 Wolverhampton - 8 Kind Touch (10/3)
18:45 Wolverhampton - 4 A Lott Of Kane (11/4)
19:15 Wolverhampton - 8 Albertini Star (3/1)
19:45 Wolverhampton - 4 Little Jaybee (3/1)
20:15 Wolverhampton - 3 Got The Booty (8/11)"""

DEMO_RESULTS = """17:15 Wolverhampton - 1st: 6 Lorna B (28/1), 2nd: 8 Star Of Mali (4/1), 3rd: 12 Chantelle (4/1)
17:45 Wolverhampton - 1st: 1 Asmen Warrior (17/2), 2nd: 5 Al Zanati (15/8)
18:15 Wolverhampton - 1st: 1 Dark Cloud Rising (5/1), 2nd: 8 Kind Touch (10/3), 3rd: 6 Silent Strike (14/1), 4th: 2 Knebworth (6/1)
18:45 Wolverhampton - 1st: 5 Macarone (11/1), 2nd: 4 A Lott Of Kane (11/4), 3rd: 7 My Mate Kev (9/2), 4th: 2 Two And Two (9/1)
19:15 Wolverhampton - 1st: 2 Sea The Light (14/1), 2nd: 9 The Anthony Gover (9/2), 3rd: 1 Moonjid (6/1)
19:45 Wolverhampton - 1st: 3 Lethimfly (4/1), 2nd: 5 Invincible Crown (3/1), 3rd: 1 Alkuwarrior (14/1)
20:15 Wolverhampton - 1st: 2 Call Margot (11/2), 2nd: 3 Got The Booty (8/11)"""

# ==========================================
# HELPER FUNCTIONS & PARSERS
# ==========================================
def parse_odds_to_decimal(odds_str):
    """Converts odds string (e.g. '11/4', '2/1', '8/11', 'Evs') to decimal odds."""
    if not odds_str:
        return 2.0
    odds_str = odds_str.strip().lower()
    if odds_str in ['evs', 'eve', 'even', 'evens']:
        return 2.0
    if '/' in odds_str:
        try:
            num, den = odds_str.split('/')
            return (float(num) / float(den)) +
