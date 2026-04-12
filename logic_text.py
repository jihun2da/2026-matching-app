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
        pat = r'[\(\*]' + re.escape(cleaned_kw.strip('(* )')) + r'[\)\*]'
        result = re.sub(pat, '', result, flags=re.IGNORECASE)
        result = result.replace(cleaned_kw, '')
    return re.sub(r'\s+', ' ', result).strip()

def apply_smart_synonyms(text, rules, target_scope):
    if not text: return text
    n = text.lower()
    for rule in rules:
        if target_scope not in rule['scope']: continue 
        
        syn = rule['syn']
        std = rule['std']
        
        if rule['exact']:
            pat = r'(?<![가-힣a-z0-9])' + re.escape(syn) + r'(?![가-힣a-z0-9])'
            n = re.sub(pat, std, n)
        else:
            if syn in n:
                n = n.replace(syn, std)
    return n

def normalize_name(name, keyword_list, synonym_rules, target_scope="product"):
    if not name: return ""
    n = str(name).lower()
    n = remove_keywords(n, keyword_list)
    n = apply_smart_synonyms(n, synonym_rules, target_scope)
    n = re.sub(r'\([^)]*\)|\*[^*]*\*', '', n)
    return re.sub(r'\s+', '', n)
