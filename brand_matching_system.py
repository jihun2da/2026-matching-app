# -*- coding: utf-8 -*-
import pandas as pd
import re
import logging
from typing import List, Dict, Tuple
from difflib import SequenceMatcher
from database import SessionLocal, MasterProduct, Synonym, Keyword

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
            self.synonym_dict = {s.standard_word: [] for s in synonyms}
            for s in synonyms: self.synonym_dict[s.standard_word].append(s.synonym_word)
        finally: db.close()

    def load_keywords_from_db(self):
        db = SessionLocal()
        try:
            keywords = db.query(Keyword).all()
            self.keyword_list = sorted(list(set([k.keyword_text for k in keywords])), key=len, reverse=True)
        finally: db.close()

    def load_brand_data_from_db(self):
        db = SessionLocal()
        try:
            products = db.query(MasterProduct).all()
            data = [{'브랜드': p.brand, '상품명': p.product_name, '옵션입력': p.options, '중도매': p.wholesale_name, '공급가': p.supply_price} for p in products]
            self.brand_data = pd.DataFrame(data)
            self._build_brand_index()
        finally: db.close()

    def _build_brand_index(self):
        self.brand_index = {}
        if self.brand_data is None: return
        for row in self.brand_data.to_dict('records'):
            b_clean = re.sub(r'\s+', '', re.sub(r'[\[\]\(\)]', '', str(row.get('브랜드', '')).lower()))
            if b_clean:
                if b_clean not in self.brand_index: self.brand_index[b_clean] = []
                self.brand_index[b_clean].append(row)

    def normalize_product_name(self, name: str) -> str:
        if not name or pd.isna(name): return ""
        n = str(name).lower()
        n = re.sub(r'\([^)]*\)|\*[^*]*\*', '', n)
        for kw in self.keyword_list: n = n.replace(kw.lower(), '')
        return re.sub(r'\s+', '', n)

    def calculate_similarity(self, s1: str, s2: str) -> float:
        s1, s2 = re.sub(r'\s+', '', s1), re.sub(r'\s+', '', s2)
        return SequenceMatcher(None, s1, s2).ratio() * 100

    def match_row(self, brand: str, product: str, size: str, color: str) -> Tuple:
        brand, product = str(brand).strip(), str(product).strip()
        if not brand or not product: return "매칭 실패", "", "", False, 0.0, []
        
        b_clean = re.sub(r'\s+', '', re.sub(r'[\[\]\(\)]', '', brand.lower()))
        p_norm = self.normalize_product_name(product)
        
        candidates = self.brand_index.get(b_clean, [])
        if not candidates:
            # 브랜드를 못 찾을 경우 전체 DB 유사도 추천
            fallback = []
            up_full = re.sub(r'\s+', '', f"{brand}{product}".lower())
            for rd in self.brand_data.to_dict('records'):
                db_full = re.sub(r'\s+', '', f"{rd['브랜드']}{rd['상품명']}".lower())
                sim = SequenceMatcher(None, up_full, db_full).ratio() * 100
                if sim >= 20: fallback.append({'rd': rd, 'sim': sim})
            fallback.sort(key=lambda x: x['sim'], reverse=True)
            suggestions = [f"[{f['rd']['브랜드']}] {f['rd']['상품명']} | {int(f['rd']['공급가']):,}원 ({f['sim']:.1f}%)" for f in fallback[:2]]
            return "매칭 실패", "", "", False, 0.0, suggestions

        best_m, best_s = None, 0.0
        eval_c = []
        for rd in candidates:
            sim = self.calculate_similarity(p_norm, self.normalize_product_name(rd['상품명']))
            if sim >= 30:
                eval_c.append({'rd': rd, 'sim': sim})
                if sim > best_s: best_s, best_m = sim, rd
        
        eval_c.sort(key=lambda x: x['sim'], reverse=True)
        suggestions = [f"[{e['rd']['브랜드']}] {e['rd']['상품명']} | {int(e['rd']['공급가']):,}원 ({e['sim']:.1f}%)" for e in eval_c[:2]]
        
        if best_m and best_s >= 60:
            return best_m['공급가'], best_m['중도매'], f"{best_m['브랜드']} {best_m['상품명']}", True, best_s, suggestions
        return "매칭 실패", "", "", False, best_s, suggestions

    def process_matching(self, sheet1_df: pd.DataFrame, progress_callback=None) -> Tuple:
        # Sheet2 폼 변환 로직 (기존 코드와 동일하므로 생략하거나 필요한 부분만 요약)
        # 실제 구현시에는 기존 convert_sheet1_to_sheet2 로직이 포함됩니다.
        from brand_matching_system_utils import convert_to_sheet2 # 편의상 분리 가정
        sheet2_df = self.convert_sheet1_to_sheet2(sheet1_df) 
        
        total = len(sheet2_df)
        failed_products = []
        
        # 결과 저장을 위한 리스트
        matches = []
        
        for i, row in sheet2_df.iterrows():
            # 🌟 진행률 보고 (streamlit_app.py에서 넘겨준 함수 호출)
            if progress_callback:
                progress_callback(i + 1, total)
                
            brand, prod = str(row['H열(브랜드)']), str(row['I열(상품명)'])
            color, size = str(row['J열(색상)']), str(row['K열(사이즈)'])
            qty = row.get('L열(수량)', 1)
            
            price, wh, full_name, success, sim, suggestions = self.match_row(brand, prod, size, color)
            
            sheet2_df.at[i, 'N열(중도매명)'] = wh
            sheet2_df.at[i, 'O열(도매가격)'] = price
            sheet2_df.at[i, '매칭_상태'] = "정확매칭" if sim >= 90 else "유사매칭" if success else "매칭실패"
            try: sheet2_df.at[i, 'W열(금액)'] = float(price) * int(qty)
            except: sheet2_df.at[i, 'W열(금액)'] = 0
            
            if not success:
                failed_products.append({
                    '발주_브랜드': brand, '발주_상품명': prod, '옵션': f"{color}/{size}",
                    '💡추천1': suggestions[0] if len(suggestions)>0 else "",
                    '💡추천2': suggestions[1] if len(suggestions)>1 else ""
                })
        
        return sheet2_df, failed_products

    def convert_sheet1_to_sheet2(self, df):
        # 기존에 제공했던 복잡한 변환 로직이 이 자리에 그대로 들어갑니다.
        # (생략: 기존 코드와 동일)
        return pd.DataFrame(columns=['H열(브랜드)','I열(상품명)','J열(색상)','K열(사이즈)','L열(수량)','N열(중도매명)','O열(도매가격)','W열(금액)','매칭_상태'])
