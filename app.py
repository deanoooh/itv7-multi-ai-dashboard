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
            return (float(num) / float(den)) + 1.0
        except ValueError:
            return 2.0
    try:
        return float(odds_str) + 1.0
    except ValueError:
        return 2.0

def parse_ai_text(text):
    """
    Parses input blocks. Handles both single-runner lines:
      '13:35 Doncaster - 1 Big Cigar (4/1)'
    and multi-tier single-line outputs:
      '13:35 Doncaster | Primary: Big Cigar (4/1) | Secondary: Bulletsnap (6/5) | Chaos: Mind Those Steps (4/1)'
    """
    races = []
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    
    header_keywords = ['going', 'runners', 'e/w', 'odds', 'places', 'distance', 'class', 'handicap', 'standard']
    
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in header_keywords) and not re.search(r'\(([\d/]+\vert{}evs)\)', line_lower):
            continue

        time_match = re.search(r'(\d{1,2}:\d{2})\s*([A-Za-z\s]+)?', line)
        if time_match:
            r_time = time_match.group(1)
            course = time_match.group(2).strip() if time_match.group(2) else "Unknown"
            course = re.sub(r'[-–|—].*', '', course).strip()
            
            # Check for multi-tier line (Primary/Secondary/Chaos)
            if 'primary:' in line_lower:
                p_match = re.search(r'primary:\s*([^|(]+)\s*\(([\d/]+\vert{}evs)\)', line, re.IGNORECASE)
                s_match = re.search(r'secondary:\s*([^|(]+)\s*\(([\d/]+\vert{}evs)\)', line, re.IGNORECASE)
                c_match = re.search(r'chaos:\s*([^|(]+)\s*\(([\d/]+\vert{}evs)\)', line, re.IGNORECASE)
                
                p_runner = p_match.group(1).strip() if p_match else "N/A"
                p_odds = p_match.group(2) if p_match else "2/1"
                
                s_runner = s_match.group(1).strip() if s_match else "N/A"
                s_odds = s_match.group(2) if s_match else "2/1"
                
                c_runner = c_match.group(1).strip() if c_match else "N/A"
                c_odds = c_match.group(2) if c_match else "2/1"
                
                races.append({
                    "time": r_time,
                    "course": course,
                    "runner": p_runner,  # Default Primary runner for consensus matching
                    "odds_str": p_odds,
                    "odds_dec": parse_odds_to_decimal(p_odds),
                    "primary": f"{p_runner} ({p_odds})",
                    "secondary": f"{s_runner} ({s_odds})",
                    "chaos": f"{c_runner} ({c_odds})"
                })
            else:
                # Standard single-runner line
                odds_match = re.search(r'\(([\d/]+\vert{}evs)\)', line, re.IGNORECASE)
                odds_str = odds_match.group(1) if odds_match else "2/1"
                
                cleaned = re.sub(r'^\d{1,2}:\d{2}\s*[-–—]?\s*', '', line)
                cleaned = re.sub(r'\((.*?)\)', '', cleaned)
                cleaned = re.sub(r'^\d+\s+', '', cleaned).strip()
                cleaned = re.sub(r'^[-–—]\s*', '', cleaned).strip()
                
                if cleaned and not any(kw in cleaned.lower() for kw in ['going:', 'runners:', 'places:']):
                    races.append({
                        "time": r_time,
                        "course": course,
                        "runner": cleaned,
                        "odds_str": odds_str,
                        "odds_dec": parse_odds_to_decimal(odds_str),
                        "primary": f"{cleaned} ({odds_str})",
                        "secondary": "-",
                        "chaos": "-"
                    })
    return races

def calculate_consensus(ai_list):
    """Aggregates picks across AIs,
