# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from io import BytesIO
from brand_matching_system import BrandMatchingSystem
from database import SessionLocal, Synonym, Keyword, MasterProduct

st.set_page_config(page_title="2026 브랜드 매칭 시스템", layout="wide", initial_sidebar_state="expanded")

if 'match_state' not in st.session_state:
    st.session_state.match_state = {
        'completed': False, 'final_df': None, 'failed_products': [],
        'total_count': 0, 'success_count': 0, 'fail_count': 0
    }

with st.sidebar:
    st.title("⚙️ 시스템 설정")
    
    st.markdown("### ⚖️ 매칭 가중치 조절")
    p_w = st.slider("상품명 유사도 가중치", 0.1, 1.0, 0.5, 0.1, help="상품명이 비슷할 때 주는 기본 점수 비율")
    o_w = st.slider("옵션 일치 보너스", 0, 100, 50, 5, help="색상/사이즈가 모두 일치하면 주는 가산점")
    b_w = st.slider("브랜드 일치 보너스", 0, 50, 20, 5, help="브랜드가 정확히 일치할 때 주는 가산점")
    weights = {'p_w': p_w, 'o_w': o_w, 'b_w': b_w}
    
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
    st.title("🚀 2026 브랜드 매칭 시스템")
    st.markdown("---")
    uploaded_files = st.file_uploader("발주 엑셀 파일 업로드", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)

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
                    status_text.markdown(f"**진행률:** {int((current/total)*100)}% ({current}건 / {total}건 처리 중)")
                
                with st.spinner(f"🤖 매칭 엔진 가동 중..."):
                    # 🌟 가중치 파라미터 전달하여 매칭 실행
                    final_df, failed_products = engine.process_matching(combined_sheet2_df, weights, progress_callback=update_progress)
                
                st.session_state.match_state.update({
                    'final_df': final_df,
                    'failed_products': failed_products,
                    'completed': True,
                    'total_count': total_input_rows,
                    'success_count': total_input_rows - len(failed_products),
                    'fail_count': len(failed_products)
                })
                st.rerun()
            except Exception as e: 
                st.error(f"오류: {e}")

    if st.session_state.match_state['completed']:
        s = st.session_state.match_state
        st.success("🎉 매칭 완료!")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("총 발주 건수", f"{s['total_count']}건")
        col2.metric("매칭 성공", f"{s['success_count']}건")
        col3.metric("매칭 실패", f"{s['fail_count']}건")
        
        st.dataframe(s['final_df'].head(50))
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            s['final_df'].to_excel(writer, index=False, sheet_name='통합_전체_매칭결과')
            if s['failed_products']: 
                pd.DataFrame(s['failed_products']).to_excel(writer, index=False, sheet_name='실패건_유사상품추천')
        st.download_button("📥 통합 결과 다운로드", data=output.getvalue(), file_name="매칭완료.xlsx", use_container_width=True)

# ==========================================
# 📚 서브 화면 2: 동의어/키워드 관리 (🌟 증발했던 전체 코드 복구 완료)
# ==========================================
elif menu == "📚 동의어/키워드 관리":
    st.title("📚 스마트 동의어 및 제외 키워드 관리")
    
    tab1, tab2 = st.tabs(["📚 동의어 사전 관리", "✂️ 제외 키워드 관리"])
    
    with tab1:
        st.subheader("➕ 개별 등록")
        with st.form("synonym_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1: std_word = st.text_input("기준 단어 (정답)")
            with col2: syn_word = st.text_input("동의어 (오타)")
            st.markdown("📍 **적용 범위 및 강도**")
            c1, c2, c3, c4 = st.columns(4)
            b_app = c1.checkbox("브랜드", value=True)
            p_app = c2.checkbox("상품명", value=True)
            o_app = c3.checkbox("옵션", value=False)
            is_ex = c4.checkbox("완전일치", value=True)
            if st.form_submit_button("등록하기") and std_word and syn_word:
                db = SessionLocal()
                try:
                    if db.query(Synonym).filter(Synonym.synonym_word == syn_word.strip()).first():
                        st.warning("🚨 이미 등록된 동의어입니다.")
                    else:
                        db.add(Synonym(standard_word=std_word.strip(), synonym_word=syn_word.strip(), apply_brand=b_app, apply_product=p_app, apply_option=o_app, is_exact_match=is_ex))
                        db.commit()
                        st.success("✅ 등록되었습니다!")
                        st.cache_resource.clear()
                        st.rerun()
                finally: db.close()

        st.markdown("---")
        
        st.subheader("📥 엑셀 일괄 등록")
        col_down, col_up = st.columns([1, 2])
        
        with col_down:
            template_df = pd.DataFrame(columns=["기준단어", "동의어", "브랜드적용(O/X)", "상품명적용(O/X)", "옵션적용(O/X)", "완전일치(O/X)"])
            template_df.loc[0] = ["티셔츠", "티", "X", "O", "X", "O"] 
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                template_df.to_excel(writer, index=False)
            st.download_button("📄 업로드 양식 다운로드", data=buffer.getvalue(), file_name="동의어_일괄등록_양식.xlsx", use_container_width=True)
        
        with col_up:
            syn_excel = st.file_uploader("동의어 엑셀 파일을 업로드하세요", type=['xlsx'])
            if syn_excel and st.button("🚀 엑셀 데이터 일괄 저장", use_container_width=True):
                try:
                    df_upload = pd.read_excel(syn_excel)
                    db = SessionLocal()
                    
                    existing_syns = {s.synonym_word for s in db.query(Synonym).all()}
                    count = 0
                    
                    for _, row in df_upload.iterrows():
                        s_word = str(row.get('기준단어', '')).strip()
                        y_word = str(row.get('동의어', '')).strip()
                        
                        if not s_word or not y_word or s_word == 'nan' or y_word == 'nan': continue
                        if y_word in existing_syns: continue
                        
                        db.add(Synonym(
                            standard_word=s_word,
                            synonym_word=y_word,
                            apply_brand=True if str(row.get('브랜드적용(O/X)', '')).upper() == 'O' else False,
                            apply_product=True if str(row.get('상품명적용(O/X)', '')).upper() == 'O' else False,
                            apply_option=True if str(row.get('옵션적용(O/X)', '')).upper() == 'O' else False,
                            is_exact_match=True if str(row.get('완전일치(O/X)', '')).upper() == 'O' else False
                        ))
                        existing_syns.add(y_word)
                        count += 1
                        
                    db.commit()
                    db.close()
                    st.success(f"✅ 중복/에러 없이 총 {count}건의 동의어가 성공적으로 일괄 등록되었습니다!")
                    st.cache_resource.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 오류가 발생했습니다: {e}")

        st.markdown("---")
        
        st.subheader("🗒️ 등록된 동의어 목록")
        db = SessionLocal()
        syns = db.query(Synonym).filter(Synonym.is_active == True).all()
        if syns:
            df_syns = pd.DataFrame([{
                "선택": False, "정답": s.standard_word, "오타": s.synonym_word,
                "브랜드": "O" if s.apply_brand else "X", "상품명": "O" if s.apply_product else "X",
                "옵션": "O" if s.apply_option else "X", "완전일치": "O" if s.is_exact_match else "X"
            } for s in syns])
            edited_df = st.data_editor(df_syns, column_config={"선택": st.column_config.CheckboxColumn("삭제", default=False)}, hide_index=True, use_container_width=True)
            selected = edited_df[edited_df["선택"] == True]
            if not selected.empty:
                if st.button("🗑️ 선택된 동의어 삭제하기"):
                    for target_syn in selected["오타"]:
                        to_del = db.query(Synonym).filter(Synonym.synonym_word == target_syn).first()
                        if to_del: db.delete(to_del)
                    db.commit(); st.cache_resource.clear(); st.rerun()
        db.close()

    with tab2:
        with st.form("keyword_form", clear_on_submit=True):
            new_keyword = st.text_input("제외 키워드 입력")
            if st.form_submit_button("등록") and new_keyword:
                db = SessionLocal()
                try:
                    if not db.query(Keyword).filter(Keyword.keyword_text == new_keyword.strip()).first():
                        db.add(Keyword(keyword_text=new_keyword.strip())); db.commit()
                        st.success("✅ 등록!"); st.cache_resource.clear(); st.rerun()
                finally: db.close()

        db = SessionLocal()
        kws = db.query(Keyword).all()
        if kws:
            df_kws = pd.DataFrame([{"선택": False, "키워드": k.keyword_text} for k in kws])
            edited_kw = st.data_editor(df_kws, column_config={"선택": st.column_config.CheckboxColumn("삭제", default=False)}, hide_index=True, use_container_width=True)
            sel_kw = edited_kw[edited_kw["선택"] == True]
            if not sel_kw.empty:
                if st.button("🗑️ 선택된 키워드 삭제"):
                    for t_kw in sel_kw["키워드"]:
                        to_del = db.query(Keyword).filter(Keyword.keyword_text == t_kw).first()
                        if to_del: db.delete(to_del)
                    db.commit(); st.cache_resource.clear(); st.rerun()
        db.close()

# ==========================================
# 📊 서브 화면 3: DB 상태 (🌟 증발했던 전체 코드 복구 완료)
# ==========================================
elif menu == "📊 DB 연동 상태":
    st.title("📊 마스터 DB 연동 및 검색 관리")
    if engine.brand_data is not None and not engine.brand_data.empty: 
        st.success(f"🟢 AWS DB 연결 완료 (총 {len(engine.brand_data):,}건 데이터)")
    
    with st.form("search_form"):
        search_query = st.text_input("🔍 브랜드 또는 상품명 검색", placeholder="검색어 입력 후 Enter")
        search_submit = st.form_submit_button("검색 실행")
    
    if (search_submit or search_query) and engine.brand_data is not None:
        df_display = engine.brand_data.copy()
        mask = df_display['브랜드'].str.contains(search_query, case=False, na=False) | df_display['상품명'].str.contains(search_query, case=False, na=False)
        st.write(f"**검색 결과:** {len(df_display[mask])}건"); st.dataframe(df_display[mask], use_container_width=True)

    with st.expander("📥 신규 마스터 DB 업로드"):
        db_upload_file = st.file_uploader("마스터 DB 엑셀 파일 업로드", type=['xlsx'])
        if db_upload_file and st.button("🚀 DB에 추가"):
            try:
                new_db = pd.read_excel(db_upload_file)
                db = SessionLocal()
                count = 0
                for _, r in new_db.iterrows():
                    b_val = str(r.get('브랜드','')).strip()
                    if b_val and b_val != 'nan':
                        raw_price = str(r.get('공급가', '0')).replace(',', '').strip()
                        try: p_val = float(raw_price)
                        except ValueError: p_val = 0.0
                            
                        db.add(MasterProduct(
                            brand=b_val, 
                            product_name=str(r.get('상품명','')).strip(), 
                            options=str(r.get('옵션입력','')).strip(), 
                            wholesale_name=str(r.get('중도매','')).strip(), 
                            supply_price=p_val
                        ))
                        count += 1
                db.commit()
                db.close()
                st.success(f"✅ 총 {count}건의 마스터 DB가 성공적으로 업로드되었습니다!")
                st.cache_resource.clear()
                st.rerun()
            except Exception as e: 
                st.error(f"오류: {e}")
