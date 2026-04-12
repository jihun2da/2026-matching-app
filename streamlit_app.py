# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from io import BytesIO
from brand_matching_system import BrandMatchingSystem
from database import SessionLocal, Synonym, Keyword, MasterProduct

st.set_page_config(page_title="2026 브랜드 매칭 시스템", layout="wide")

if 'match_state' not in st.session_state:
    st.session_state.match_state = {'completed': False, 'final_df': None, 'failed_products': [], 'total_input_rows': 0}

with st.sidebar:
    st.title("⚙️ 2026 시스템")
    menu = st.radio("메뉴", ["✅ 발주서 자동 매칭", "📚 동의어/키워드 관리", "📊 DB 연동 상태"])
    if st.button("🗑️ 초기화", use_container_width=True):
        st.session_state.match_state['completed'] = False
        st.rerun()

@st.cache_resource
def load_engine(): return BrandMatchingSystem()
engine = load_engine()

if menu == "✅ 발주서 자동 매칭":
    st.title("🚀 발주서 자동 매칭")
    uploaded_files = st.file_uploader("엑셀 파일", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)
    if uploaded_files and st.button("🏁 매칭 시작", use_container_width=True):
        dfs = []
        for file in uploaded_files:
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file) 
            if not df.empty: dfs.append(engine.convert_sheet1_to_sheet2(df))
        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            prog = st.progress(0)
            final_df, failed = engine.process_matching(combined, progress_callback=lambda c, t: prog.progress(c/t))
            st.session_state.match_state.update({'final_df': final_df, 'failed_products': failed, 'completed': True})
            st.rerun()

    if st.session_state.match_state['completed']:
        st.success("완료!")
        st.dataframe(st.session_state.match_state['final_df'].head(50))
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.match_state['final_df'].to_excel(writer, index=False)
            if st.session_state.match_state['failed_products']: pd.DataFrame(st.session_state.match_state['failed_products']).to_excel(writer, index=False, sheet_name='실패추천')
        st.download_button("📥 다운로드", data=output.getvalue(), file_name="결과.xlsx")

elif menu == "📚 동의어/키워드 관리":
    st.title("📚 관리")
    tab1, tab2 = st.tabs(["동의어", "키워드"])
    with tab1:
        with st.form("syn_form", clear_on_submit=True):
            s1, s2 = st.columns(2)
            std = s1.text_input("정답")
            syn = s2.text_input("오타")
            c1, c2, c3 = st.columns(3)
            b_ok = c1.checkbox("브랜드", True)
            p_ok = c2.checkbox("상품명", True)
            o_ok = c3.checkbox("옵션", False)
            exact = st.radio("방식", ["부분포함", "완전일치"]) == "완전일치"
            if st.form_submit_button("등록") and std and syn:
                db = SessionLocal()
                db.add(Synonym(standard_word=std, synonym_word=syn, apply_brand=b_ok, apply_product=p_ok, apply_option=o_ok, is_exact_match=exact))
                db.commit(); db.close(); st.cache_resource.clear(); st.success("등록됨"); st.rerun()
    with tab2:
        with st.form("kw_form", clear_on_submit=True):
            kw = st.text_input("제외 키워드")
            if st.form_submit_button("등록") and kw:
                db = SessionLocal(); db.add(Keyword(keyword_text=kw)); db.commit(); db.close(); st.cache_resource.clear(); st.success("등록됨"); st.rerun()

elif menu == "📊 DB 연동 상태":
    st.title("📊 마스터 DB")
    if engine.brand_data is not None:
        st.success(f"🟢 연결됨 ({len(engine.brand_data):,}건)")
    
    # 🌟 검색창 엔터 오류 해결: form을 사용하여 엔터 시 자동 전송되도록 구현
    with st.form("search_form"):
        q = st.text_input("🔍 검색어 입력 (브랜드 또는 상품명)", placeholder="엔터를 치면 검색됩니다")
        search_submit = st.form_submit_button("검색 실행")
        
    if q or search_submit:
        df = engine.brand_data.copy()
        res = df[df['브랜드'].str.contains(q, na=False, case=False) | df['상품명'].str.contains(q, na=False, case=False)]
        st.write(f"검색 결과: {len(res)}건")
        st.dataframe(res, use_container_width=True)
    
    with st.expander("📥 신규 DB 업로드"):
        f = st.file_uploader("엑셀")
        if f and st.button("업로드"):
            db_df = pd.read_excel(f)
            db = SessionLocal()
            for _, r in db_df.iterrows():
                db.add(MasterProduct(brand=str(r.get('브랜드','')), product_name=str(r.get('상품명','')), options=str(r.get('옵션입력','')), wholesale_name=str(r.get('중도매','')), supply_price=str(r.get('공급가','0'))))
            db.commit(); db.close(); st.cache_resource.clear(); st.success("완료"); st.rerun()
