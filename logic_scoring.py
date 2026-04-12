from difflib import SequenceMatcher
import re

def get_sim(a, b):
    a = re.sub(r'\s+', '', str(a).lower())
    b = re.sub(r'\s+', '', str(b).lower())
    return SequenceMatcher(None, a, b).ratio() * 100

def get_4step_recommendations(target_prod_norm, search_brands, product_index, brand_data, full_query):
    suggestions = []
    exact_both = []
    exact_prod_only = []
    
    if target_prod_norm in product_index:
        for rd in product_index[target_prod_norm]:
            db_b = re.sub(r'\s+', '', str(rd.get('브랜드','')).lower())
            if db_b in search_brands: exact_both.append(rd)
            else: exact_prod_only.append(rd)
            
    for rd in exact_both[:4]:
        suggestions.append(format_res(rd, "✔브랜드+상품명 동일"))
        
    for rd in exact_prod_only:
        if len(suggestions) >= 4 or len([s for s in suggestions if "상품명만" in s]) >= 2: break
        suggestions.append(format_res(rd, "✔상품명만 동일"))
        
    if len(suggestions) < 4:
        fallback = []
        for rd in brand_data.to_dict('records'):
            db_full = re.sub(r'\s+', '', f"{rd.get('브랜드','')}{rd.get('상품명','')}".lower())
            sim = SequenceMatcher(None, full_query, db_full).ratio() * 100
            if sim >= 30: fallback.append({'rd':rd, 'sim':sim})
        fallback.sort(key=lambda x: x['sim'], reverse=True)
        for c in fallback:
            if len(suggestions) >= 4: break
            suggestions.append(format_res(c['rd'], f"{c['sim']:.1f}% 유사"))
            
    return suggestions

def format_res(rd, desc):
    try: price = f"{int(rd.get('공급가',0)):,}원"
    except: price = f"{rd.get('공급가',0)}원"
    return f"[{rd.get('브랜드','')}] {rd.get('상품명','')} | {price} ({desc})"
