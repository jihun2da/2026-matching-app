import re

def parse_options(option_text):
    if not option_text or str(option_text).lower() == 'nan': return "", ""
    text = str(option_text).strip()
    color, size = "", ""
    
    # 컬러/사이즈 키워드 패턴
    c_m = re.search(r'(?:색상|컬러|Color)\s*[=:]\s*([^,/]+)', text, re.I)
    s_m = re.search(r'(?:사이즈|Size)\s*[=:]\s*([^,/]+)', text, re.I)
    
    if c_m: color = c_m.group(1).strip()
    if s_m: size = s_m.group(1).strip()
    
    # 슬래시(/)나 대시(-) 기반 자동 파싱 (키워드 없을 때)
    if not color and not size:
        parts = re.split(r'[/|-]', text)
        if len(parts) >= 2:
            color, size = parts[0].strip(), parts[1].strip()
            
    return color, size

def extract_db_size(text):
    m = re.search(r"사이즈\{([^}]*)\}", str(text))
    return m.group(1).lower().replace('|', ' ') if m else ""

def extract_db_color(text):
    m = re.search(r"색상\{([^}]*)\}", str(text))
    return m.group(1).lower().replace('|', ' ') if m else ""

def normalize_size(size):
    if not size: return ""
    s = size.strip().upper()
    s = re.sub(r'([0-9]+)호', r'\1', s)
    return s.replace('-', '~')

def check_size_match(up_size, db_pattern):
    if not up_size or not db_pattern: return 0.0
    u = normalize_size(up_size)
    d = db_pattern.upper()
    if u in d: return 100.0
    return 0.0
