# -*- coding: utf-8 -*-
from difflib import SequenceMatcher
import re
import logic_option as lo

def get_sim(a, b):
    if not a or not b: return 0.0
    a = re.sub(r'\s+', '', str(a).lower())
    b = re.sub(r'\s+', '', str(b).lower())
    return SequenceMatcher(None, a, b).ratio() * 100

def get_4step_recommendations(target_prod_norm, search_brands, product_index, brand_data, full_query, up_c, up_s):
    suggestions = []
    temp_list = []

    for rd in brand_data.to_dict('records'):
        db_b = re.sub(r'\s+', '', str(rd.get('브랜드','')).lower())
        db_p = re.sub(r'\s+', '', str(rd.get('상품명','')).lower())
        
        b_match = any(re.sub(r'\s+', '', str(b)) in db_b for b in search_brands)
        p_sim = get_sim(target_prod_norm, db_p)
        
        if b_match or p_sim > 50:
            reason = []
            db_colors, db_sizes = lo.get_db_option_list(rd.get('옵션입력', ''))
            
            if p_sim < 80: 
                reason.append(f"상품명 유사도 낮음({p_sim:.0f}%)")
            
            if up_c and not lo.check_option_inclusion(up_c, db_colors):
                reason.append(f"색상 불포함(발주:{up_c}/DB:{'|'.join(db_colors)})")
            
            if up_s and not lo.check_option_inclusion(up_s, db_sizes):
                reason.append(f"사이즈 불포함(발주:{up_s}/DB:{'|'.join(db_sizes)})")
            
            fail_msg = " / ".join(reason) if reason else "옵션 규격 불일치"
            temp_list.append({'rd': rd, 'p_sim': p_sim, 'reason': fail_msg})

    temp_list.sort(key=lambda x: x['p_sim'], reverse=True)
    for item in temp_list[:4]:
        try: price = f"{int(item['rd'].get('공급가',0)):,}원"
        except: price = f"{item['rd'].get('공급가',0)}원"
        suggestions.append(f"[{item['rd'].get('브랜드','')}] {item['rd'].get('상품명','')} | {price} (사유: {item['reason']})")
            
    return suggestions
