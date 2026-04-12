import streamlit as st
import pandas as pd
from io import BytesIO
from brand_matching_system import BrandMatchingSystem
from database import SessionLocal, Synonym, Keyword, MasterProduct

st.set_page_config(page_title="2026 브랜드 매칭 시스템", layout="wide", initial_sidebar_state="expanded")

if 'match_state' not in st.session_state:
    st.session_state.match_state = {'completed': False, 'final_df': None, 'failed_products': [], 'total_input_rows': 0}
if 'del_syn_target' not in st.session_state: st.session_state.del_syn_target = None
if 'del_kw_target' not in st.session_state: st.session_state.del_kw_target = None

with st.sidebar:
    st.title("⚙️ 2026 시스템 메뉴")
    st.markdown("---")
    menu = st.radio("작업 메뉴를 선택하세요", ["✅ 발주서 자동 매칭", "📚 동의어/키워드 관리", "📊 DB 연동 상태"])
    st.markdown("---")
    st.info("💡 Tip: 화면을 이동해도 작업 내역은 유지됩니다.")
    if st.button("🗑️ 현재 작업내역 지우기", use_container_width=True):
        st.session_state.match_state['completed'] = False
        st.rerun()

@st.cache_resource
def load_engine(): return BrandMatchingSystem()
engine = load_engine()

# ==========================================
# 🚀 메인 화면 1: 발주서 자동 매칭
# ==========================================
if menu == "✅ 발주서 자동 매칭":
    st.title("🚀 2026 브랜드 매칭 시스템 (통합 매칭 & 기억 유지)")
    st.markdown("---")
    uploaded_files = st.file_uploader("발주 엑셀 파일 업로드 (첫 시트만 추출)", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)

    if uploaded_files:
        if st.button("🏁 통합 매칭 시작", use_container_width=True):
            try:
                dfs = []
                for file in uploaded_files:
                    df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file) 
                    df = df.dropna(how='all') 
                    if not df.empty: dfs.append(engine.convert_sheet1_to_sheet2(df))
                
                if not dfs:
                    st.warning("유효한 데이터가 없습니다.")
                    st.stop()

                combined_sheet2_df = pd.concat(dfs, ignore_index=True)
                total_input_rows = len(combined_sheet2_df)
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                def update_progress(current, total):
                    progress_bar.progress(current / total)
                    status_text.markdown(f"**진행률:** {int((current/total)*100)}% ({current}/{total} 처리 중)")
                
                with st.spinner(f"🤖 매칭 엔진 가동 중..."):
                    final_df, failed_products = engine.process_matching(combined_sheet2_df, progress_callback=update_progress)
                
                st.session_state.match_state['final_df'] = final_df
                st.session_state.match_state['failed_products'] = failed_products
                st.session_state.match_state['completed'] = True
            except Exception as e: st.error(f"오류: {e}")

    if st.session_state.match_state['completed']:
        final_df = st.session_state.match_state['final_df']
        failed_products = st.session_state.match_state['failed_products']
        
        st.success("🎉 매칭 완료!")
        col1, col2, col3 = st.columns(3)
        col1.metric("총 발주 건수", f"{len(final_df)}건")
        col2.metric("매칭 성공", f"{len(final_df)-len(failed_products)}건")
        col3.metric("매칭 실패", f"{len(failed_products)}건")
        
        st.dataframe(final_df.head(50))
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='통합_전체_매칭결과')
            if failed_products: pd.DataFrame(failed_products).to_excel(writer, index=False, sheet_name='실패건_유사상품추천')
        st.download_button("📥 통합 결과 다운로드", data=output.getvalue(), file_name="매칭완료.xlsx")

# ==========================================
# 📚 서브 화면 2: 동의어/키워드 관리 (스마트 표기 추가)
# ==========================================
elif menu == "📚 동의어/키워드 관리":
    st.title("📚 스마트 동의어 및 제외 키워드 관리")
    if st.button("🔄 매칭 엔진 기억 새로고침"):
        st.cache_resource.clear()
        st.success("업데이트 완료!")
        st.rerun()

    tab1, tab2 = st.tabs(["📚 동의어 사전 추가/삭제", "✂️ 제외 키워드 추가/삭제"])
    
    with tab1:
        with st.form("synonym_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1: std_word = st.text_input("기준 단어 (정답)")
            with col2: syn_word = st.text_input("동의어 (오타)")
            
            st.markdown("📍 **어디에 적용하시겠습니까?**")
            c1, c2, c3 = st.columns(3)
            with c1: apply_brand = st.checkbox("☑️ 브랜드", value=True)
            with c2: apply_product = st.checkbox("☑️ 상품명", value=True)
            with c3: apply_option = st.checkbox("☑️ 옵션 (색상/사이즈)", value=False)
            
            match_type = st.radio("⚙️ 치환 강도 조절", ["🟢 부분 포함", "🔴 완전 일치"])
            is_exact = True if "완전 일치" in match_type else False

            if st.form_submit_button("등록하기") and std_word and syn_word:
                if not (apply_brand or apply_product or apply_option): st.error("범위를 선택하세요!")
                else:
                    db = SessionLocal()
                    try:
                        if db.query(Synonym).filter(Synonym.synonym_word == syn_word.strip()).first():
                            st.warning("🚨 이미 등록된 동의어입니다.")
                        else:
                            db.add(Synonym(standard_word=std_word.strip(), synonym_word=syn_word.strip(), apply_brand=apply_brand, apply_product=apply_product, apply_option=apply_option, is_exact_match=is_exact))
                            db.commit()
                            st.success("✅ 등록되었습니다!")
                            st.cache_resource.clear()
                    finally: db.close()

        st.markdown("---")
        db = SessionLocal()
        syns = db.query(Synonym).filter(Synonym.is_active == True).all()
        
        if syns:
            def get_scope_str(s):
                res = []
                if s.apply_brand: res.append("브랜드")
                if s.apply_product: res.append("상품명")
                if s.apply_option: res.append("옵션")
                return ", ".join(res)

            df_syns = pd.DataFrame([{
                "선택": False, 
                "정답": s.standard_word, 
                "오타": s.synonym_word,
                "적용범위": get_scope_str(s),
                "강도": "완전일치" if s.is_exact_match else "부분포함"
            } for s in syns])
            
            edited_df = st.data_editor(df_syns, column_config={"선택": st.column_config.CheckboxColumn("삭제 선택", default=False)}, hide_index=True, use_container_width=True)
            selected = edited_df[edited_df["선택"] == True]
            
            if not selected.empty:
                target = selected.iloc[0]["오타"]
                if st.session_state.del_syn_target != target:
                    if st.button("🗑️ 선택 항목 삭제하기"):
                        st.session_state.del_syn_target = target
                        st.rerun()
                if st.session_state.del_syn_target == target:
                    st.error(f"🚨 정말 [{target}] 삭제하시겠습니까?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ 네, 삭제"):
                            try:
                                to_del = db.query(Synonym).filter(Synonym.synonym_word == target).first()
                                if to_del: db.delete(to_del); db.commit(); st.session_state.del_syn_target = None; st.cache_resource.clear(); st.rerun()
                            finally: pass
                    with c2:
                        if st.button("❌ 취소"): st.session_state.del_syn_target = None; st.rerun()
        db.close()

    with tab2:
        with st.form("keyword_form", clear_on_submit=True):
            new_keyword = st.text_input("제외 키워드 입력")
            if st.form_submit_button("등록") and new_keyword:
                db = SessionLocal()
                try:
                    if not db.query(Keyword).filter(Keyword.keyword_text == new_keyword.strip()).first():
                        db.add(Keyword(keyword_text=new_keyword.strip())); db.commit(); st.success("✅ 등록!")
                        st.cache_resource.clear()
                finally: db.close()

        db = SessionLocal()
        kws = db.query(Keyword).all()
        if kws:
            df_kws = pd.DataFrame([{"선택": False, "키워드": k.keyword_text} for k in kws])
            edited_kw = st.data_editor(df_kws, column_config={"선택": st.column_config.CheckboxColumn("삭제", default=False)}, hide_index=True, use_container_width=True)
            sel_kw = edited_kw[edited_kw["선택"] == True]
            if not sel_kw.empty:
                t_kw = sel_kw.iloc[0]["키워드"]
                if st.session_state.del_kw_target != t_kw:
                    if st.button("🗑️ 삭제"): st.session_state.del_kw_target = t_kw; st.rerun()
                if st.session_state.del_kw_target == t_kw:
                    st.error(f"🚨 [{t_kw}] 삭제?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ 네"):
                            to_del = db.query(Keyword).filter(Keyword.keyword_text == t_kw).first()
                            if to_del: db.delete(to_del); db.commit(); st.session_state.del_kw_target = None; st.cache_resource.clear(); st.rerun()
                    with c2:
                        if st.button("❌ 취소"): st.session_state.del_kw_target = None; st.rerun()
        db.close()

# ==========================================
# 📊 서브 화면 3: DB 상태 
# ==========================================
elif menu == "📊 DB 연동 상태":
    st.title("📊 DB 연동 및 검색")
    if engine.brand_data is not None: st.success(f"🟢 연결됨 (총 {len(engine.brand_data)}건)")
    
    st.markdown("---")
    db_upload_file = st.file_uploader("마스터 DB 업로드", type=['xlsx', 'xls', 'csv'])
    if db_upload_file and st.button("🚀 DB에 추가"):
        with st.spinner("저장 중..."):
            try:
                new_db = pd.read_csv(db_upload_file) if db_upload_file.name.endswith('.csv') else pd.read_excel(db_upload_file)
                db = SessionLocal()
                for _, r in new_db.iterrows():
                    b_val = str(r.get('브랜드', '')).strip()
                    if b_val and b_val != 'nan':
                        db.add(MasterProduct(brand=b_val, product_name=str(r.get('상품명', '')).strip(), options=str(r.get('옵션입력', '')).strip(), wholesale_name=str(r.get('중도매', '')).strip(), supply_price=str(r.get('공급가', '0')).strip()))
                db.commit(); st.success("✅ 성공!"); st.cache_resource.clear()
            finally: db.close()
