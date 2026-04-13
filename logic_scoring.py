# -*- coding: utf-8 -*-
from difflib import SequenceMatcher
import re
import logic_option as lo

def get_sim(a, b):
    if not a or not b: return 0.0
    a = re.sub(r'\s+', '', str(a).lower())
    b = re.sub(r'\s+', '', str(b).lower())
    return SequenceMatcher(None, a, b).ratio() * 100

def get_4step_recommendations(target_prod_norm, search_brands, db_records, up_c_norm, up_s_norm, raw_c, raw_s, p_threshold=80):
    suggestions = []
    temp_list = []

    for rd in db_records:
        db_b = re.sub(r'\s+', '', str(rd.get('브랜드','')).lower())
        db_p_norm = rd.get('_p_norm', '') 
        
        b_match = any(re.sub(r'\s+', '', str(b)) in db_b for b in search_brands)
        p_sim = get_sim(target_prod_norm, db_p_norm)
        
        if b_match or p_sim > 50:
            reason = []
            
            db_colors = rd.get('_db_colors', [])
            db_sizes = rd.get('_db_sizes', [])
            
            if p_sim < p_threshold: 
                reason.append(f"상품명 유사도 낮음({p_sim:.0f}%)")
            
            if up_c_norm and not lo.check_option_inclusion(up_c_norm, db_colors):
                raw_db_colors = rd.get('_db_colors_raw', [])
                reason.append(f"색상 불포함(발주:{raw_c}/DB:{'|'.join(raw_db_colors)})")
            
            if up_s_norm and not lo.check_option_inclusion(up_s_norm, db_sizes):
                raw_db_sizes = rd.get('_db_sizes_raw', [])
                reason.append(f"사이즈 불포함(발주:{raw_s}/DB:{'|'.join(raw_db_sizes)})")
            
            fail_msg = " / ".join(reason) if reason else "브랜드 파싱 누락 또는 총점 미달"
            
            sort_score = p_sim + (50.0 if b_match else 0.0)
            
            temp_list.append({
                'rd': rd, 
                'sort_score': sort_score, 
                'reason': fail_msg
            })

    temp_list.sort(key=lambda x: x['sort_score'], reverse=True)
    
    for item in temp_list[:4]:
        try: 
            # 🌟 소수점 가격 크래시 방어 (7000.0 -> 7,000)
            price = f"{int(float(item['rd'].get('공급가',0))):,}원"
        except: 
            price = f"{item['rd'].get('공급가',0)}원"
        suggestions.append(f"[{item['rd'].get('브랜드','')}] {item['rd'].get('상품명','')} | {price} (사유: {item['reason']})")
            
    return suggestions
