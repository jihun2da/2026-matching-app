# -*- coding: utf-8 -*-
import pandas as pd
import re
from typing import List, Dict, Tuple
import logic_text as lt
import logic_option as lo
import logic_scoring as ls
from database import SessionLocal, MasterProduct, Synonym, Keyword

class BrandMatchingSystem:
    def __init__(self):
        self.brand_data = None
        self.synonym_rules, self.keyword_list = [], []
        self.brand_index, self.product_index = {}, {}
        self.load_data()

    def load_data(self):
        db = SessionLocal()
        try:
            syns = db.query(Synonym).filter(Synonym.is_active == True).all()
            self.synonym_rules = [{'std': s.standard_word.lower(), 'syn': s.synonym_word.lower(), 'scope': [k for k,v in {'brand':s.apply_brand,'product':s.apply_product,'option':s.apply_option}.items() if v], 'exact': s.is_exact_match} for s in syns]
            self.keyword_list = [k.keyword_text for k in db.query(Keyword).all()]
            prods = db.query(MasterProduct).all()
            data = []
            for p in prods:
                row = {'브랜드': p.brand, '상품명': p.product_name, '옵션입력': p.options, '중도매': p.wholesale_name, '공급가': p.supply_price}
                data.append(row)
                b_norm = lt.apply_smart_synonyms(str(p.brand), self.synonym_rules, 'brand')
                b_key = "".join(re.sub(r'[\[\]\(\)]', '', str(b_norm)).lower().split())
                if b_key not in self.brand_index: self.brand_index[b_key] = []
                self.brand_index[b_key].append(row)
                p_key = lt.normalize_name(p.product_name, self.keyword_list, self.synonym_rules, 'product')
                if p_key not in self.product_index: self.product_index[p_key] = []
                self.product_index[p_key].append(row)
            self.brand_data = pd.DataFrame(data)
        finally: db.close()

    def extract_third_word_from_address(self, address: str) -> str:
        words = str(address).strip().split()
        return words[2] if len(words) >= 3 else ""

    def convert_sheet1_to_sheet2(self, sheet1_df: pd.DataFrame) -> pd.DataFrame:
        cols = ['A열(ㅇ)', 'B열(미등록주문)', 'C열(주문일)', 'D열(아이디주문번호)', 'E열(ㅇ)', 'F열(주문자명)', 'G열(위탁자명)', 'H열(브랜드)', 'I열(상품명)', 'J열(색상)', 'K열(사이즈)', 'L열(수량)', 'M열(옵션가)', 'N열(중도매명)', 'O열(도매가격)', 'P열(미송)', 'Q열(비고)', 'R열(이름)', 'S열(전화번호)', 'T열(주소)', 'U열(아이디)', 'V열(배송메세지)', 'W열(금액)']
        rows = []
        for _, r in sheet1_df.iterrows():
            d = {c: "" for c in cols}
            if len(sheet1_df.columns) >= 1: d['C열(주문일)'] = str(r.iloc[0])
            if len(sheet1_df.columns) >= 2: d['D열(아이디주문번호)'] = str(r.iloc[1])
            if len(sheet1_df.columns) >= 3: d['F열(주문자명)'] = str(r.iloc[2])
            if len(sheet1_df.columns) >= 4:
                name, addr = str(r.iloc[3]), str(r.iloc[10]) if len(sheet1_df.columns) >= 11 else ""
                a3 = self.extract_third_word_from_address(addr)
                d['G열(위탁자명)'] = f"{name}({a3})" if a3 else name
            if len(sheet1_df.columns) >= 5:
                raw = str(r.iloc[4]).strip()
                m = re.match(r'^([^)]+\)[^)]*?)\s+(.+)$', raw)
                if m:
                    d['H열(브랜드)'] = lt.remove_size_patterns_from_brand(m.group(1))
                    d['I열(상품명)'] = lt.remove_keywords(lt.remove_front_parentheses(m.group(2)), self.keyword_list)
                elif ' ' in raw:
                    p = raw.split(' ', 1)
                    d['H열(브랜드)'] = lt.remove_size_patterns_from_brand(p[0])
                    d['I열(상품명)'] = lt.remove_keywords(lt.remove_front_parentheses(p[1]), self.keyword_list)
                else: d['I열(상품명)'] = raw
            if len(sheet1_df.columns) >= 6: d['J열(색상)'], d['K열(사이즈)'] = lo.parse_options(str(r.iloc[5]))
            if len(sheet1_df.columns) >= 7:
                try: d['L열(수량)'] = int(r.iloc[6])
                except: d['L열(수량)'] = 1
            rows.append(d)
        return pd.DataFrame(rows, columns=cols)

    def match_row(self, b, p, s, c):
        if not p: return "매칭 실패", "", "", False, 0.0, []
        b_n = lt.apply_smart_synonyms(b, self.synonym_rules, 'brand')
        b_c = "".join(re.sub(r'[\[\]\(\)]', '', b_n).lower().split())
        p_n = lt.normalize_name(p, self.keyword_list, self.synonym_rules, 'product')
        best_m, best_s = None, 0.0
        cands = self.brand_index.get(b_c, [])
        for rd in cands:
            row_p_n = lt.normalize_name(rd.get('상품명', ''), self.keyword_list, self.synonym_rules, 'product')
            p_sim = ls.get_sim(p_n, row_p_n)
            if p_sim >= 80:
                db_c, db_s = lo.get_db_option_list(rd.get('옵션입력', ''))
                up_c_n = lt.apply_smart_synonyms(c, self.synonym_rules, 'option')
                up_s_n = lt.apply_smart_synonyms(s, self.synonym_rules, 'option')
                if lo.check_option_inclusion(up_c_n, db_c) and lo.check_option_inclusion(up_s_n, db_s):
                    score = p_sim * 0.5 + 50.0
                    if score > best_s: best_s, best_m = score, rd
        if best_m and best_s >= 60: return best_m.get('공급가', 0), best_m.get('중도매', ''), f"{best_m.get('브랜드', '')} {best_m.get('상품명', '')}", True, best_s, []
        suggs = ls.get_4step_recommendations(p_n, {b_c}, self.product_index, self.brand_data, "".join(f"{b}{p}".lower().split()), c, s)
        return "매칭 실패", "", "", False, best_s, suggs

    def process_matching(self, sheet2_df, progress_callback=None):
        results, failed = [], []
        for i, row in sheet2_df.iterrows():
            if progress_callback: progress_callback(i + 1, len(sheet2_df))
            b, p, s, c = row.get('H열(브랜드)', ''), row.get('I열(상품명)', ''), row.get('K열(사이즈)', ''), row.get('J열(색상)', '')
            qty = row.get('L열(수량)', 1)
            pr, wh, fn, ok, sc, su = self.match_row(b, p, s, c)
            res = {**row, 'N열(중도매명)': wh if ok else "", 'O열(도매가격)': pr if ok else 0, '매칭_상태': "정확매칭" if sc >= 90 else "유사매칭" if ok else "매칭실패"}
            try: res['W열(금액)'] = float(pr) * int(qty) if ok else 0
            except: res['W열(금액)'] = 0
            results.append(res)
            if not ok: failed.append({'발주_브랜드': b, '발주_상품명': p, '옵션': f"{c}/{s}", '💡추천_1순위': su[0] if len(su)>0 else ""})
        return pd.DataFrame(results), failed
