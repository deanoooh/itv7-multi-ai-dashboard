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

TIPSTER_PRIORITY = {"Gemini": 0, "Copilot": 1, "ChatGPT": 2, "WildCard": 3}
TIER_ORDER = ["PRIMARY", "SECONDARY", "CHAOS"]

# ==========================================
# HELPER FUNCTIONS & PARSERS
# ==========================================
def parse_odds_to_decimal(odds_str):
    """Converts odds string (e.g. '11/4', '2/1', '8/11', 'Evs') to decimal odds."""
    if not odds_str:
        return 2.0
    odds_str = odds_str.strip().lower().replace(' ', '')
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


def clean_runner_name(value):
    value = value.strip()
    value = value.replace('🔴', '').replace('No Bet', '').replace('no bet', '').strip()
    value = re.sub(r'\s+', ' ', value)
    value = re.sub(r'\s*[|;]\s*$', '', value)
    value = value.strip(' -–—:')
    return value


def parse_confidence(value):
    if not value:
        return None
    m = re.search(r'(?:Conf(?:idence)?\s*[:=]?\s*|\(\s*Conf(?:idence)?\s*[:=]?\s*)(\d+)', value, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'\b(\d)\b', value)
    if m:
        return int(m.group(1))
    return None


def extract_odds(value):
    match = re.search(r'(\d+\s*/\s*\d+|evs|eve|even|evens)', value, re.IGNORECASE)
    if match:
        return re.sub(r'\s+', '', match.group(1))
    return None


def is_no_bet_flag(value):
    return '🔴' in value or 'no bet' in value.lower() or 'no-bet' in value.lower()


def parse_field_size(text):
    m = re.search(r'(?:Runners?|Field(?:\s+size)?)\s*[:=]\s*(\d+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def parse_structured_tipster_block(text, tipster_name):
    """Parse a tipster's structured selections of the form:
    13:25 Redcar | Runners: 14 | PRIMARY: Horse (2/1) | SECONDARY: Horse (5/1) | CHAOS: Horse (20/1) | Confidence: 7
    """
    if not text or not text.strip():
        return {}

    records = {}
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    current_time = None
    current_course = "Unknown"
    current_field_size = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Race header detection
        header_match = re.search(r'(\d{1,2}:\d{2})\s*[-–—]?\s*([A-Za-z][A-Za-z0-9&\'\s.-]+)', line)
        if header_match:
            current_time = header_match.group(1)
            current_course = header_match.group(2).strip()
            current_course = re.sub(r'\s*[-–—].*$', '', current_course).strip() or 'Unknown'
            current_field_size = parse_field_size(line)
            continue

        if current_time is None:
            continue

        # Split on pipes or semicolons, then parse tier labels
        for part in re.split(r'\s*[|;]\s*', line):
            if not part:
                continue
            part_l = part.strip()
            for tier in TIER_ORDER:
                if re.match(rf'^{tier}\s*[:\-]', part_l, re.IGNORECASE):
                    value = re.sub(rf'^{tier}\s*[:\-]\s*', '', part_l, flags=re.IGNORECASE).strip()
                    odds = extract_odds(value)
                    if not odds:
                        continue
                    runner = value[:value.rfind('(')] if '(' in value else value
                    runner = clean_runner_name(runner)
                    if not runner:
                        continue

                    if runner.lower() in ['unknown', 'na', 'n/a']:
                        continue

                    conf = parse_confidence(value)
                    flag = is_no_bet_flag(value)
                    race_key = (current_time, current_course)
                    if race_key not in records:
                        records[race_key] = {
                            'time': current_time,
                            'course': current_course,
                            'field_size': current_field_size,
                            'tiers': {tier_name: None for tier_name in TIER_ORDER},
                            'tipster': tipster_name,
                            'flagged': []
                        }

                    records[race_key]['tiers'][tier] = {
                        'runner': runner,
                        'odds_str': odds,
                        'odds_dec': parse_odds_to_decimal(odds),
                        'confidence': conf,
                        'flag': flag,
                        'tipster': tipster_name
                    }

    # Allow single-line inputs where all tiers are on one line after the race header
    if not records:
        # Build a single-pass from the whole block if not already parsed
        block = text.strip()
        # detect time+course and then parse all tiers from remaining text
        header_match = re.search(r'(\d{1,2}:\d{2})\s*[-–—]?\s*([A-Za-z][A-Za-z0-9&\'\s.-]+)', block)
        if header_match:
            current_time = header_match.group(1)
            current_course = header_match.group(2).strip()
            current_course = re.sub(r'\s*[-–—].*$', '', current_course).strip() or 'Unknown'
            current_field_size = parse_field_size(block)
            record = {'time': current_time, 'course': current_course, 'field_size': current_field_size, 'tiers': {tier_name: None for tier_name in TIER_ORDER}, 'tipster': tipster_name, 'flagged': []}
            for tier in TIER_ORDER:
                tier_match = re.search(rf'(?i){tier}\s*[:\-]\s*(.*?)(?=(?:\s*(?:\||;|\bPRIMARY\b|\bSECONDARY\b|\bCHAOS\b))|$)', block)
                if tier_match:
                    value = tier_match.group(1).strip()
                    odds = extract_odds(value)
                    if odds:
                        runner = value[:value.rfind('(')] if '(' in value else value
                        runner = clean_runner_name(runner)
                        conf = parse_confidence(value)
                        flag = is_no_bet_flag(value)
                        if runner:
                            record['tiers'][tier] = {'runner': runner, 'odds_str': odds, 'odds_dec': parse_odds_to_decimal(odds), 'confidence': conf, 'flag': flag, 'tipster': tipster_name}
            records[(current_time, current_course)] = record

    return records


def build_dynamic_consensus(all_tipster_data):
    """Applies the 8-Rule Dynamic Consensus Engine per race.
    all_tipster_data is a list of dicts keyed by (time, course), one dict per tipster.
    """
    race_map = {}

    # Combine all tipsters' race records by race key
    for tipster_name, data in all_tipster_data.items():
        for race_key, record in data.items():
            if race_key not in race_map:
                race_map[race_key] = {
                    'time': record['time'],
                    'course': record['course'],
                    'field_size': record.get('field_size'),
                    'tipsters': {}
                }
            race_map[race_key]['tipsters'][tipster_name] = record['tiers']

    result = []
    warnings = []

    for race_key in sorted(race_map, key=lambda k: (race_map[k]['time'], race_map[k]['course'])):
        race = race_map[race_key]
        time = race['time']
        course = race['course']
        field_size = race.get('field_size')

        # Flag missing confidence scores
        missing_conf = []
        for tipster_name, tiers in race['tipsters'].items():
            for tier_name, pick in tiers.items():
                if pick and pick.get('confidence') is None:
                    missing_conf.append(f"{tipster_name} {tier_name}")
        if missing_conf:
            warnings.append(f"{time} {course}: Missing confidence score for {', '.join(missing_conf)}")

        # Flag missing unclear field sizes
        if field_size is None:
            warnings.append(f"{time} {course}: Missing or unclear field size — SPPF pending")

        # Build vote tallies per tier with de-duplication across tiers
        consensus = {}
        used_horses = set()
        value_flags = []

        for tier in TIER_ORDER:
            tier_votes = {}
            for tipster_name in TIPSTER_PRIORITY:
                if tipster_name not in race['tipsters']:
                    continue
                pick = race['tipsters'][tipster_name].get(tier)
                if not pick:
                    continue
                runner = pick['runner']
                if runner in used_horses:
                    continue
                if runner not in tier_votes:
                    tier_votes[runner] = {'count': 0, 'confidence_values': [], 'tipster_order': []}
                tier_votes[runner]['count'] += 1
                if pick.get('confidence') is not None:
                    tier_votes[runner]['confidence_values'].append(pick['confidence'])
                tier_votes[runner]['tipster_order'].append(TIPSTER_PRIORITY[tipster_name])

            if not tier_votes:
                consensus[tier] = None
                continue

            def winner_sort_key(item):
                runner, data = item
                avg_conf = np.mean(data['confidence_values']) if data['confidence_values'] else 0.0
                earliest_tipster = min(data['tipster_order']) if data['tipster_order'] else 999
                return (data['count'], avg_conf, -earliest_tipster)

            chosen_runner, chosen_data = sorted(tier_votes.items(), key=winner_sort_key, reverse=True)[0]
            consensus[tier] = {
                'runner': chosen_runner,
                'votes': chosen_data['count'],
                'odds_str': next(
                    (
                        race['tipsters'][tn][tier]['odds_str']
                        for tn in TIPSTER_PRIORITY
                        if tn in race['tipsters'] and race['tipsters'][tn].get(tier) and race['tipsters'][tn][tier]['runner'] == chosen_runner
                    ),
                    '2/1'
                ),
                'confidence_avg': float(np.mean(chosen_data['confidence_values'])) if chosen_data['confidence_values'] else None,
                'tie_break': 'Confidence weighted' if chosen_data['confidence_values'] else 'Listed order fallback',
                'used_tipsters': [
                    tn for tn in TIPSTER_PRIORITY
                    if tn in race['tipsters'] and race['tipsters'][tn].get(tier) and race['tipsters'][tn][tier]['runner'] == chosen_runner
                ]
            }
            used_horses.add(chosen_runner)

        primary_choice = consensus.get('PRIMARY')
        secondary_choice = consensus.get('SECONDARY')

        sppf = None
        if primary_choice:
            primary_odds_dec = parse_odds_to_decimal(primary_choice['odds_str'])
            if field_size is not None and field_size >= 6 and primary_choice['votes'] >= 3 and 2.0 < primary_odds_dec <= 3.0:
                sppf = {
                    'triggered': True,
                    'field_size': field_size,
                    'primary_demoted': primary_choice['runner'],
                    'secondary_promoted': secondary_choice['runner'] if secondary_choice else None,
                    'note': 'SPPF triggered'
                }
                if secondary_choice:
                    consensus['SECONDARY'] = primary_choice
                    consensus['PRIMARY'] = secondary_choice
                    # Do not re-check SPPF; promoted horse stays as primary

        if field_size is None and primary_choice is not None:
            sppf = {'triggered': False, 'field_size': None, 'note': 'SPPF pending'}

        # Value flag on chaos horses at 5/1 or longer backed by 2+ tipsters
        if field_size is not None and consensus.get('CHAOS'):
            chaos_runner = consensus['CHAOS']['runner']
            chaos_votes = 0
            for tipster_name in TIPSTER_PRIORITY:
                if tipster_name not in race['tipsters']:
                    continue
                pick = race['tipsters'][tipster_name].get('CHAOS')
                if pick and pick['runner'] == chaos_runner:
                    chaos_votes += 1
            chaos_odds_dec = parse_odds_to_decimal(consensus['CHAOS']['odds_str'])
            if chaos_votes >= 2 and chaos_odds_dec >= 6.0:
                value_flags.append(f"{chaos_runner} ({consensus['CHAOS']['odds_str']}) at 5/1+ backed by {chaos_votes} tipsters")

        result.append({
            'time': time,
            'course': course,
            'distance': 'Unknown',
            'runners': field_size or 'Unknown',
            'sppf': sppf,
            'consensus': consensus,
            'value_flags': value_flags,
            'warnings': warnings
        })

    return result


def parse_ai_text(text):
    """Original parser retained for backwards compatibility with the simpler app format."""
    races = []
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]

    header_keywords = ['going', 'runners', 'e/w', 'odds', 'places', 'distance', 'class', 'handicap', 'standard']

    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in header_keywords) and not re.search(r'(\d+\s*/\s*\d+|evs)', line_lower):
            continue

        # Full result-sheet rows like:
        # '1st – Winner – (8) – Kartini – P Mulrennan – S Whitaker – 13/2'
        if re.match(r'^(?:\d+(?:st|nd|rd|th)|PU)\b', line, re.IGNORECASE):
            odds_match = re.search(r'(\d+\s*/\s*\d+(?:[a-zA-Z]+)?|evs|eve)', line, re.IGNORECASE)
            if odds_match:
                odds_str = re.sub(r'\s+', '', odds_match.group(1))
                line_without_odds = line[:odds_match.start()].rstrip()
                parts = [p.strip() for p in re.split(r'\s*[-–—]\s*', line_without_odds) if p.strip()]

                runner = None
                for part in parts:
                    clean = re.sub(r'^\(|\)$', '', part).strip()
                    if not clean or clean.lower() in {'winner', 'pu'}:
                        continue
                    if re.fullmatch(r'\(\d+\)', clean):
                        continue
                    if re.fullmatch(r'\d+(?:st|nd|rd|th)', clean, re.IGNORECASE):
                        continue
                    if re.fullmatch(r'[\d\s¼½¾+-]+', clean):
                        continue
                    if re.search(r'[A-Za-z]', clean):
                        runner = clean
                        break

                if runner:
                    races.append({
                        "time": "Unknown",
                        "course": "Unknown",
                        "runner": runner,
                        "odds_str": odds_str,
                        "odds_dec": parse_odds_to_decimal(odds_str),
                        "primary": f"{runner} ({odds_str})",
                        "secondary": "-",
                        "chaos": "-"
                    })
                    continue

        time_match = re.search(r'(\d{1,2}:\d{2})\s*([A-Za-z\s]+)?', line)
        if time_match:
            r_time = time_match.group(1)
            course = time_match.group(2).strip() if time_match.group(2) else "Unknown"
            course = re.sub(r'[-–|—].*', '', course).strip()

            if 'primary:' in line_lower:
                p_match = re.search(r'primary:\s*([^|(]+)\s*\(([\d/]+|evs)\)', line, re.IGNORECASE)
                s_match = re.search(r'secondary:\s*([^|(]+)\s*\(([\d/]+|evs)\)', line, re.IGNORECASE)
                c_match = re.search(r'chaos:\s*([^|(]+)\s*\(([\d/]+|evs)\)', line, re.IGNORECASE)

                p_runner = p_match.group(1).strip() if p_match else "N/A"
                p_odds = p_match.group(2) if p_match else "2/1"
                s_runner = s_match.group(1).strip() if s_match else "N/A"
                s_odds = s_match.group(2) if s_match else "2/1"
                c_runner = c_match.group(1).strip() if c_match else "N/A"
                c_odds = c_match.group(2) if c_match else "2/1"

                races.append({
                    "time": r_time,
                    "course": course,
                    "runner": p_runner,
                    "odds_str": p_odds,
                    "odds_dec": parse_odds_to_decimal(p_odds),
                    "primary": f"{p_runner} ({p_odds})",
                    "secondary": f"{s_runner} ({s_odds})",
                    "chaos": f"{c_runner} ({c_odds})"
                })
            else:
                odds_match = re.search(r'\(([\d/]+|evs)\)', line, re.IGNORECASE)
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
    """Aggregates picks across AIs, evaluates consensus, and applies strict profitability filters."""
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
        odds_dec = top_data['odds_dec']

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

        # PROFITABILITY & STAKING FILTER LOGIC
        is_no_bet = False
        if odds_dec < 2.0:
            staking_rule = "🔴 No Bet (Price < 2/1)"
            is_no_bet = True
        elif count == 1 and odds_dec >= 13.0:
            staking_rule = "🔴 No Bet (Unprofitable Risk Profile)"
            is_no_bet = True
        elif odds_dec < 6.0:
            staking_rule = "Win Only (£1.00)"
        else:
            staking_rule = "Each-Way (£0.50 EW)"

        consensus_results.append({
            "time": r_time,
            "course": data['course'],
            "consensus_runner": top_runner,
            "count": count,
            "agreement": agreement,
            "badge_class": badge_class,
            "odds_str": top_data['odds_str'],
            "odds_dec": odds_dec,
            "staking_rule": staking_rule,
            "is_no_bet": is_no_bet,
            "all_picks": picks
        })
    return consensus_results


def extract_stake_from_rule(staking_rule):
    if not staking_rule:
        return 1.0
    staking_rule = staking_rule.lower()
    if 'no bet' in staking_rule:
        return 0.0
    if 'each-way' in staking_rule:
        return 0.5
    if 'win only' in staking_rule:
        return 1.0
    return 1.0


def parse_race_results(results_text):
    """Parses race result sheets and returns a mapping keyed by (time, course)."""
    if not results_text or not results_text.strip():
        return {}

    results = {}
    active_race = None
    lines = [line.strip() for line in results_text.split('\n') if line.strip()]

    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ['going:', 'runners:', 'e/w:', 'odds', 'places', 'distance', 'class', 'handicap', 'standard']):
            continue

        # Race header: '13:25 Redcar – Going: Heavy – Runners: 14 ...'
        header_match = re.match(r'^\s*(\d{1,2}:\d{2})\s*[-–—]?\s*([A-Za-z][A-Za-z0-9&\'\s.-]+?)(?:\s*[-–—].*)?$', line, re.IGNORECASE)
        if header_match:
            time_value = header_match.group(1)
            course_name = header_match.group(2).strip()
            course_name = re.sub(r'\s*[-–—].*$', '', course_name).strip()
            active_race = {
                'time': time_value,
                'course': course_name or 'Unknown',
                'key': (time_value, course_name or 'Unknown')
            }
            continue

        if re.match(r'^(?:\d+(?:st|nd|rd|th)|PU)\b', line, re.IGNORECASE):
            odds_match = re.search(r'(\d+\s*/\s*\d+(?:[a-zA-Z]+)?|evs|eve)', line, re.IGNORECASE)
            if not odds_match or active_race is None:
                continue

            odds_str = re.sub(r'\s+', '', odds_match.group(1))
            odds_dec = parse_odds_to_decimal(odds_str)
            line_without_odds = line[:odds_match.start()].rstrip()
            tokens = [p.strip() for p in re.split(r'\s*[-–—]\s*', line_without_odds) if p.strip()]

            runner = None
            for token in reversed(tokens):
                clean = token.strip()
                if clean.lower() in {'winner', 'pu'}:
                    continue
                if re.fullmatch(r'\(\d+\)', clean):
                    continue
                if re.fullmatch(r'\d+(?:st|nd|rd|th)', clean, re.IGNORECASE):
                    continue
                if re.fullmatch(r'[\d\s¼½¾+-]+', clean):
                    continue
                if clean and re.search(r'[A-Za-z]', clean):
                    runner = clean
                    break

            if runner:
                results[active_race['key']] = {
                    'winner': runner,
                    'odds_str': odds_str,
                    'odds_dec': odds_dec,
                    'time': active_race['time'],
                    'course': active_race['course']
                }

    return results


def calculate_settlement(consensus_data, results_text):
    """Calculates win/loss for the consensus pick of each race against the pasted result sheet."""
    result_map = parse_race_results(results_text)
    rows = []
    total_pnl = 0.0

    for race in consensus_data:
        r_time = race['time']
        r_course = race['course']
        key = (r_time, r_course)
        selection = race['consensus_runner']
        stake = extract_stake_from_rule(race.get('staking_rule', ''))

        if race.get('is_no_bet') or stake == 0:
            pnl = 0.0
            status = 'NO BET'
            winner = '-'
        elif key not in result_map:
            pnl = 0.0
            status = 'NO RESULT'
            winner = '-'
        else:
            result = result_map[key]
            winner = result['winner']
            if selection.lower() == winner.lower():
                pnl = (result['odds_dec'] - 1.0) * stake
                status = 'WIN'
            else:
                pnl = -stake
                status = 'LOSS'

        total_pnl += pnl
        rows.append({
            'Time': r_time,
            'Course': r_course,
            'Selection': selection,
            'Winner': winner,
            'Stake': stake,
            'Status': status,
            'P/L': round(pnl, 2)
        })

    return rows, round(total_pnl, 2)


# ==========================================
# APPLICATION LAYOUT
# ==========================================
st.title("🏇 ITV7 Multi-AI Racing Consensus & Audit Engine")
st.caption("v5.23.2 Dynamic Consensus • Digital Pipeline & Auto-Calculating Audit")

# Main Tabs
tab1, tab2, tab3 = st.tabs(["📝 1. Paste & Selections Hub", "📊 2. Side-by-Side Comparison", "💰 3. Settlement & Audit"])

# TAB 1: PASTE & SELECTIONS HUB
with tab1:
    st.subheader("Paste Selection Output Blocks")
    st.info("Use either the original simple format, or the 8-Rule Dynamic consensus format: 13:25 Redcar | Runners: 14 | PRIMARY: Horse (2/1) | SECONDARY: Horse (5/1) | CHAOS: Horse (20/1) | Confidence: 7")

    col1, col2 = st.columns(2)
    with col1:
        ai1_text = st.text_area("Gemini", value=st.session_state.get('ai1_input', ''), height=180, key="ai1_area")
        ai2_text = st.text_area("Copilot", value=st.session_state.get('ai2_input', ''), height=180, key="ai2_area")
    with col2:
        ai3_text = st.text_area("ChatGPT", value=st.session_state.get('ai3_input', ''), height=180, key="ai3_area")
        ai4_text = st.text_area("WildCard", value=st.session_state.get('ai4_input', ''), height=180, key="ai4_area")

    ai1_parsed = parse_ai_text(ai1_text) if ai1_text else []
    ai2_parsed = parse_ai_text(ai2_text) if ai2_text else []
    ai3_parsed = parse_ai_text(ai3_text) if ai3_text else []
    ai4_parsed = parse_ai_text(ai4_text) if ai4_text else []

    # Dynamic consensus engine using per-tipster structured blocks
    structured_data = {
        "Gemini": parse_structured_tipster_block(ai1_text, "Gemini") if ai1_text else {},
        "Copilot": parse_structured_tipster_block(ai2_text, "Copilot") if ai2_text else {},
        "ChatGPT": parse_structured_tipster_block(ai3_text, "ChatGPT") if ai3_text else {},
        "WildCard": parse_structured_tipster_block(ai4_text, "WildCard") if ai4_text else {},
    }

    dynamic_consensus = build_dynamic_consensus(structured_data) if any(structured_data.values()) else []

    all_ais = [ai1_parsed, ai2_parsed, ai3_parsed, ai4_parsed]
    consensus_data = calculate_consensus(all_ais) if any(all_ais) else []
    if dynamic_consensus:
        consensus_data = []
        for race in dynamic_consensus:
            primary = race['consensus'].get('PRIMARY')
            if primary:
                consensus_data.append({
                    'time': race['time'],
                    'course': race['course'],
                    'consensus_runner': primary['runner'],
                    'count': primary['votes'],
                    'agreement': f"Primary consensus ({primary['votes']}/4)",
                    'badge_class': 'badge-majority',
                    'odds_str': primary['odds_str'],
                    'odds_dec': parse_odds_to_decimal(primary['odds_str']),
                    'staking_rule': 'Win Only (£1.00)',
                    'is_no_bet': False,
                    'all_picks': {}
                })

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
        df_consensus.index = np.arange(1, len(df_consensus) + 1)
        st.dataframe(df_consensus, use_container_width=True)

        if dynamic_consensus:
            st.subheader("⚠️ Dynamic Consensus Audit")
            for race in dynamic_consensus:
                st.write(f"{race['time']} {race['course']} — Runners: {race['runners']}")
                if race['sppf']:
                    if race['sppf']['triggered']:
                        st.write(f"SPPF triggered — field size {race['sppf']['field_size']} — {race['sppf']['primary_demoted']} demoted, {race['sppf']['secondary_promoted']} promoted")
                    else:
                        st.write("SPPF pending")
                for tier in TIER_ORDER:
                    pick = race['consensus'].get(tier)
                    if pick:
                        st.write(f"{tier}: {pick['runner']} ({pick['odds_str']}) — votes {pick['votes']} — {pick['tie_break']}")
                if race['value_flags']:
                    st.write("Value Flags: " + "; ".join(race['value_flags']))
                st.markdown("---")

# TAB 2: SIDE-BY-SIDE COMPARISON MATRIX
with tab2:
    st.subheader("Multi-AI Side-by-Side Comparison Matrix")

    if not consensus_data:
        st.warning("Please paste AI selections in Tab 1.")
    else:
        matrix_rows = []
        for c in consensus_data:
            r_time = c['time']

            def get_pick(parsed_list):
                for item in parsed_list:
                    if item['time'] == r_time:
                        if item['secondary'] != "-":
                            return f"P: {item['primary']} | S: {item['secondary']} | C: {item['chaos']}"
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

    if consensus_data and results_text.strip():
        settlement_rows, total_pnl = calculate_settlement(consensus_data, results_text)
        df_settlement = pd.DataFrame(settlement_rows)

        col_total, col_wins, col_losses = st.columns(3)
        with col_total:
            st.metric("Total P/L", f"£{total_pnl:.2f}")
        with col_wins:
            st.metric("Wins", sum(1 for r in settlement_rows if r['Status'] == 'WIN'))
        with col_losses:
            st.metric("Losses", sum(1 for r in settlement_rows if r['Status'] == 'LOSS'))

        st.dataframe(df_settlement, use_container_width=True)
    elif not consensus_data:
        st.warning("Please complete Tab 1 first so there are actual consensus selections to settle.")
    else:
        st.info("Paste the full racecard/result sheet to calculate P/L against the current consensus picks.")
