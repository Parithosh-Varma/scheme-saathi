"""Rule-based eligibility extraction + matching. Works offline; LLM refines when keys exist."""
import re
import json


def extract_profile(query: str) -> dict:
    q = query.lower()
    profile = {
        "age": None, "gender": None, "income_annual": None, "occupation": None,
        "location_type": None, "state": None, "caste": None, "family_size": None,
        "has_children": False, "is_farmer": False, "is_student": False,
        "is_widow": False, "has_disability": False, "raw_query": query,
    }
    m = re.search(r"(\d{1,3})\s*(saal|year|yrs|age|umr)", q)
    if m:
        try:
            profile["age"] = int(m.group(1))
        except Exception:
            pass
    else:
        m2 = re.search(r"\b(\d{2})\b", q)
        if m2 and any(w in q for w in ["age", "saal", "year", "old", "umr", "umra"]):
            profile["age"] = int(m2.group(1))
    if any(w in q for w in ["mahila", "aurat", "ladki", "woman", "female", "girl", "behna", "beti", "mother", "pregnant", "garbhvati", "widow", "vidhwa"]):
        profile["gender"] = "female"
    elif any(w in q for w in ["admi", "purush", "male", "man", "ladka"]):
        profile["gender"] = "male"
    if any(w in q for w in ["transgender", "trans", "kinnar"]):
        profile["gender"] = "other"
    if any(w in q for w in ["kisan", "farmer", "kheti", "fasal", "land", "zameen"]):
        profile["is_farmer"] = True
        profile["occupation"] = "farmer"
    if any(w in q for w in ["student", "padhai", "school", "college", "vidyarthi", "scholarship"]):
        profile["is_student"] = True
        profile["occupation"] = profile["occupation"] or "student"
    if any(w in q for w in ["mazdoor", "labour", "labor", "mistri", "construction", "mason", "shramik", "worker"]):
        profile["occupation"] = profile["occupation"] or "labourer"
    if any(w in q for w in ["vendor", "rehdi", "thela", "hawker", "shop", "dukaan", "business", "vyapar"]):
        profile["occupation"] = profile["occupation"] or "street vendor"
    if any(w in q for w in ["carpenter", "badhai", "tailor", "darzi", "potter", "kumhar", "barber", "nai", "artisan", "karigar"]):
        profile["occupation"] = profile["occupation"] or "artisan"
    if any(w in q for w in ["fish", "machli", "matsya"]):
        profile["occupation"] = profile["occupation"] or "fisherman"
    if any(w in q for w in ["dairy", "doodh", "cow", "gay", "bhains", "poultry", "murgi"]):
        profile["occupation"] = profile["occupation"] or "dairy"
    if any(w in q for w in ["gaon", "village", "rural", "gram", "dehat"]):
        profile["location_type"] = "rural"
    if any(w in q for w in ["sheher", "shahar", "city", "urban", "mumbai", "delhi", "chennai"]):
        profile["location_type"] = "urban"
    for st, keys in {
        "Madhya Pradesh": ["madhya pradesh", "mp ", "bhopal", "indore"],
        "Tamil Nadu": ["tamil", "chennai", "madurai"],
        "West Bengal": ["bengal", "kolkata", "bangla"],
        "Maharashtra": ["maharashtra", "mumbai", "pune", "marathi"],
        "Uttar Pradesh": ["uttar pradesh", "up ", "lucknow"],
        "Bihar": ["bihar", "patna"],
        "Rajasthan": ["rajasthan", "jaipur"],
    }.items():
        if any(k in q for k in keys):
            profile["state"] = st
            break
    if re.search(r"\bsc\b", q) or "scheduled caste" in q or "dalit" in q:
        profile["caste"] = "sc"
    if re.search(r"\bst\b", q) or "tribe" in q or "adivasi" in q:
        profile["caste"] = "st"
    if "obc" in q or "backward" in q:
        profile["caste"] = "obc"
    if any(w in q for w in ["widow", "vidhwa"]):
        profile["is_widow"] = True
    if any(w in q for w in ["divyang", "viklang", "disab", "handicap", "wheelchair"]):
        profile["has_disability"] = True
    if any(w in q for w in ["bache", "bacha", "children", "kids", "beti", "beta", "child"]):
        profile["has_children"] = True
    m3 = re.search(r"(\d+)\s*(bache|bacha|children|kids|bacche)", q)
    if m3:
        try:
            profile["family_size"] = int(m3.group(1)) + 2
        except Exception:
            pass
    mi = re.search(r"(income|kamai|salary|vetan)[^\d]*(\d+)", q)
    if mi:
        try:
            profile["income_annual"] = int(mi.group(2))
        except Exception:
            pass
    return profile


def score_scheme(scheme: dict, profile: dict):
    crit = scheme.get("eligibility_criteria", {})
    score = 0.5
    reasons = []
    q = profile.get("raw_query", "").lower()
    # hard filters
    age = profile.get("age")
    if age is not None:
        if crit.get("min_age") is not None and age < crit["min_age"]:
            return 0.0, "age below minimum"
        if crit.get("max_age") is not None and age > crit["max_age"]:
            return 0.0, "age above maximum"
    g = profile.get("gender")
    cg = (crit.get("gender") or "any").lower()
    if g and cg != "any" and g != cg:
        # allow female-specific to pass only for female; male queries fail female schemes
        return 0.0, "gender mismatch"
    # caste
    pc = profile.get("caste")
    # scheme caste field may be "sc,st" etc.
    sc_caste = str(crit.get("caste") or "any").lower()
    if "sc" in sc_caste or "st" in sc_caste or "obc" in sc_caste:
        allowed = [c.strip() for c in sc_caste.split(",")]
        if pc and pc not in allowed:
            return 0.0, "caste mismatch"
        if pc and pc in allowed:
            score += 0.3
            reasons.append("caste match")
    # occupation keyword boost via tags + occupation list
    occ = (profile.get("occupation") or "").lower()
    occ_list = [str(o).lower() for o in (crit.get("occupation") or [])]
    tags = [str(t).lower() for t in scheme.get("tags", [])]
    blob = " ".join(occ_list + tags + [scheme.get("description", "").lower()])
    if profile.get("is_farmer") and any(k in blob for k in ["farm", "kisan", "crop", "agri", "fasal"]):
        score += 0.35
        reasons.append("farmer match")
    if profile.get("is_student") and any(k in blob for k in ["student", "scholar", "school", "college", "education", "padhai"]):
        score += 0.35
        reasons.append("student match")
    if profile.get("is_widow") and any(k in blob for k in ["widow", "vidhwa"]):
        score += 0.4
        reasons.append("widow match")
    if profile.get("has_disability") and any(k in blob for k in ["disab", "divyang", "viklang"]):
        score += 0.4
        reasons.append("disability match")
    if occ and occ in blob:
        score += 0.25
        reasons.append("occupation match")
    # tag overlap with query tokens
    qtokens = set(re.findall(r"[a-z\u0900-\u097f]{3,}", q))
    overlap = len(qtokens & set(tags)) + len([t for t in tags if t in q])
    score += min(0.3, overlap * 0.1)
    # location
    loc = crit.get("location")
    if profile.get("location_type") and loc and loc != "any" and profile["location_type"] == loc:
        score += 0.1
        reasons.append("location match")
    if g == "female" and any(k in blob for k in ["women", "mahila", "girl", "beti", "mother", "maternity"]):
        score += 0.15
        reasons.append("women-focused")
    if not reasons:
        # generic fallback: small boost if query mentions health/housing etc.
        for key in ["health", "hospital", "house", "ghar", "loan", "pension", "ration", "water"]:
            if key in q and key in blob:
                score += 0.15
                reasons.append(f"{key} match")
                break
    return min(1.0, score), "; ".join(reasons) or "general match"


def rank_schemes(schemes: list, profile: dict, top_k: int = 5) -> list:
    scored = []
    for s in schemes:
        sc, reason = score_scheme(s, profile)
        if sc > 0.35:
            scored.append((sc, reason, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for sc, reason, s in scored[:top_k]:
        out.append({"score": round(sc, 3), "match_reason": reason, "scheme": s})
    return out
