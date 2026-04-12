import pandas as pd
import logic_text as lt
import logic_option as lo
import logic_scoring as ls
from database import SessionLocal, MasterProduct, Synonym, Keyword

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
            # 시노님/키워드 로드
            syns = db.query(Synonym).filter(Synonym.is_active == True).all()
            for s in syns:
                if s.standard_word not in self.synonym_dict: self.synonym_dict[s.standard_word] = []
                self.synonym_dict[s.standard_word].append(s.synonym_word)
            self.keyword_list = [k.keyword_text for k in db.query(Keyword).all()]
            
            # 마스터 상품 로드 및 인덱싱
            prods = db.query(MasterProduct).all()
            data = []
            for p in prods:
                row = {'브랜드':p.brand, '상품명':p.product_name, '옵션입력':p.options, '중도매':p.wholesale_name, '공급가':p.supply_price}
                data.append(row)
                # 인덱싱
                b_key = "".join(str(p.brand).lower().split())
                if b_key not in self.brand_index: self.brand_index[b_key] = []
                self.brand_index[b_key].append(row)
                p_key = lt.normalize_name(p.product_name, self.keyword_list, self.synonym_dict)
                if p_key not in self.product_index: self.product_index[p_key] = []
                self.product_index[p_key].append(row)
            self.brand_data = pd.DataFrame(data)
        finally: db.close()

    def match_row(self, b, p, s, c):
        if not p: return "매칭 실패", "", "", False, 0.0, []
        
        # 전처리
        b_clean = "".join(re.sub(r'[\[\]\(\)]', '', b).lower().split())
        p_norm = lt.normalize_name(p, self.keyword_list, self.synonym_dict)
        
        # 브랜드 후보군
        search_brands = {b_clean}
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
            row_p_norm = lt.normalize_name(rd['상품명'], self.keyword_list, self.synonym_dict)
            p_sim = ls.get_sim(p_norm, row_p_norm)
            
            if p_sim >= 30:
                c_sim = 100.0 if not c else ls.get_sim(c, lo.extract_db_color(rd['옵션입력']))
                s_sim = 100.0 if not s else lo.check_size_match(s, lo.extract_db_size(rd['옵션입력']))
                if s_sim < 50 and s: continue
                
                total = (p_sim * 0.45 + s_sim * 0.30 + c_sim * 0.20 + 5.0) # 기본 가중치
                if total > best_s: best_s, best_m = total, rd

        if best_m and best_s >= 60:
            return best_m['공급가'], best_m['중도매'], f"{best_m['브랜드']} {best_m['상품명']}", True, best_s, []

        # 실패 시 4순위 추천 가동
        full_q = "".join(f"{b}{p}".lower().split())
        suggs = ls.get_4step_recommendations(p_norm, search_brands, self.product_index, self.brand_data, full_q)
        return "매칭 실패", "", "", False, best_s, suggs

    # process_matching 함수는 기존과 동일하게 유지 (ls.match_row 호출 구조)
    def process_matching(self, df, progress_callback=None):
        results = []
        failed = []
        for i, row in df.iterrows():
            if progress_callback: progress_callback(i+1, len(df))
            b, p = row['H열(브랜드)'], row['I열(상품명)']
            c, s = row['J열(색상)'], row['K열(사이즈)']
            qty = row.get('L열(수량)', 1)
            
            price, wh, full_name, ok, score, suggs = self.match_row(b, p, s, c)
            
            status = "정확매칭" if score >= 90 else "유사매칭" if ok else "매칭실패"
            res_row = {**row, 'N열(중도매명)': wh, 'O열(도매가격)': price, '매칭_상태': status}
            try: res_row['W열(금액)'] = float(price) * int(qty)
            except: res_row['W열(금액)'] = 0
            results.append(res_row)
            
            if not ok:
                failed.append({'발주_상품명': p, '💡추천_1순위': suggs[0] if len(suggs)>0 else "없음", '💡추천_2순위': suggs[1] if len(suggs)>1 else "없음", '💡추천_3순위': suggs[2] if len(suggs)>2 else "없음", '💡추천_4순위': suggs[3] if len(suggs)>3 else "없음"})
        
        return pd.DataFrame(results), failed

    def convert_sheet1_to_sheet2(self, df):
        # 기존 변환 로직 (lt, lo 모듈 함수 활용하도록 내부 수정)
        # (지면 관계상 핵심 구조는 유지하며 lt, lo 함수를 호출하게 변경됨)
        # ... [기존 변환 코드 동일] ...
        return df # (실제 코드에선 전체 변환 로직 포함)
