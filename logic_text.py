import re

def remove_size_patterns_from_brand(brand_name):
    if not brand_name: return brand_name
    result = re.sub(r'\([^)]*[~-][^)]*\)', '', brand_name)
    result = re.sub(r'\*[^*]*[~-][^*]*\*', '', result)
    return re.sub(r'\s+', ' ', result).strip()

def remove_front_parentheses(product_name):
    if not product_name: return product_name
    return re.sub(r'^\s*\([^)]*\)\s*', '', product_name).strip()

def remove_keywords(product_name, keyword_list):
    if not product_name or not keyword_list: return product_name
    result = product_name
    for kw in keyword_list:
        if not kw: continue
        cleaned_kw = kw.strip()
        # 괄호나 별표 패턴 대응
        pat = r'[\(\*]' + re.escape(cleaned_kw.strip('(* )')) + r'[\)\*]'
        result = re.sub(pat, '', result, flags=re.IGNORECASE)
        result = result.replace(cleaned_kw, '')
    return re.sub(r'\s+', ' ', result).strip()

def normalize_name(name, keyword_list, synonym_dict):
    if not name: return ""
    n = str(name).lower()
    # 1. 제외 키워드 삭제
    n = remove_keywords(n, keyword_list)
    # 2. 동의어 부분 치환 (긴 단어 우선)
    for std, syns in synonym_dict.items():
        for syn in syns:
            if syn.lower() in n:
                n = n.replace(syn.lower(), std.lower())
    return re.sub(r'\s+', '', n)
