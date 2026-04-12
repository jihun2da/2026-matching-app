# -*- coding: utf-8 -*-
import re

def normalize_for_comparison(val):
    """비교를 위해 공백 제거, 소문자화, 그리고 ~(물결)을 -(하이픈)으로 완벽히 통일합니다."""
    if not val: return ""
    v = str(val).lower().replace(" ", "")
    v = v.replace("~", "-")
    return v

def parse_options(option_text):
    if not option_text or str(option_text).lower() == 'nan': return "", ""
    text = str(option_text).strip()
    color, size = "", ""
    c_m = re.search(r'(?:색상|컬러|Color)\s*[=:]\s*([^,/]+)', text, re.IGNORECASE)
    s_m = re.search(r'(?:사이즈|Size)\s*[=:]\s*([^,/]+)', text, re.IGNORECASE)
    if c_m: color = c_m.group(1).strip()
    if s_m: size = s_m.group(1).strip()
    if not color and not size:
        parts = re.split(r'[/|-]', text)
        if len(parts) >= 2:
            color, size = parts[0].strip(), parts[1].strip()
        else:
            color = text
    return color, size

def get_db_option_list(db_options_raw):
    """DB의 옵션(예: 색상{아이|퍼플}//사이즈{90|100})을 파싱하여 리스트로 반환합니다."""
    if not db_options_raw: return [], []
    colors, sizes = [], []
    parts = str(db_options_raw).split("//")
    for part in parts:
        if "색상{" in part:
            match = re.search(r"색상\{([^}]*)\}", part)
            if match:
                colors = [c.strip() for c in match.group(1).split("|") if c.strip()]
        elif "사이즈{" in part:
            match = re.search(r"사이즈\{([^}]*)\}", part)
            if match:
                sizes = [s.strip() for s in match.group(1).split("|") if s.strip()]
    return colors, sizes

def check_option_inclusion(input_val, db_list):
    """발주서 옵션이 DB 옵션 리스트 중 하나라도 포함하고 있는지 검사합니다."""
    if not input_val: return True
    if not db_list: return False
    target = normalize_for_comparison(input_val)
    for item in db_list:
        db_item = normalize_for_comparison(item)
        if db_item in target or target in db_item:
            return True
    return False

def check_size_match(up_size, db_pattern):
    _, db_sizes = get_db_option_list(db_pattern)
    if check_option_inclusion(up_size, db_sizes):
        return 100.0
    return 0.0

def extract_db_color(text):
    c, _ = get_db_option_list(text)
    return " ".join(c)

def extract_db_size(text):
    _, s = get_db_option_list(text)
    return " ".join(s)
