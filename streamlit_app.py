# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from io import BytesIO
from brand_matching_system import BrandMatchingSystem
from database import SessionLocal, Synonym, Keyword, MasterProduct

st.set_page_config(page_title="2026 브랜드 매칭 시스템", layout="wide")

if 'match_state' not in st.session_state:
    st.session_state.match_state = {'completed': False, 'final_df': None, 'failed_products': [], 'total': 0, 'success': 0, 'fail': 0}

with st.sidebar:
    st.title("⚙️ 2026 시스템")
    menu = st.radio("메뉴", ["✅ 발주서 자동 매칭", "📚 동의어/키워드 관리", "📊 DB 연동 상태"])
    if st.button("🗑️ 초기화"):
        st.session_state.match_state['completed'] = False
        st.rerun()

@st.cache_resource
def load_engine(): return BrandMatchingSystem()
engine = load_engine()

if menu == "✅ 발주서 자동 매칭":
    st.title("🚀 발주서 자동 매칭")
    files = st.file_uploader("엑셀 파일", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)
    if files and st.button("🏁 매칭 시작", use_container_width=True):
        all_data = []
        for f in files:
            df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
            if not df.empty: all_data.append(engine.convert_sheet1_to_sheet2(df))
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            status_text = st.empty()
            prog_bar = st.progress(0)
            def update(c, t):
                prog_bar.progress(c/t)
                status_text.text(f"⏳ 진행 중: {c} / {t} 건 처리 완료 ({(c/t)*100:.1f}%)")
            final, failed = engine.process_matching(combined, progress_callback=update)
            st.session_state.match_state.update({'final_df': final, 'failed_products': failed, 'completed': True, 'total': len(final), 'success': len(final)-len(failed), 'fail': len(failed)})
            st.rerun()

    if st.session_state.match_state['completed']:
        s = st.session_state.match_state
        st.success("✅ 매칭이 완료되었습니다!")
        c1, c2, c3 = st.columns(3)
        c1.metric("총 발주 건수", f"{s['total']}건")
        c2.metric("매칭 성공", f"{s['success']}건", delta=f"{(s['success']/s['total'])*100:.1f}%", delta_color="normal")
        c3.metric("매칭 실패", f"{s['fail']}건", delta=f"-{(s['fail']/s['total'])*100:.1f}%", delta_color="inverse")
        
        st.dataframe(s['final_df'].head(100))
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            s['final_df'].to_excel(writer, index=False, sheet_name='매칭결과')
            if s['failed_products']: pd.DataFrame(s['failed_products']).to_excel(writer, index=False, sheet_name='실패추천')
        st.download_button("📥 결과 엑셀 다운로드", data=out.getvalue(), file_name="매칭완료.xlsx", use_container_width=True)

elif menu == "📚 동의어/키워드 관리":
    st.title("📚 관리")
    t1, t2 = st.tabs(["동의어", "키워드"])
    with t1:
        with st.form("syn_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            std = col1.text_input("기준 단어(정답)")
            syn = col2.text_input("동의어(오타)")
            c1, c2, c3 = st.columns(3)
            b, p, o = c1.checkbox("브랜드", True), c2.checkbox("상품명", True), c3.checkbox("옵션", False)
            exact = st.radio("방식", ["부분포함", "완전일치"]) == "완전일치"
            if st.form_submit_button("등록") and std and syn:
                db = SessionLocal()
                db.add(Synonym(standard_word=std, synonym_word=syn, apply_brand=b, apply_product=p, apply_option=o, is_exact_match=exact))
                db.commit(); db.close(); st.cache_resource.clear(); st.success("등록완료"); st.rerun()
    with t2:
        with st.form("kw_form", clear_on_submit=True):
            kw = st.text_input("제외 키워드")
            if st.form_submit_button("등록") and kw:
                db = SessionLocal(); db.add(Keyword(keyword_text=kw)); db.commit(); db.close(); st.cache_resource.clear(); st.success("등록완료"); st.rerun()

elif menu == "📊 DB 연동 상태":
    st.title("📊 마스터 DB")
    if engine.brand_data is not None: st.success(f"🟢 연결됨 ({len(engine.brand_data):,}건)")
    with st.form("db_search"):
        q = st.text_input("🔍 검색어 입력 (브랜드/상품명)", placeholder="엔터를 치면 검색 결과가 유지됩니다")
        if st.form_submit_button("검색") or q:
            res = engine.brand_data[engine.brand_data['브랜드'].str.contains(q, na=False, case=False) | engine.brand_data['상품명'].str.contains(q, na=False, case=False)]
            st.write(f"결과: {len(res)}건"); st.dataframe(res, use_container_width=True)
