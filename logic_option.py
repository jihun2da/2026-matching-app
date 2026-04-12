# -*- coding: utf-8 -*-
import re

def parse_options(option_text):
    """발주서의 혼합 옵션 텍스트에서 색상과 사이즈를 분리합니다."""
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
    """DB의 색상{아이|퍼플}//사이즈{90|100} 규격을 리스트로 분리합니다."""
    if not db_options_raw: return [], []
    
    colors = []
    sizes = []
    
    # // 기호로 색상과 사이즈 구역 분리
    parts = str(db_options_raw).split("//")
    for part in parts:
        if "색상{" in part:
            match = re.search(r"색상\{([^}]*)\}", part)
            if match:
                colors = [c.strip().lower() for c in match.group(1).split("|") if c.strip()]
        elif "사이즈{" in part:
            match = re.search(r"사이즈\{([^}]*)\}", part)
            if match:
                sizes = [s.strip().lower() for s in match.group(1).split("|") if s.strip()]
                
    return colors, sizes

def check_option_inclusion(input_val, db_list):
    """입력된 옵션이 DB 리스트 중 하나를 포함하고 있는지 확인합니다."""
    if not input_val: return True # 입력이 없으면 패스
    if not db_list: return False
    
    target = str(input_val).strip().lower()
    for item in db_list:
        # DB 옵션 항목이 발주서 옵션에 포함되거나 그 반대인 경우 100% 일치로 간주
        if item in target or target in item:
            return True
    return False

def normalize_size(size):
    if not size: return ""
    s = str(size).strip().upper()
    s = re.sub(r'([0-9]+)호', r'\1', s)
    return s.replace('-', '~')

# 기존 호환성을 위해 유지되는 함수 (추가 로직)
def extract_db_color(text):
    c, _ = get_db_option_list(text)
    return " ".join(c)

def extract_db_size(text):
    _, s = get_db_option_list(text)
    return " ".join(s)

def check_size_match(up_size, db_pattern):
    # 포함 로직으로 대체 사용 가능하도록 100/0 반환
    _, db_sizes = get_db_option_list(db_pattern)
    if check_option_inclusion(up_size, db_sizes):
        return 100.0
    return 0.0
