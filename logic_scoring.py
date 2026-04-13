# -*- coding: utf-8 -*-
from difflib import SequenceMatcher
import re
import logic_option as lo
import logic_text as lt

def get_sim(a, b):
    if not a or not b: return 0.0
    a = re.sub(r'\s+', '', str(a).lower())
    b = re.sub(r'\s+', '', str(b).lower())
    return SequenceMatcher(None, a, b).ratio() * 100

def get_4step_recommendations(target_prod_norm, search_brands, brand_data, up_c, up_s, keyword_list, synonym_rules):
    suggestions = []
    temp_list = []

    for rd in brand_data.to_dict('records'):
        db_b = re.sub(r'\s+', '', str(rd.get('브랜드','')).lower())
        
        # 🌟 핵심 수정 1: DB 상품명도 키워드와 괄호를 완벽히 벗겨서 순수한 상태로 정규화!
        raw_db_p = rd.get('상품명', '')
        db_p_norm = lt.normalize_name(raw_db_p, keyword_list, synonym_rules, 'product')
        
        b_match = any(re.sub(r'\s+', '', str(b)) in db_b for b in search_brands)
        p_sim = get_sim(target_prod_norm, db_p_norm)
        
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
            
            # 🌟 핵심 수정 2: 브랜드가 일치하면 추천 정렬 점수에 강력한 가중치(+50) 부여!
            sort_score = p_sim + (50.0 if b_match else 0.0)
            
            temp_list.append({
                'rd': rd, 
                'sort_score': sort_score, 
                'reason': fail_msg
            })

    # 가중치가 반영된 최종 점수로 정렬
    temp_list.sort(key=lambda x: x['sort_score'], reverse=True)
    
    for item in temp_list[:4]:
        try: price = f"{int(item['rd'].get('공급가',0)):,}원"
        except: price = f"{item['rd'].get('공급가',0)}원"
        suggestions.append(f"[{item['rd'].get('브랜드','')}] {item['rd'].get('상품명','')} | {price} (사유: {item['reason']})")
            
    return suggestions
