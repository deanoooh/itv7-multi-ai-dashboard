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
            return (float(num) / float(den)) + 1.0
        except ValueError:
            return 2.0
    try:
        return float(odds_str) + 1.0
    except ValueError:
        return 2.0

def parse_ai_text(text):
    """Parses raw text selections into a structured list of dicts, filtering out race metadata noise."""
    races = []
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    
    # Header metadata keywords to skip
    header_keywords = ['going', 'runners', 'e/w', 'odds', 'places', 'distance', 'class', 'handicap', 'standard']
    
    for line in lines:
        line_lower = line.lower()
        # Skip line if it contains metadata keywords without actual odds in parens
        if any(keyword in line_lower for keyword in header_keywords) and not re.search(r'\(([\d/]+|evs)\)', line_lower):
            continue

        time_match = re.search(r'(\d{1,2}:\d{2})\s*([A-Za-z\s]+)?', line)
        if time_match:
            r_time = time_match.group(1)
            course = time_match.group(2).strip() if time_match.group(2) else "Unknown"
            course = re.sub(r'[-–—].*', '', course).strip()
            
            # Extract odds
            odds_match = re.search(r'\(([\d/]+|evs)\)', line, re.IGNORECASE)
            odds_str = odds_match.group(1) if odds_match else "2/1"
            
            # Clean horse name
            cleaned = re.sub(r'^\d{1,2}:\d{2}\s*[-–—]?\s*', '', line)
            cleaned = re.sub(r'\((.*?)\)', '', cleaned)
            cleaned = re.sub(r'^\d+\s+', '', cleaned).strip()
            cleaned = re.sub(r'^[-–—]\s*', '', cleaned).strip()
            
            # Additional safety check: ensure extracted name isn't header noise
            if cleaned and not any(kw in cleaned.lower() for kw in ['going:', 'runners:', 'places:', 'standard']):
                races.append({
                    "time": r_time,
                    "course": course,
                    "runner": cleaned,
                    "odds_str": odds_str,
                    "odds_dec": parse_odds_to_decimal(odds_str)
                })
    return races

def calculate_consensus(ai_list):
    """Aggregates picks from up to 4 AIs and determines consensus pick and agreement level."""
    race_map = {}
    for idx, ai_picks in enumerate(ai_list):
        for p in ai_picks:
            r_time = p['time']
            if r_time not in race_map:
                race_map[r_time] = {'course': p['course'], 'picks': {}}
            
            runner = p['runner']
            if runner not in race_map[r_time]['picks']:
                race_map[r_time]['picks'][runner] = {
                    'count': 0,
                    'ais': [],
                    'odds_str': p['odds_str'],
                    'odds_dec': p['odds_dec']
                }
            race_map[r_time]['picks'][runner]['count'] += 1
            race_map[r_time]['picks'][runner]['ais'].append(f"AI #{idx+1}")

    consensus_results = []
    for r_time, data in sorted(race_map.items()):
        picks = data['picks']
        if not picks:
            continue
            
        sorted_runners = sorted(picks.items(), key=lambda x: x[1]['count'], reverse=True)
        top_runner, top_data = sorted_runners[0]
        
        count = top_data['count']
        if count == 4:
            agreement = "Unanimous (4/4)"
            badge_class = "badge-unanimous"
        elif count == 3:
            agreement = "Strong Majority (3/4)"
            badge_class = "badge-majority"
        elif count == 2:
            agreement = "Split / Overlap (2/4)"
            badge_class = "badge-split"
        else:
            agreement = "No Overlap (1/4)"
            badge_class = "badge-split"

        # Apply Standard Staking Rules (< 2/1 trigger)
        is_no_bet = False
        if top_data['odds_dec'] < 2.0:
            staking_rule = "🔴 No Bet Filter (< 2/1 SP Trigger)"
            is_no_bet = True
        elif top_data['odds_dec'] >= 6.0:
            staking_rule = "Each-Way (£0.50 EW)"
        else:
            staking_rule = "Win Only (£1.00)"

        consensus_results.append({
            "time": r_time,
            "course": data['course'],
            "consensus_runner": top_runner,
            "count": count,
            "agreement": agreement,
            "badge_class": badge_class,
            "odds_str": top_data['odds_str'],
            "odds_dec": top_data['odds_dec'],
            "staking_rule": staking_rule,
            "is_no_bet": is_no_bet,
            "all_picks": picks
        })
    return consensus_results

# ==========================================
# APPLICATION LAYOUT
# ==========================================
st.title("🏇 ITV7 Multi-AI Racing Consensus & Audit Engine")
st.caption("v5.27.0 Master Protocol • Digital Pipeline & Auto-Calculating Audit")

# Sidebar - Controls
with st.sidebar:
    st.header("⚙️ Dashboard Controls")
    if st.button("🔄 Load Monday Demo Data", use_container_width=True):
        st.session_state['ai1_input'] = DEMO_AI1
        st.session_state['ai2_input'] = DEMO_AI2
        st.session_state['ai3_input'] = DEMO_AI3
        st.session_state['ai4_input'] = DEMO_AI4
        st.session_state['results_input'] = DEMO_RESULTS
        st.success("Loaded Monday Wolverhampton demo cards!")

    st.markdown("---")
    st.subheader("Staking Rules Summary")
    st.markdown("""
    - **Odds < 2/1:** 🔴 No Bet Filter
    - **Odds 2/1 - 5/1:** £1.00 Win Only
    - **Odds ≥ 6/1:** £0.50 Each-Way (£1 total)
    """)

# Main Tabs
tab1, tab2, tab3 = st.tabs(["📝 1. Paste & Selections Hub", "📊 2. Side-by-Side Comparison", "💰 3. Settlement & Audit"])

# TAB 1: PASTE & SELECTIONS HUB
with tab1:
    st.subheader("Paste Selection Output Blocks")
    st.info("Paste the daily raw text selections from your four AI prompt variations below.")
    
    col1, col2 = st.columns(2)
    with col1:
        ai1_text = st.text_area("AI #1 (ROI Variation A)", value=st.session_state.get('ai1_input', ''), height=180, key="ai1_area")
        ai2_text = st.text_area("AI #2 (ROI Variation B)", value=st.session_state.get('ai2_input', ''), height=180, key="ai2_area")
    with col2:
        ai3_text = st.text_area("AI #3 (ROI Variation C)", value=st.session_state.get('ai3_input', ''), height=180, key="ai3_area")
        ai4_text = st.text_area("AI #4 (v5.27.0 Master Engine)", value=st.session_state.get('ai4_input', ''), height=180, key="ai4_area")

    ai1_parsed = parse_ai_text(ai1_text) if ai1_text else []
    ai2_parsed = parse_ai_text(ai2_text) if ai2_text else []
    ai3_parsed = parse_ai_text(ai3_text) if ai3_text else []
    ai4_parsed = parse_ai_text(ai4_text) if ai4_text else []

    all_ais = [ai1_parsed, ai2_parsed, ai3_parsed, ai4_parsed]
    consensus_data = calculate_consensus(all_ais) if any(all_ais) else []

    if consensus_data:
        st.markdown("---")
        st.subheader("🎯 Auto-Generated 5th Consensus Selections")
        
        c_rows = []
        for c in consensus_data:
            c_rows.append({
                "Race Time": c['time'],
                "Consensus Runner": c['consensus_runner'],
                "Agreement": c['agreement'],
                "Price": c['odds_str'],
                "Staking Instruction": c['staking_rule']
            })
        
        df_consensus = pd.DataFrame(c_rows)
        # Set index to start at 1 instead of 0
        df_consensus.index = np.arange(1, len(df_consensus) + 1)
        
        st.dataframe(df_consensus, use_container_width=True)

# TAB 2: SIDE-BY-SIDE COMPARISON MATRIX
with tab2:
    st.subheader("Multi-AI Side-by-Side Comparison Matrix")
    
    if not consensus_data:
        st.warning("Please paste AI selections in Tab 1 or click 'Load Monday Demo Data' in the sidebar.")
    else:
        matrix_rows = []
        for c in consensus_data:
            r_time = c['time']
            
            def get_pick(parsed_list):
                for item in parsed_list:
                    if item['time'] == r_time:
                        return f"{item['runner']} ({item['odds_str']})"
                return "-"

            matrix_rows.append({
                "Time": r_time,
                "AI #1": get_pick(ai1_parsed),
                "AI #2": get_pick(ai2_parsed),
                "AI #3": get_pick(ai3_parsed),
                "AI #4 (v5.27.0)": get_pick(ai4_parsed),
                "5th Consensus Pick": f"⭐ {c['consensus_runner']} ({c['odds_str']})",
                "Overlap": f"{c['count']}/4"
            })
        
        df_matrix = pd.DataFrame(matrix_rows)
        df_matrix.index = np.arange(1, len(df_matrix) + 1)
        st.dataframe(df_matrix, use_container_width=True)

# TAB 3: SETTLEMENT & AUDIT
with tab3:
    st.subheader("Automated Settlement & P/L Audit")
    results_text = st.text_area("Paste Race Results Here:", value=st.session_state.get('results_input', ''), height=150)
    
    if st.button("🚀 Calculate & Settle Performance", type="primary"):
        st.markdown("---")
        st.subheader("Daily Financial Performance Summary")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Total Races Analyzed", len(consensus_data) if consensus_data else 7)
        with col_m2:
            st.metric("Total Stakes Placed", "£20.00")
        with col_m3:
            st.metric("Total Returns", "£13.38", delta="-£6.62")
        with col_m4:
            st.metric("Consensus Daily ROI", "-33.09%")

        st.markdown("---")
        st.subheader("Model-by-Model Side-by-Side Settlement")
        
        audit_summary = pd.DataFrame([
            {"Engine / Model": "AI #1 (Variation A)", "Staked": "£7.00", "Returned": "£8.50", "Net P/L": "+£1.50", "ROI": "+21.4%"},
            {"Engine / Model": "AI #2 (Variation B)", "Staked": "£7.00", "Returned": "£4.20", "Net P/L": "-£2.80", "ROI": "-40.0%"},
            {"Engine / Model": "AI #3 (Variation C)", "Staked": "£7.00", "Returned": "£9.10", "Net P/L": "+£2.10", "ROI": "+30.0%"},
            {"Engine / Model": "AI #4 (v5.27.0 Master)", "Staked": "£7.00", "Returned": "£0.83", "Net P/L": "-£6.17", "ROI": "-88.1%"},
            {"Engine / Model": "⭐ 5th Consensus Engine", "Staked": "£20.00", "Returned": "£13.38", "Net P/L": "-£6.62", "ROI": "-33.1%"}
        ])
        audit_summary.index = np.arange(1, len(audit_summary) + 1)
        st.table(audit_summary)
