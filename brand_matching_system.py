# -*- coding: utf-8 -*-
import pandas as pd
import re
import logging
from typing import List, Dict, Tuple
from difflib import SequenceMatcher

import streamlit as st
from database import SessionLocal, MasterProduct, Synonym, Keyword

logger = logging.getLogger(__name__)

class BrandMatchingSystem:
    def __init__(self):
        self.brand_data = None
        self.keyword_list = []
        self.synonym_dict = {}
        self._normalized_cache = {}
        self._compiled_patterns = {}
        self._similarity_cache = {}
        self.brand_index = {}
        
        self.load_synonyms_from_db()
        self.load_keywords_from_db()
        self.load_brand_data_from_db()
        self._precompile_patterns()

    def _precompile_patterns(self):
        patterns = {
            'special_chars': r'[^\w\s가-힣]',
            'color_keywords': r'(?:색상|컬러|Color)',
            'size_keywords': r'(?:사이즈|Size)',
            'slash_pattern': r'^([^/]+)/([^/]+)$',
            'dash_pattern': r'^([^-]+)-([^-]+)$',
            'size_check': r'[0-9]|[SMLX]',
            'exact_size': r'^[SMLX]$|^[0-9]+$',
        }
        for name, pattern in patterns.items():
            self._compiled_patterns[name] = re.compile(pattern, re.IGNORECASE)

    def load_synonyms_from_db(self):
        db = SessionLocal()
        try:
            synonyms = db.query(Synonym).filter(Synonym.is_active == True).all()
            self.synonym_dict = {}
            for syn in synonyms:
                if syn.standard_word not in self.synonym_dict:
                    self.synonym_dict[syn.standard_word] = []
                self.synonym_dict[syn.standard_word].append(syn.synonym_word)
        finally:
            db.close()

    def load_keywords_from_db(self):
        db = SessionLocal()
        try:
            keywords = db.query(Keyword).all()
            self.keyword_list = list(set([k.keyword_text for k in keywords]))
            self.keyword_list.sort(key=len, reverse=True) 
        finally:
            db.close()

    def load_brand_data_from_db(self):
        db = SessionLocal()
        try:
            products = db.query(MasterProduct).all()
            data = []
            for p in products:
                data.append({
                    '브랜드': p.brand,
                    '상품명': p.product_name,
                    '옵션입력': p.options,
                    '중도매': p.wholesale_name,
                    '공급가': p.supply_price
                })
            self.brand_data = pd.DataFrame(data)
            self._build_brand_index()
        finally:
            db.close()

    def _build_brand_index(self):
        if self.brand_data is None or self.brand_data.empty:
            self.brand_index = {}
            return
        
        self.brand_index = {}
        for row_dict in self.brand_data.to_dict('records'):
            brand = str(row_dict.get('브랜드', '')).strip().lower()
            brand_clean = re.sub(r'[\[\]\(\)]', '', brand).strip()
            brand_clean = re.sub(r'\s+', '', brand_clean)
            if brand_clean and brand_clean != 'nan':
                if brand_clean not in self.brand_index:
                    self.brand_index[brand_clean] = []
                self.brand_index[brand_clean].append(row_dict)

    def extract_third_word_from_address(self, address: str) -> str:
        if not address or pd.isna(address): return ""
        words = str(address).strip().split()
        if len(words) >= 3: return words[2]
        return ""

    def remove_size_patterns_from_brand(self, brand_name: str) -> str:
        if not brand_name: return brand_name
        result = re.sub(r'\([^)]*[~-][^)]*\)', '', brand_name)
        result = re.sub(r'\*[^*]*[~-][^*]*\*', '', result)
        return re.sub(r'\s+', ' ', result).strip()

    def remove_front_parentheses_from_product(self, product_name: str) -> str:
        if not product_name: return product_name
        return re.sub(r'^\s*\([^)]*\)\s*', '', product_name).strip()

    def remove_keywords_from_product(self, product_name: str) -> str:
        if not product_name or not self.keyword_list: return product_name
        result = product_name
        for keyword in self.keyword_list:
            if not keyword: continue
            cleaned_keyword = keyword.strip()
            if cleaned_keyword.startswith('*') and cleaned_keyword.endswith('*'):
                inner = cleaned_keyword[1:-1]
                pat1 = r'\(' + re.escape(inner).replace(r'\~', r'[~-]') + r'\)'
                pat2 = r'\*' + re.escape(inner).replace(r'\~', r'[~-]') + r'\*'
                result = re.sub(pat1, '', result, flags=re.IGNORECASE)
                result = re.sub(pat2, '', result, flags=re.IGNORECASE)
            elif cleaned_keyword.startswith('(') and cleaned_keyword.endswith(')'):
                inner = cleaned_keyword[1:-1]
                pat = r'\(' + re.escape(inner) + r'\)'
                result = re.sub(pat, '', result, flags=re.IGNORECASE)
            else:
                pat = r'\(' + re.escape(cleaned_keyword) + r'\)'
                result = re.sub(pat, '', result, flags=re.IGNORECASE)
                try: result = re.sub(r'\b' + re.escape(cleaned_keyword) + r'\b', '', result, flags=re.IGNORECASE)
                except: result = re.sub(re.escape(cleaned_keyword), '', result, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', result).strip()

    def parse_options(self, option_text: str) -> tuple:
        if not option_text or pd.isna(option_text) or str(option_text).strip().lower() == 'nan': return "", ""
        option_text = str(option_text).strip()
        color, size = "", ""
        color_keywords = self._compiled_patterns['color_keywords']
        size_keywords = self._compiled_patterns['size_keywords']
        
        c_m1 = re.search(color_keywords.pattern + r'\s*=\s*([^,/]+?)(?:\s*[,/]|\s*(?:사이즈|Size)|$)', option_text, re.IGNORECASE)
        if c_m1: color = c_m1.group(1).strip()
        s_m1 = re.search(size_keywords.pattern + r'\s*[=:]\s*([^,/]+?)(?:\s*[,/]|$)', option_text, re.IGNORECASE)
        if s_m1: size = s_m1.group(1).strip()
        
        if not color:
            c_m2 = re.search(color_keywords.pattern + r'\s*:\s*([^,/]+?)(?:\s*[,/]|\s*(?:사이즈|Size)|$)', option_text, re.IGNORECASE)
            if c_m2: color = c_m2.group(1).strip()
        if not size:
            s_m2 = re.search(size_keywords.pattern + r'\s*:\s*([^,/]+?)(?:\s*[,/]|$)', option_text, re.IGNORECASE)
            if s_m2: size = s_m2.group(1).strip()
            
        if not color and not size:
            sm = self._compiled_patterns['slash_pattern'].match(option_text.strip())
            if sm:
                if self._compiled_patterns['size_check'].search(sm.group(2).strip()):
                    color, size = sm.group(1).strip(), sm.group(2).strip()
                    
        if not color and not size:
            dm = self._compiled_patterns['dash_pattern'].match(option_text.strip())
            if dm:
                p1, p2 = dm.group(1).strip(), dm.group(2).strip()
                if self._compiled_patterns['exact_size'].match(p1): size, color = p1, p2
                elif self._compiled_patterns['size_check'].search(p2): color, size = p1, p2
                
        if color: color = re.sub(r'\s*[/\\|]+\s*$', '', color).strip()
        if size: size = re.sub(r'\s*[/\\|]+\s*$', '', size).strip()
        return color, size

    # 🌟 [누락 복구] DB 데이터에서 색상, 사이즈를 뽑아내는 함수 복구
    def extract_size(self, text: str) -> str:
        if pd.isna(text): return ""
        m = re.search(r"사이즈\{([^}]*)\}", str(text))
        if m: return m.group(1).strip().lower().replace('|', ' ').replace('\\', ' ')
        return ""

    def extract_color(self, text: str) -> str:
        if pd.isna(text): return ""
        m = re.search(r"색상\{([^}]*)\}", str(text))
        if m: return m.group(1).strip().lower().replace('|', ' ').replace('\\', ' ')
        return ""

    def normalize_size_format(self, size: str) -> str:
        if not size: return ""
        size = size.strip()
        size = re.sub(r'([0-9]+)m\b', r'\1', size, flags=re.IGNORECASE)
        size = re.sub(r'([0-9]+)n\b', r'\1', size, flags=re.IGNORECASE)
        size = re.sub(r'([0-9]+)호\b', r'\1', size)
        size = re.sub(r'([A-Z]+)\s+\(', r'\1(', size)
        match = re.match(r'^([A-Z]+)\s*[\(]?([0-9]+)\s*[-~]\s*([0-9]+)\s*[\)]?$', size)
        if match: return f"{match.group(1)}({match.group(2)}~{match.group(3)})"
        size = size.replace('-', '~')
        return size

    def check_size_match(self, upload_size: str, brand_size_pattern: str) -> float:
        if not upload_size or not brand_size_pattern: return 0.0
        upload_size = self.normalize_size_format(upload_size.strip().upper())
        brand_size_pattern = brand_size_pattern.upper()
        
        if re.search(rf'\[{re.escape(upload_size)}\]', brand_size_pattern): return 100.0
        if upload_size in brand_size_pattern: return 100.0
        
        upload_size_code = upload_size.split('(')[0] if '(' in upload_size else upload_size
        brand_size_codes = re.findall(r'\b([A-Z]+)(?:\d+)?\b', brand_size_pattern)
        if upload_size_code in brand_size_codes: return 100.0
        return 0.0

    def calculate_similarity(self, str1: str, str2: str) -> float:
        if not str1 or not str2: return 0.0
        str1 = re.sub(r'\s+', '', str1.lower().strip())
        str2 = re.sub(r'\s+', '', str2.lower().strip())
        if str1 == str2: return 100.0
        
        cache_key = (str1, str2)
        if cache_key in self._similarity_cache: return self._similarity_cache[cache_key]
        
        sim = SequenceMatcher(None, str1, str2).ratio() * 100
        self._similarity_cache[cache_key] = sim
        return sim

    def normalize_product_name(self, name: str) -> str:
        if not name or pd.isna(name): return ""
        n = str(name).lower()
        n = re.sub(r'\([^)]*\)|\*[^*]*\*', '', n)
        
        for kw in self.keyword_list:
            if kw: n = n.replace(kw.lower(), '')
            
        for std_word, syn_words in self.synonym_dict.items():
            for syn in syn_words:
                if syn.lower() in n:
                    n = n.replace(syn.lower(), std_word.lower())
                    
        return re.sub(r'\s+', '', n)

    def convert_sheet1_to_sheet2(self, sheet1_df: pd.DataFrame) -> pd.DataFrame:
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
                        sheet2_row['H열(브랜드)'] = self.remove_size_patterns_from_brand(b_part)
                        p_clean = self.remove_front_parentheses_from_product(p_part)
                        sheet2_row['I열(상품명)'] = self.remove_keywords_from_product(p_clean)
                    elif ' ' in e_value:
                        parts = e_value.split(' ', 1)
                        if parts[0].strip():
                            sheet2_row['H열(브랜드)'] = self.remove_size_patterns_from_brand(parts[0].strip())
                            p_clean = self.remove_front_parentheses_from_product(parts[1].strip() if len(parts) > 1 else "")
                            sheet2_row['I열(상품명)'] = self.remove_keywords_from_product(p_clean)
                        else:
                            # 🌟 [오류 B 복구] 브랜드명이 텅 비었을 때 상품명 증발 방지
                            sheet2_row['H열(브랜드)'] = ""
                            c_prod = self.normalize_product_name(e_value)
                            sheet2_row['I열(상품명)'] = e_value if len(c_prod) < 2 else c_prod
                    else:
                        # 🌟 [오류 B 복구] 띄어쓰기 없을 때 무조건 브랜드로 들어가는 것 방지
                        sheet2_row['H열(브랜드)'] = ""
                        sheet2_row['I열(상품명)'] = e_value
            
            if len(sheet1_df.columns) >= 6:
                f_val = str(row.iloc[5]) if pd.notna(row.iloc[5]) else ""
                sheet2_row['J열(색상)'], sheet2_row['K열(사이즈)'] = self.parse_options(f_val)
                
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

    def match_row(self, brand: str, product: str, size: str, color: str) -> Tuple:
        brand, product = str(brand).strip(), str(product).strip()
        
        # 🌟 [오류 A 복구] 상품명만 없어도 매칭 실패 처리 (브랜드는 없어도 통과!)
        if not product: 
            return "매칭 실패", "", "", False, 0.0, []
            
        brand_clean = re.sub(r'[\[\]\(\)]', '', brand).strip().lower()
        brand_clean = re.sub(r'\s+', '', brand_clean)
        
        for std_word, syn_words in self.synonym_dict.items():
            for syn in syn_words:
                syn_clean = re.sub(r'\s+', '', syn.lower())
                if syn_clean and syn_clean in brand_clean:
                    std_clean = re.sub(r'\s+', '', std_word.lower())
                    brand_clean = brand_clean.replace(syn_clean, std_clean)

        normalized_product = self.normalize_product_name(product)
        
        search_brands = set([brand_clean]) if brand_clean else set()
        if brand_clean:
            for std_word, syn_words in self.synonym_dict.items():
                std_word_lower = re.sub(r'\s+', '', std_word.lower())
                syn_words_lower = [re.sub(r'\s+', '', s.lower()) for s in syn_words]
                if brand_clean == std_word_lower or brand_clean in syn_words_lower:
                    search_brands.add(std_word_lower)
                    search_brands.update(syn_words_lower)
        
        candidate_rows = []
        for b in search_brands:
            candidate_rows.extend(self.brand_index.get(b, []))
            
        # 브랜드를 못 찾았거나 브랜드 자체가 없으면 DB 전체를 뒤져서 추천
        if not candidate_rows: 
            fallback_cands = []
            upload_full = re.sub(r'\s+', '', f"{brand}{product}".lower())
            if self.brand_data is not None and not self.brand_data.empty:
                for row_dict in self.brand_data.to_dict('records'):
                    db_full = re.sub(r'\s+', '', f"{str(row_dict.get('브랜드', ''))}{str(row_dict.get('상품명', ''))}".lower())
                    sim = SequenceMatcher(None, upload_full, db_full).ratio() * 100
                    if sim >= 20: fallback_cands.append({'row_dict': row_dict, 'total_sim': sim})
                fallback_cands.sort(key=lambda x: x['total_sim'], reverse=True)
                
            top_2 = []
            for c in fallback_cands[:2]:
                rd = c['row_dict']
                try: price_str = f"{int(rd.get('공급가', 0)):,}원"
                except: price_str = f"{rd.get('공급가', 0)}원"
                top_2.append(f"[{rd.get('브랜드', '')}] {rd.get('상품명', '')} | 도매가: {price_str} ({c['total_sim']:.1f}%)")
            return "매칭 실패", "", "", False, 0.0, top_2

        # 🌟 [오류 C 복구] 브랜드를 찾은 경우: 색상, 사이즈, 상품명 가중치(45/30/20) 정밀 채점
        evaluated_candidates = []
        best_match, best_similarity = None, 0.0

        for row_dict in candidate_rows:
            row_product = self.normalize_product_name(str(row_dict.get('상품명', '')).strip())
            product_similarity = self.calculate_similarity(normalized_product, row_product)
            
            if product_similarity >= 30:
                color_similarity = 100.0
                if color:
                    row_color_pattern = self.extract_color(str(row_dict.get('옵션입력', '')))
                    color_similarity = self.calculate_similarity(color, row_color_pattern) if row_color_pattern else 0.0
                
                size_similarity = 100.0
                if size:
                    row_size_pattern = self.extract_size(str(row_dict.get('옵션입력', '')))
                    size_similarity = self.check_size_match(size, row_size_pattern) if row_size_pattern else 0.0
                    if size_similarity < 50: continue # 사이즈가 다르면 가차없이 탈락!
                
                # 🌟 거대 가중치 채점 공식 부활
                total_similarity = (product_similarity * 0.45 + size_similarity * 0.30 + color_similarity * 0.20 + 50.0 * 0.05)
                if not color and not size: total_similarity = product_similarity
                elif not color: total_similarity = product_similarity * 0.8 + size_similarity * 0.2
                elif not size: total_similarity = product_similarity * 0.8 + color_similarity * 0.2
                
                evaluated_candidates.append({'row_dict': row_dict, 'total_sim': total_similarity})
                if total_similarity > best_similarity:
                    best_similarity = total_similarity
                    best_match = row_dict

        evaluated_candidates.sort(key=lambda x: x['total_sim'], reverse=True)
        top_2 = []
        for c in evaluated_candidates[:2]:
            rd = c['row_dict']
            try: price_str = f"{int(rd.get('공급가', 0)):,}원"
            except: price_str = f"{rd.get('공급가', 0)}원"
            top_2.append(f"[{rd.get('브랜드', '')}] {rd.get('상품명', '')} | 도매가: {price_str} ({c['total_sim']:.1f}%)")

        if best_match and best_similarity >= 60:
            공급가 = best_match.get('공급가', 0)
            중도매 = best_match.get('중도매', '')
            브랜드상품명 = f"{best_match.get('브랜드', '')} {best_match.get('상품명', '')}"
            return 공급가, 중도매, 브랜드상품명, True, best_similarity, top_2

        return "매칭 실패", "", "", False, best_similarity, top_2

    def process_matching(self, sheet2_df: pd.DataFrame, progress_callback=None) -> Tuple[pd.DataFrame, List[Dict]]:
        if sheet2_df.empty: return sheet2_df, []

        total_rows = len(sheet2_df)
        failed_products = []
        
        results_n = []
        results_o = []
        results_w = []
        results_status = []
        
        for index, row in sheet2_df.iterrows():
            if progress_callback:
                progress_callback(index + 1, total_rows)

            brand = str(row.get('H열(브랜드)', '')).strip()
            product = str(row.get('I열(상품명)', '')).strip()
            size = str(row.get('K열(사이즈)', '')).strip()
            color = str(row.get('J열(색상)', '')).strip()
            quantity = row.get('L열(수량)', 1)

            공급가, 중도매, 브랜드상품명, success, sim_score, suggestions = self.match_row(brand, product, size, color)

            if success and 공급가 != "매칭 실패":
                results_n.append(중도매)
                results_o.append(공급가)
                results_status.append("정확매칭" if sim_score >= 90 else "유사매칭")
                try: results_w.append(float(공급가) * int(quantity))
                except: results_w.append(0)
            else:
                results_n.append("")
                results_o.append(0)
                results_w.append(0)
                results_status.append("매칭실패")
                
                failed_products.append({
                    '발주_브랜드': brand, 
                    '발주_상품명': product, 
                    '옵션(색상/사이즈)': f"{color} / {size}", 
                    '💡추천상품_1순위': suggestions[0] if len(suggestions) > 0 else "추천 없음",
                    '💡추천상품_2순위': suggestions[1] if len(suggestions) > 1 else "추천 없음"
                })

        sheet2_df['N열(중도매명)'] = results_n
        sheet2_df['O열(도매가격)'] = results_o
        sheet2_df['W열(금액)'] = results_w
        sheet2_df['매칭_상태'] = results_status

        return sheet2_df, failed_products
