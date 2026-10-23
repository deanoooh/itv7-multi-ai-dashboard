import streamlit as st
import pandas as pd
import re

# Set page config for wide view and high-contrast dark theme support
st.set_page_config(
    page_title="ITV7 Multi-AI Racing Consensus & Audit Engine",
    page_icon="🏇",
    layout="wide"
)

# Custom CSS for high-contrast dark styling
st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    h1, h2, h3 { color: #FAFAFA; }
    .stCodeBlock { border: 1px solid #30363D; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# STAKING LOGIC UTILITY
# ---------------------------------------------------------
def evaluate_staking_rule(odds_str):
    """
    Staking Rules:
    - < 2/1 SP: 🔴 No Bet Filter (£0.00)
    - 2/1 to 5/1: £1.00 Win Only (£1.00)
    - >= 6/1: £0.50 Each-Way (£1.00 total stake)
    """
    if not odds_str or "/" not in odds_str:
        return "🔴 No Bet Filter", 0.0, "No Bet"
    
    try:
        num, den = map(int, odds_str.strip().split("/"))
        decimal_odds = (num / den) + 1.0
        
        if decimal_odds < 3.0:  # Less than 2/1
            return "🔴 No Bet Filter", 0.0, "No Bet"
        elif 3.0 <= decimal_odds < 7.0:  # 2/1 to 5/1
            return "£1.00 Win Only", 1.0, "Win"
        else:  # >= 6/1
            return "£0.50 EW (£1.00 Total)", 1.0, "Each-Way"
    except Exception:
        return "🔴 No Bet Filter", 0.0, "No Bet"

# ---------------------------------------------------------
# INITIALIZE SESSION STATE
# ---------------------------------------------------------
if 'ai_inputs' not in st.session_state:
    st.session_state.ai_inputs = {
        'Master Engine (v5.27.0)': {},
        'ChatGPT': {},
        'Claude': {},
        'DeepSeek': {}
    }

if 'settlement_data' not in st.session_state:
    st.session_state.settlement_data = {f"Race {i}": {"winner": "", "sp": "", "placed": ""} for i in range(1, 8)}

# ---------------------------------------------------------
# UI TABS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📋 AI Selections Hub", "📊 5th Consensus Engine", "⚖️ Audit & Settlement"])

# ---------------------------------------------------------
# TAB 1: 4-AI PASTE HUB (Including 3-Tier Master Engine)
# ---------------------------------------------------------
with tab1:
    st.header("📋 Multi-AI Selections Input Hub")
    st.caption("Paste output from Master Engine v5.27.0 (Primary, Secondary, Chaos) and comparative AI engines.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏆 Master Engine v5.27.0 (3-Tier)")
        for race_num in range(1, 8):
            with st.expander(f"Race {race_num} - Master Engine Tier Selections", expanded=(race_num == 1)):
                p_horse = st.text_input(f"R{race_num} Primary Horse", key=f"me_p_h_{race_num}")
                p_odds = st.text_input(f"R{race_num} Primary Odds (e.g. 4/1)", key=f"me_p_o_{race_num}")
                
                s_horse = st.text_input(f"R{race_num} Secondary Horse", key=f"me_s_h_{race_num}")
                s_odds = st.text_input(f"R{race_num} Secondary Odds", key=f"me_s_o_{race_num}")
                
                c_horse = st.text_input(f"R{race_num} Chaos Horse", key=f"me_c_h_{race_num}")
                c_odds = st.text_input(f"R{race_num} Chaos Odds", key=f"me_c_o_{race_num}")

                # Save to state
                st.session_state.ai_inputs['Master Engine (v5.27.0)'][f"Race {race_num}"] = {
                    'Primary': {'horse': p_horse, 'odds': p_odds},
                    'Secondary': {'horse': s_horse, 'odds': s_odds},
                    'Chaos': {'horse': c_horse, 'odds': c_odds}
                }

    with col2:
        st.subheader("🤖 Comparative AI Inputs")
        selected_ai = st.selectbox("Select AI Model", ["ChatGPT", "Claude", "DeepSeek"])
        
        for race_num in range(1, 8):
            ai_pick = st.text_input(f"Race {race_num} Selection ({selected_ai})", key=f"{selected_ai}_r{race_num}")
            ai_odds = st.text_input(f"Race {race_num} Odds ({selected_ai})", key=f"{selected_ai_o}_r{race_num}" if 'selected_ai_o' in locals() else f"{selected_ai}_o_r{race_num}")
            
            st.session_state.ai_inputs[selected_ai][f"Race {race_num}"] = {
                'Primary': {'horse': ai_pick, 'odds': ai_odds}
            }

# ---------------------------------------------------------
# TAB 2: 5TH CONSENSUS ENGINE
# ---------------------------------------------------------
with tab2:
    st.header("📊 5th Consensus Engine & Staking Breakdown")
    st.write("Aggregates selections across all engines to determine top consensus per race.")

    consensus_summary = []

    for race_num in range(1, 8):
        race_key = f"Race {race_num}"
        st.markdown(f"### 🏁 Race {race_num}")
        
        # Pull Master Engine 3 Tiers
        me_data = st.session_state.ai_inputs['Master Engine (v5.27.0)'].get(race_key, {})
        
        tier_rows = []
        for tier in ['Primary', 'Secondary', 'Chaos']:
            t_info = me_data.get(tier, {'horse': '', 'odds': ''})
            h_name = t_info.get('horse', '')
            odds = t_info.get('odds', '')
            rule, stake, btype = evaluate_staking_rule(odds)
            
            tier_rows.append({
                "Tier": f"Master Engine - {tier}",
                "Horse Selection": h_name if h_name else "—",
                "Odds (SP)": odds if odds else "—",
                "Staking Action": rule,
                "Outlay": f"£{stake:.2f}"
            })
            
        st.table(pd.DataFrame(tier_rows))

# ---------------------------------------------------------
# TAB 3: AUDIT & SETTLEMENT
# ---------------------------------------------------------
with tab3:
    st.header("⚖️ Side-by-Side Audit & Settlement Engine")
    st.caption("Enter actual winning horses and SPs to auto-settle ROI across all 3 tiers.")

    settle_rows = []
    total_outlay = 0.0
    total_returns = 0.0

    for race_num in range(1, 8):
        race_key = f"Race {race_num}"
        c1, c2, c3 = st.columns(3)
        
        with c1:
            winner = st.text_input(f"R{race_num} Actual Winner", key=f"win_r{race_num}")
        with c2:
            winning_sp = st.text_input(f"R{race_num} Winner SP", key=f"sp_r{race_num}")
        with c3:
            st.write(f"**Race {race_num} Status**: " + ("✅ Settled" if winner else "⏳ Pending"))

    st.markdown("---")
    st.subheader("📈 Settlement Summary")
    st.metric(label="Total Outlay", value=f"£{total_outlay:.2f}")
    st.metric(label="Total Returns", value=f"£{total_returns:.2f}")
