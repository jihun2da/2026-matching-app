# -*- coding: utf-8 -*-
from difflib import SequenceMatcher
import re

def get_sim(a, b):
    if not a or not b: return 0.0
    a = re.sub(r'\s+', '', str(a).lower())
    b = re.sub(r'\s+', '', str(b).lower())
    return SequenceMatcher(None, a, b).ratio() * 100

def get_4step_recommendations(target_prod_norm, search_brands, product_index, brand_data, full_query, up_c, up_s):
    from logic_option import extract_db_color, extract_db_size, check_size_match
    suggestions = []
    temp_list = []

    # 전체 DB에서 후보군 탐색
    for rd in brand_data.to_dict('records'):
        db_b = re.sub(r'\s+', '', str(rd.get('브랜드','')).lower())
        db_p = re.sub(r'\s+', '', str(rd.get('상품명','')).lower())
        
        # 브랜드 일치 여부 확인
        b_match = any(re.sub(r'\s+', '', str(b)) in db_b for b in search_brands)
        p_sim = get_sim(target_prod_norm, db_p)
        
        # 브랜드가 같거나 상품명 유사도가 높으면 후보로 등록
        if b_match or p_sim > 50:
            reason = []
            db_c_raw = extract_db_color(rd.get('옵션입력', ''))
            db_s_raw = extract_db_size(rd.get('옵션입력', ''))
            
            # 실패 원인 정밀 분석
            if p_sim < 85: 
                reason.append(f"상품명 유사도 낮음({p_sim:.0f}%)")
            
            # 색상 체크
            if up_c and get_sim(up_c, db_c_raw) < 70:
                reason.append(f"색상 불일치(발주:{up_c}/DB:{db_c_raw})")
            
            # 사이즈 체크 (CON 제품 실패의 주원인 예상)
            if up_s and check_size_match(up_s, db_s_raw) < 50:
                reason.append(f"사이즈 불일치(발주:{up_s}/DB:{db_s_raw})")
            
            fail_msg = " / ".join(reason) if reason else "기타 규격 미달"
            temp_list.append({'rd': rd, 'p_sim': p_sim, 'reason': fail_msg})

    # 유사도 순 정렬 후 상위 4개 포맷팅
    temp_list.sort(key=lambda x: x['p_sim'], reverse=True)
    for item in temp_list[:4]:
        suggestions.append(format_res(item['rd'], item['reason']))
            
    return suggestions

def format_res(rd, desc):
    try: price = f"{int(rd.get('공급가',0)):,}원"
    except: price = f"{rd.get('공급가',0)}원"
    return f"[{rd.get('브랜드','')}] {rd.get('상품명','')} | {price} (사유: {desc})"
