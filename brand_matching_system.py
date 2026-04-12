# -*- coding: utf-8 -*-
import pandas as pd
import re
import logging
from typing import List, Dict, Tuple

import logic_text as lt
import logic_option as lo
import logic_scoring as ls
from database import SessionLocal, MasterProduct, Synonym, Keyword

logger = logging.getLogger(__name__)

class BrandMatchingSystem:
    def __init__(self):
        self.brand_data = None
        self.synonym_dict = {}
        self.keyword_list = []
        self.brand_index = {}
        self.product_index = {}
        self.load_data()

    def load_data(self):
        db = SessionLocal()
        try:
            # 1. 동의어/키워드 로드
            syns = db.query(Synonym).filter(Synonym.is_active == True).all()
            for s in syns:
                if s.standard_word not in self.synonym_dict: 
                    self.synonym_dict[s.standard_word] = []
                self.synonym_dict[s.standard_word].append(s.synonym_word)
            
            self.keyword_list = [k.keyword_text for k in db.query(Keyword).all()]
            
            # 2. 마스터 상품 로드 및 인덱싱 빌드
            prods = db.query(MasterProduct).all()
            data = []
            for p in prods:
                row = {
                    '브랜드': p.brand, 
                    '상품명': p.product_name, 
                    '옵션입력': p.options, 
                    '중도매': p.wholesale_name, 
                    '공급가': p.supply_price
                }
                data.append(row)
                
                # 브랜드 인덱싱
                b_key = "".join(str(p.brand).lower().split())
                if b_key not in self.brand_index: 
                    self.brand_index[b_key] = []
                self.brand_index[b_key].append(row)
                
                # 상품명 100% 인덱싱 (4순위 추천용)
                p_key = lt.normalize_name(p.product_name, self.keyword_list, self.synonym_dict)
                if p_key not in self.product_index: 
                    self.product_index[p_key] = []
                self.product_index[p_key].append(row)
                
            self.brand_data = pd.DataFrame(data)
        finally: 
            db.close()

    def extract_third_word_from_address(self, address: str) -> str:
        if not address or pd.isna(address): return ""
        words = str(address).strip().split()
        if len(words) >= 3: return words[2]
        return ""

    def convert_sheet1_to_sheet2(self, sheet1_df: pd.DataFrame) -> pd.DataFrame:
        # 🌟 [누락 복구 완료] 엑셀 변환 로직 (lt, lo 모듈 적용)
        sheet2_columns = [
            'A열(ㅇ)', 'B열(미등록주문)', 'C열(주문일)', 'D열(아이디주문번호)', 'E열(ㅇ)',
            'F열(주문자명)', 'G열(위탁자명)', 'H열(브랜드)', 'I열(상품명)', 'J열(색상)',
            'K열(사이즈)', 'L열(수량)', 'M열(옵션가)', 'N열(중도매명)', 'O열(도매가격)',
            'P열(미송)', 'Q열(비고)', 'R열(이름)', 'S열(전화번호)', 'T열(주소)',
            'U열(아이디)', 'V열(배송메세지)', 'W열(금액)'
        ]
        if sheet1_df.empty: return pd.DataFrame(columns=sheet2_columns)
        
        sheet2_rows = []
        for i, (idx, row) in enumerate(sheet1_df.iterrows()):
            sheet2_row = {col: "" for col in sheet2_columns}
            
            if len(sheet1_df.columns) >= 1: 
                v = row.iloc[0]
                sheet2_row['C열(주문일)'] = str(int(v)) if pd.notna(v) and isinstance(v, (int, float)) and v == int(v) else str(v) if pd.notna(v) else ""
            if len(sheet1_df.columns) >= 2: 
                v = row.iloc[1]
                sheet2_row['D열(아이디주문번호)'] = str(int(v)) if pd.notna(v) and isinstance(v, (int, float)) and v == int(v) else str(v) if pd.notna(v) else ""
            if len(sheet1_df.columns) >= 3: sheet2_row['F열(주문자명)'] = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
            
            if len(sheet1_df.columns) >= 4:
                name = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
                addr_3rd = self.extract_third_word_from_address(str(row.iloc[10])) if len(sheet1_df.columns) >= 11 and pd.notna(row.iloc[10]) else ""
                sheet2_row['G열(위탁자명)'] = f"{name}({addr_3rd})" if name and addr_3rd else name

            if len(sheet1_df.columns) >= 5:
                e_value = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ""
                if e_value:
                    b_match = re.match(r'^([^)]+\)[^)]*?)\s+(.+)$', e_value)
                    if b_match:
                        b_part = b_match.group(1).strip()
                        p_part = b_match.group(2).strip()
                        sheet2_row['H열(브랜드)'] = lt.remove_size_patterns_from_brand(b_part)
                        p_clean = lt.remove_front_parentheses(p_part)
                        sheet2_row['I열(상품명)'] = lt.remove_keywords(p_clean, self.keyword_list)
                    elif ' ' in e_value:
                        parts = e_value.split(' ', 1)
                        if parts[0].strip():
                            sheet2_row['H열(브랜드)'] = lt.remove_size_patterns_from_brand(parts[0].strip())
                            p_clean = lt.remove_front_parentheses(parts[1].strip() if len(parts) > 1 else "")
                            sheet2_row['I열(상품명)'] = lt.remove_keywords(p_clean, self.keyword_list)
                        else:
                            sheet2_row['H열(브랜드)'] = ""
                            c_prod = lt.normalize_name(e_value, self.keyword_list, self.synonym_dict)
                            sheet2_row['I열(상품명)'] = e_value if len(c_prod) < 2 else c_prod
                    else:
                        sheet2_row['H열(브랜드)'] = ""
                        sheet2_row['I열(상품명)'] = e_value
            
            if len(sheet1_df.columns) >= 6:
                f_val = str(row.iloc[5]) if pd.notna(row.iloc[5]) else ""
                sheet2_row['J열(색상)'], sheet2_row['K열(사이즈)'] = lo.parse_options(f_val)
                
            if len(sheet1_df.columns) >= 7:
                try: sheet2_row['L열(수량)'] = int(row.iloc[6]) if pd.notna(row.iloc[6]) else 1
                except: sheet2_row['L열(수량)'] = 1
                
            if len(sheet1_df.columns) >= 8: sheet2_row['M열(옵션가)'] = str(row.iloc[7]) if pd.notna(row.iloc[7]) else ""
            
            if len(sheet1_df.columns) >= 9:
                name = str(row.iloc[8]) if pd.notna(row.iloc[8]) else ""
                addr_3rd = self.extract_third_word_from_address(str(row.iloc[10])) if len(sheet1_df.columns) >= 11 and pd.notna(row.iloc[10]) else ""
                sheet2_row['R열(이름)'] = f"{name}({addr_3rd})" if name and addr_3rd else name
                
            if len(sheet1_df.columns) >= 10: sheet2_row['S열(전화번호)'] = str(row.iloc[9]) if pd.notna(row.iloc[9]) else ""
            if len(sheet1_df.columns) >= 11: sheet2_row['T열(주소)'] = str(row.iloc[10]) if pd.notna(row.iloc[10]) else ""
            if len(sheet1_df.columns) >= 12: sheet2_row['V열(배송메세지)'] = str(row.iloc[11]) if pd.notna(row.iloc[11]) else ""
            
            sheet2_row['N열(중도매명)'], sheet2_row['O열(도매가격)'], sheet2_row['W열(금액)'] = "", 0, 0
            sheet2_rows.append(sheet2_row)

        return pd.DataFrame(sheet2_rows, columns=sheet2_columns)

    def match_row(self, b: str, p: str, s: str, c: str) -> Tuple:
        if not p: return "매칭 실패", "", "", False, 0.0, []
        
        # 전처리
        b_clean = "".join(re.sub(r'[\[\]\(\)]', '', b).lower().split())
        p_norm = lt.normalize_name(p, self.keyword_list, self.synonym_dict)
        
        # 브랜드 후보군
        search_brands = set([b_clean]) if b_clean else set()
        if b_clean:
            for std, syns in self.synonym_dict.items():
                std_c = "".join(std.lower().split())
                if b_clean == std_c or any("".join(sy.lower().split()) == b_clean for sy in syns):
                    search_brands.add(std_c)
                    search_brands.update("".join(sy.lower().split()) for sy in syns)

        # 채점
        best_m, best_s = None, 0.0
        candidates = []
        for sb in search_brands: candidates.extend(self.brand_index.get(sb, []))
        
        for rd in candidates:
            row_p_norm = lt.normalize_name(rd.get('상품명', ''), self.keyword_list, self.synonym_dict)
            p_sim = ls.get_sim(p_norm, row_p_norm)
            
            if p_sim >= 30:
                c_sim = 100.0 if not c else ls.get_sim(c, lo.extract_db_color(rd.get('옵션입력', '')))
                s_sim = 100.0 if not s else lo.check_size_match(s, lo.extract_db_size(rd.get('옵션입력', '')))
                if s_sim < 50 and s: continue # 사이즈 다르면 탈락!
                
                total = (p_sim * 0.45 + s_sim * 0.30 + c_sim * 0.20 + 5.0) 
                if not c and not s: total = p_sim
                elif not c: total = p_sim * 0.8 + s_sim * 0.2
                elif not s: total = p_sim * 0.8 + c_sim * 0.2
                
                if total > best_s: 
                    best_s, best_m = total, rd

        if best_m and best_s >= 60:
            return best_m.get('공급가', 0), best_m.get('중도매', ''), f"{best_m.get('브랜드', '')} {best_m.get('상품명', '')}", True, best_s, []

        # 실패 시 4순위 추천 가동 (ls 모듈 호출)
        full_q = "".join(f"{b}{p}".lower().split())
        suggs = ls.get_4step_recommendations(p_norm, search_brands, self.product_index, self.brand_data, full_q)
        return "매칭 실패", "", "", False, best_s, suggs

    def process_matching(self, sheet2_df: pd.DataFrame, progress_callback=None) -> Tuple[pd.DataFrame, List[Dict]]:
        if sheet2_df.empty: return sheet2_df, []

        total_rows = len(sheet2_df)
        failed_products = []
        
        results_n = []
        results_o = []
        results_w = []
        results_status = []
        
        for index, row in sheet2_df.iterrows():
            if progress_callback: progress_callback(index + 1, total_rows)

            b = str(row.get('H열(브랜드)', '')).strip()
            p = str(row.get('I열(상품명)', '')).strip()
            s = str(row.get('K열(사이즈)', '')).strip()
            c = str(row.get('J열(색상)', '')).strip()
            qty = row.get('L열(수량)', 1)

            price, wh, full_name, ok, score, suggs = self.match_row(b, p, s, c)

            if ok and price != "매칭 실패":
                results_n.append(wh)
                results_o.append(price)
                results_status.append("정확매칭" if score >= 90 else "유사매칭")
                try: results_w.append(float(price) * int(qty))
                except: results_w.append(0)
            else:
                results_n.append("")
                results_o.append(0)
                results_w.append(0)
                results_status.append("매칭실패")
                
                failed_products.append({
                    '발주_브랜드': b, 
                    '발주_상품명': p, 
                    '옵션(색상/사이즈)': f"{c} / {s}", 
                    '💡추천_1순위': suggs[0] if len(suggs) > 0 else "추천 없음",
                    '💡추천_2순위': suggs[1] if len(suggs) > 1 else "추천 없음",
                    '💡추천_3순위': suggs[2] if len(suggs) > 2 else "추천 없음",
                    '💡추천_4순위': suggs[3] if len(suggs) > 3 else "추천 없음"
                })

        sheet2_df['N열(중도매명)'] = results_n
        sheet2_df['O열(도매가격)'] = results_o
        sheet2_df['W열(금액)'] = results_w
        sheet2_df['매칭_상태'] = results_status

        return sheet2_df, failed_products
