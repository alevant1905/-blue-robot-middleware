"""
Blue Robot Memory System
========================
Handles facts storage, extraction, and long-term memory.
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import log

# ================================================================================
# CONFIGURATION
# ================================================================================

BLUE_FACTS_DB = os.environ.get("BLUE_FACTS_DB", "data/blue.db")
BLUE_FACTS: Dict[str, str] = {}

# Try to load enhanced memory system
try:
    from blue_memory_improved import get_memory_system
    memory_system = get_memory_system()
    ENHANCED_MEMORY_AVAILABLE = True
    print("[OK] Enhanced memory system loaded - Blue will remember better!")
except ImportError as e:
    ENHANCED_MEMORY_AVAILABLE = False
    memory_system = None
    print(f"[WARN] Enhanced memory not available: {e}")
    print("[WARN] Using legacy memory system")


# ================================================================================
# FACT LOADING/SAVING
# ================================================================================

def load_blue_facts(db_path: str = BLUE_FACTS_DB) -> Dict[str, str]:
    """Load facts using improved memory system if available."""
    if ENHANCED_MEMORY_AVAILABLE and memory_system:
        return memory_system.load_facts()

    # Fallback to legacy system
    facts: Dict[str, str] = {}
    try:
        if not os.path.exists(db_path):
            log.warning(f"[MEM] facts DB not found: {db_path}")
            return facts
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT fact_key, values_concat FROM facts_top").fetchall()
        for r in rows:
            facts[r["fact_key"]] = r["values_concat"]
    except Exception as e:
        log.warning(f"[MEM] failed to load facts: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
    if facts:
        log.info(f"[MEM] loaded {len(facts)} core facts from {db_path}")
    return facts


def save_blue_facts(facts: Dict[str, str], db_path: str = None) -> bool:
    """Save facts using improved memory system if available."""
    global BLUE_FACTS
    BLUE_FACTS.update(facts)

    if ENHANCED_MEMORY_AVAILABLE and memory_system:
        return memory_system.save_facts(facts)

    # Fallback to legacy system
    if db_path is None:
        db_path = BLUE_FACTS_DB

    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts_top (
                fact_key TEXT PRIMARY KEY,
                values_concat TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        saved_count = 0
        for fact_key, values_concat in facts.items():
            cursor.execute("""
                INSERT INTO facts_top (fact_key, values_concat, last_updated)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(fact_key) DO UPDATE SET
                    values_concat = excluded.values_concat,
                    last_updated = CURRENT_TIMESTAMP
            """, (fact_key, values_concat))
            saved_count += 1

        conn.commit()
        conn.close()
        log.info(f"[MEM] Saved {saved_count} facts to database")
        return True
    except Exception as e:
        log.error(f"[MEM] Failed to save facts: {e}")
        return False


def _facts_block() -> str:
    """Build a formatted string of facts for system prompt."""
    items: List[str] = []
    facts = load_blue_facts() if ENHANCED_MEMORY_AVAILABLE else BLUE_FACTS

    def add(label: str, key: str) -> None:
        v = facts.get(key)
        if v:
            items.append(f"{label}: {v}")

    for label, key in [
        ("Name", "name"),
        ("Identity", "identity"),
        ("Created by", "created_by"),
        ("Original form", "original_form"),
        ("Upgraded by", "upgraded_by"),
        ("Privacy", "privacy"),
        ("Physical features", "physical_features"),
        ("Tools", "tool"),
        ("Has memory", "has_memory"),
        ("Moods", "mood"),
    ]:
        add(label, key)
    return " | ".join(items)


def build_system_preamble() -> str:
    """Build the system preamble with Blue's facts."""
    core = _facts_block()
    return ("You are Blue. Use these ground-truth facts as identity context. "
            "Do not contradict them. " + core) if core else "You are Blue."


# ================================================================================
# FACT EXTRACTION
# ================================================================================

def extract_and_save_facts(messages: list) -> bool:
    """Extract facts from conversation and save to database."""
    if ENHANCED_MEMORY_AVAILABLE and memory_system:
        try:
            return memory_system.extract_and_save_facts(messages)
        except Exception as e:
            log.warning(f"[MEM] Enhanced extraction failed, using legacy: {e}")

    if not messages:
        return False

    facts_to_save = {}

    for msg in messages:
        if msg.get('role') not in ['user', 'assistant']:
            continue

        content = msg.get('content', '')
        content_lower = content.lower()

        if len(content) < 10 or content.strip().startswith(('{', '[', '```', 'import ')):
            continue

        # === NAME EXTRACTION ===
        name_patterns = [
            r"my name is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"i'?m ([A-Z][a-z]+)(?:\s|,|\.|$)",
            r"call me ([A-Z][a-z]+)",
            r"this is ([A-Z][a-z]+) speaking",
            r"it'?s ([A-Z][a-z]+) here"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1).strip()
                if 2 <= len(name) <= 30 and name.replace(' ', '').isalpha():
                    facts_to_save['user_name'] = name
                    log.info(f"[MEM] Learned name: {name}")
                    break

        # === LOCATION EXTRACTION ===
        location_patterns = [
            r"i live in ([A-Z][a-zA-Z\s,]+?)(?:\.|,|$|\sand\s|\swith\s)",
            r"i'?m (?:from|in|based in) ([A-Z][a-zA-Z\s]+?)(?:\.|,|$)",
            r"my (?:city|town|home) is ([A-Z][a-zA-Z\s]+)",
            r"we live in ([A-Z][a-zA-Z\s,]+?)(?:\.|,|$)"
        ]
        for pattern in location_patterns:
            match = re.search(pattern, content)
            if match:
                location = match.group(1).strip().rstrip('.,;')
                if 2 <= len(location) <= 50:
                    facts_to_save['location'] = location
                    log.info(f"[MEM] Learned location: {location}")
                    break

        # === WORK/EDUCATION ===
        work_patterns = [
            (r"i (?:work|teach) at ([A-Z][a-zA-Z\s&.]+?)(?:\.|,|$)", 'workplace'),
            (r"i work for ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)", 'workplace'),
            (r"i'?m (?:a|an) ([a-z][a-z\s]+(?:teacher|professor|engineer|developer|doctor|scientist|artist|writer|designer|manager|director))", 'occupation'),
            (r"i studied (?:at )?([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)", 'education'),
            (r"i graduated from ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)", 'education'),
            (r"i run ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)", 'business'),
            (r"my company is ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)", 'business')
        ]
        for pattern, key in work_patterns:
            match = re.search(pattern, content)
            if match:
                value = match.group(1).strip().rstrip('.,;')
                if 2 <= len(value) <= 100:
                    facts_to_save[key] = value
                    log.info(f"[MEM] Learned {key}: {value}")

        # === FAMILY EXTRACTION ===
        family_relations = ['partner', 'wife', 'husband', 'spouse', 'daughter', 'son', 'child',
                          'mother', 'father', 'mom', 'dad', 'brother', 'sister', 'girlfriend', 'boyfriend']
        for relation in family_relations:
            patterns = [
                rf"my {relation}(?:'s name)? is ([A-Z][a-z]+)",
                rf"my {relation},? ([A-Z][a-z]+)",
                rf"(?:this is |meet )?my {relation} ([A-Z][a-z]+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    name = match.group(1).strip()
                    if 2 <= len(name) <= 30 and name.isalpha():
                        facts_to_save[f'{relation}_name'] = name
                        log.info(f"[MEM] Learned {relation}: {name}")
                        break

        # Multiple children
        if re.search(r"my (?:daughters?|sons?|children|kids) (?:are|named) ", content_lower):
            match = re.search(r"my (?:daughters?|sons?|children|kids) (?:are|named) ([A-Z][a-zA-Z,\s&]+?)(?:\.|$)", content)
            if match:
                names = match.group(1).strip()
                if 2 <= len(names) <= 100:
                    facts_to_save['children_names'] = names
                    log.info(f"[MEM] Learned children: {names}")

        # === PETS ===
        pet_types = ['dog', 'cat', 'pet', 'puppy', 'kitten', 'bird', 'fish', 'hamster', 'rabbit']
        for pet in pet_types:
            patterns = [
                rf"my {pet}(?:'s name)? is ([A-Z][a-z]+)",
                rf"my {pet},? ([A-Z][a-z]+)",
                rf"i have a {pet} (?:named |called )?([A-Z][a-z]+)",
                rf"(?:this is |meet )?my {pet} ([A-Z][a-z]+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    name = match.group(1).strip()
                    if 2 <= len(name) <= 30 and name.isalpha():
                        facts_to_save[f'{pet}_name'] = name
                        log.info(f"[MEM] Learned {pet}: {name}")
                        break

        # === HOBBIES & INTERESTS ===
        hobby_patterns = [
            (r"i (?:love|enjoy|like) (?:to )?([a-z]+ing)", 'hobby'),
            (r"my hobbies? (?:is|are|include) ([a-zA-Z,\s&]+?)(?:\.|$)", 'hobbies'),
            (r"i'?m (?:really )?into ([a-zA-Z\s]+?)(?:\.|,|$)", 'interest'),
            (r"i collect ([a-zA-Z\s]+?)(?:\.|,|$)", 'collection')
        ]
        for pattern, key in hobby_patterns:
            match = re.search(pattern, content_lower)
            if match:
                value = match.group(1).strip().rstrip('.,;')
                if 3 <= len(value) <= 50:
                    facts_to_save[key] = value.title()
                    log.info(f"[MEM] Learned {key}: {value}")

        # === PREFERENCES ===
        if 'my favorite' in content_lower or 'i prefer' in content_lower:
            match = re.search(r"my favorite ([a-z\s]+) is ([a-zA-Z0-9\s]+?)(?:\.|,|$)", content_lower)
            if match:
                pref_type = match.group(1).strip().replace(' ', '_')
                pref_value = match.group(2).strip().title()
                if len(pref_type) <= 20 and len(pref_value) <= 50:
                    facts_to_save[f'favorite_{pref_type}'] = pref_value
                    log.info(f"[MEM] Learned {pref_type}: {pref_value}")

            match = re.search(r"i prefer ([a-zA-Z\s]+) (?:over|to) ([a-zA-Z\s]+)", content_lower)
            if match:
                preference = f"{match.group(1).strip()} over {match.group(2).strip()}"
                facts_to_save['preference'] = preference.title()
                log.info(f"[MEM] Learned preference: {preference}")

        # === BIRTHDAY/AGE ===
        if "i'm " in content_lower or "i am " in content_lower:
            match = re.search(r"i'?m (\d{1,2}) years old", content_lower)
            if match:
                age = match.group(1)
                if 5 <= int(age) <= 120:
                    facts_to_save['age'] = age
                    log.info(f"[MEM] Learned age: {age}")

        birthday_patterns = [
            r"my birthday is ([A-Za-z]+ \d{1,2})",
            r"i was born (?:on )?([A-Za-z]+ \d{1,2})",
            r"my birthday'?s? (?:on )?([A-Za-z]+ \d{1,2})"
        ]
        for pattern in birthday_patterns:
            match = re.search(pattern, content)
            if match:
                birthday = match.group(1).strip()
                facts_to_save['birthday'] = birthday
                log.info(f"[MEM] Learned birthday: {birthday}")
                break

        # === ALLERGIES/DIETARY ===
        allergy_patterns = [
            r"i'?m allergic to ([a-zA-Z\s,]+?)(?:\.|$)",
            r"i have (?:a |an )?([a-zA-Z\s]+) allergy",
            r"i can'?t eat ([a-zA-Z\s]+?)(?:\.|,|$)"
        ]
        for pattern in allergy_patterns:
            match = re.search(pattern, content_lower)
            if match:
                allergy = match.group(1).strip()
                if 2 <= len(allergy) <= 50:
                    facts_to_save['allergy'] = allergy.title()
                    log.info(f"[MEM] Learned allergy: {allergy}")
                    break

        dietary_patterns = [
            r"i'?m (?:a )?(vegetarian|vegan|pescatarian|gluten[- ]free|lactose[- ]intolerant|keto|paleo)",
            r"i (?:don'?t|do not) eat ([a-zA-Z\s]+?)(?:\.|,|$)"
        ]
        for pattern in dietary_patterns:
            match = re.search(pattern, content_lower)
            if match:
                diet = match.group(1).strip()
                facts_to_save['dietary'] = diet.title()
                log.info(f"[MEM] Learned dietary: {diet}")
                break

        # === VEHICLES ===
        vehicle_patterns = [
            (r"i drive (?:a |an )?(\d{4} )?([A-Z][a-zA-Z]+ [A-Z]?[a-zA-Z]+)", 'vehicle'),
            (r"my car is (?:a |an )?(\d{4} )?([A-Z][a-zA-Z]+ [A-Z]?[a-zA-Z]+)", 'vehicle'),
            (r"i have (?:a |an )?(\d{4} )?([A-Z][a-zA-Z]+ [A-Z]?[a-zA-Z]+) (?:car|truck|suv|vehicle)", 'vehicle'),
        ]
        for pattern, key in vehicle_patterns:
            match = re.search(pattern, content)
            if match:
                year = match.group(1).strip() if match.group(1) else ""
                make_model = match.group(2).strip()
                vehicle = f"{year}{make_model}".strip()
                if 3 <= len(vehicle) <= 50:
                    facts_to_save['vehicle'] = vehicle
                    log.info(f"[MEM] Learned vehicle: {vehicle}")
                    break

        # === LANGUAGES ===
        language_patterns = [
            r"i speak ([A-Z][a-z]+(?:,? (?:and )?[A-Z][a-z]+)*)",
            r"i'?m fluent in ([A-Z][a-z]+(?:,? (?:and )?[A-Z][a-z]+)*)",
            r"my (?:native|first) language is ([A-Z][a-z]+)",
            r"i'?m learning ([A-Z][a-z]+)"
        ]
        for pattern in language_patterns:
            match = re.search(pattern, content)
            if match:
                languages = match.group(1).strip()
                if 3 <= len(languages) <= 100:
                    facts_to_save['languages'] = languages
                    log.info(f"[MEM] Learned languages: {languages}")
                    break

        # === SKILLS/EXPERTISE ===
        skill_patterns = [
            r"i'?m (?:good|great|skilled|experienced) at ([a-zA-Z\s,]+?)(?:\.|$)",
            r"i know (?:how to )?([a-zA-Z\s]+?)(?:\.|$)",
            r"i can ([a-zA-Z\s]+) (?:well|professionally|expertly)",
            r"my skills? (?:include|are|is) ([a-zA-Z\s,]+?)(?:\.|$)"
        ]
        for pattern in skill_patterns:
            match = re.search(pattern, content_lower)
            if match:
                skill = match.group(1).strip()
                if 3 <= len(skill) <= 100 and skill not in ['do', 'be', 'help']:
                    facts_to_save['skills'] = skill.title()
                    log.info(f"[MEM] Learned skill: {skill}")
                    break

        # === MEDICAL ===
        medical_patterns = [
            r"i have ([a-zA-Z\s]+(?:diabetes|asthma|arthritis|condition|disease|disorder))",
            r"i'?m (?:on|taking) ([a-zA-Z\s]+) (?:medication|medicine|pills)",
            r"i wear ([a-zA-Z\s]+(?:glasses|contacts|hearing aid|braces))"
        ]
        for pattern in medical_patterns:
            match = re.search(pattern, content_lower)
            if match:
                medical = match.group(1).strip()
                if 3 <= len(medical) <= 50:
                    facts_to_save['medical'] = medical.title()
                    log.info(f"[MEM] Learned medical: {medical}")
                    break

        # === TIMEZONE/SCHEDULE ===
        if 'timezone' in content_lower or 'time zone' in content_lower:
            match = re.search(r"(?:my )?time ?zone is ([A-Z]{2,4}|[A-Z][a-z]+/[A-Z][a-z]+)", content)
            if match:
                tz = match.group(1).strip()
                facts_to_save['timezone'] = tz
                log.info(f"[MEM] Learned timezone: {tz}")

        # === PHONE/CONTACT ===
        phone_match = re.search(r"my (?:phone|number|cell) is ([0-9\-\(\)\s]{10,20})", content)
        if phone_match:
            phone = phone_match.group(1).strip()
            facts_to_save['phone'] = phone
            log.info(f"[MEM] Learned phone: {phone}")

        # === EMAIL ===
        email_match = re.search(r"my email is ([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", content)
        if email_match:
            email = email_match.group(1).strip()
            facts_to_save['email'] = email
            log.info(f"[MEM] Learned email: {email}")

    if facts_to_save:
        global BLUE_FACTS
        BLUE_FACTS.update(facts_to_save)
        return save_blue_facts(BLUE_FACTS)

    return False


# ================================================================================
# INITIALIZATION
# ================================================================================

def init_memory():
    """Initialize the memory system."""
    global BLUE_FACTS
    try:
        if not ENHANCED_MEMORY_AVAILABLE:
            BLUE_FACTS = load_blue_facts()
        else:
            BLUE_FACTS = {}
    except Exception:
        BLUE_FACTS = {}


# Initialize on import
init_memory()
