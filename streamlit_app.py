import streamlit as st
import pandas as pd
from io import BytesIO
from brand_matching_system import BrandMatchingSystem
from database import SessionLocal, Synonym, Keyword

st.set_page_config(page_title="2026 브랜드 매칭 시스템", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.title("⚙️ 2026 시스템 메뉴")
    st.markdown("---")
    menu = st.radio(
        "작업 메뉴를 선택하세요", 
        ["✅ 발주서 자동 매칭", "📚 동의어/키워드 관리", "📊 DB 연동 상태"]
    )
    st.markdown("---")
    st.info("💡 **Tip:** 매칭 실패 건은 다운로드한 엑셀의 두 번째 시트에서 도매가와 추천 상품을 확인하세요!")

@st.cache_resource
def load_engine():
    return BrandMatchingSystem()

engine = load_engine()

if menu == "✅ 발주서 자동 매칭":
    st.title("🚀 2026 브랜드 매칭 시스템 (첫 번째 시트 전용 통합 매칭)")
    st.markdown("여러 개의 발주 엑셀 파일을 올리면, **각 파일의 '첫 번째 시트(Sheet1)' 데이터만 추출**하여 하나로 합친 뒤 안전하게 매칭합니다.")
    st.markdown("---")

    st.subheader("📁 발주서 일괄 업로드")
    uploaded_files = st.file_uploader(
        "작업할 발주 엑셀 파일들을 모두 드래그해서 올려주세요", 
        type=['xlsx', 'xls', 'csv'], 
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("🏁 통합 매칭 시작 (진행률 보기)", use_container_width=True):
            st.info(f"📁 총 {len(uploaded_files)}개의 파일에서 '첫 번째 시트'의 유효 데이터를 추출하고 있습니다...")
            try:
                dfs = []
                for file in uploaded_files:
                    # 🌟 [수술 핵심] 무조건 파일의 '첫 번째 시트'만 읽어오도록 수정 완료!
                    if file.name.endswith('.csv'):
                        df = pd.read_csv(file)
                    else:
                        df = pd.read_excel(file) # 기본값이 첫 번째 시트만 읽는 것입니다.
                    
                    # 🌟 유령 행(빈 줄) 필터링은 그대로 유지하여 데이터 밀림 현상 완벽 차단!
                    df = df.dropna(how='all') 
                    
                    if not df.empty:
                        # 폼이 제각각인 파일들을 합치기 전에, 먼저 표준 폼으로 각각 변환합니다.
                        converted_df = engine.convert_sheet1_to_sheet2(df)
                        dfs.append(converted_df)
                
                if not dfs:
                    st.warning("업로드된 파일들의 첫 번째 시트에 유효한 데이터가 없습니다.")
                    st.stop()

                # 똑같은 표준 폼으로 맞춰진 데이터들을 하나로 안전하게 병합
                combined_sheet2_df = pd.concat(dfs, ignore_index=True)
                total_input_rows = len(combined_sheet2_df)
                
                st.markdown("---")
                st.subheader("⚙️ 실시간 작업 진행 현황")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(current, total):
                    percent = int((current / total) * 100)
                    progress_bar.progress(percent / 100)
                    status_text.markdown(f"**진행률: {percent}%** ({current:,} / {total:,} 행 처리 중...)")
                
                with st.spinner(f"🤖 중복/누락 제로! 총 {total_input_rows:,}행 매칭 엔진 가동 중..."):
                    # 합쳐진 sheet2를 통째로 넘겨서 매칭만 수행
                    final_df, failed_products = engine.process_matching(combined_sheet2_df, progress_callback=update_progress)
                    
                st.success("🎉 불필요한 시트는 제외하고, 첫 번째 시트들만 완벽하게 통합 매칭되었습니다!")
                
                total_count = len(final_df)
                failed_count = len(failed_products)
                success_count = total_count - failed_count
                
                col1, col2, col3 = st.columns(3)
                col1.metric("총 발주 건수 (첫 시트 기준)", f"{total_count:,}건")
                col2.metric("매칭 성공 (정확/유사)", f"{success_count:,}건")
                col3.metric("매칭 실패 (추천 필요)", f"{failed_count:,}건")
                
                st.markdown("---")
                st.subheader("📊 매칭 결과 미리보기 (상위 50개)")
                st.dataframe(final_df.head(50))
                
                st.markdown("---")
                st.subheader("💡 통합 엑셀 다운로드 (스마트 추천 시트 포함)")
                st.write("업로드하신 모든 파일의 결과가 하나로 합쳐진 파일입니다. **다운로드하신 엑셀의 두 번째 시트**에서 실패 건 및 추천 상품을 확인하세요.")

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_df.to_excel(writer, index=False, sheet_name='통합_전체_매칭결과')
                    if failed_products:
                        failed_df = pd.DataFrame(failed_products)
                        failed_df.to_excel(writer, index=False, sheet_name='실패건_유사상품추천')
                
                st.download_button(
                    label="📥 누락 제로 통합 결과 다운로드",
                    data=output.getvalue(),
                    file_name="통합_매칭완료_무결점.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

elif menu == "📚 동의어/키워드 관리":
    st.title("📚 동의어 및 제외 키워드 관리")
    st.markdown("AWS DB에 직접 접근하여 매칭 엔진을 실시간으로 똑똑하게 학습시키는 관리자 전용 공간입니다.")
    
    if st.button("🔄 매칭 엔진 기억 새로고침 (DB 변경사항 즉시 적용)"):
        st.cache_resource.clear()
        st.success("매칭 엔진이 최신 DB 정보로 완벽하게 업데이트되었습니다!")
        st.rerun()

    st.markdown("---")
    tab1, tab2 = st.tabs(["📚 동의어 사전 추가", "✂️ 제외 키워드 추가"])
    
    with tab1:
        st.subheader("새로운 동의어 등록")
        with st.form("synonym_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1: std_word = st.text_input("기준 단어 (DB 진짜 브랜드명)", placeholder="예: 나이키")
            with col2: syn_word = st.text_input("동의어 (발주서 오타)", placeholder="예: 나이기")
            submit_syn = st.form_submit_button("AWS DB에 추가하기")
            
            if submit_syn and std_word and syn_word:
                db = SessionLocal()
                try:
                    db.add(Synonym(standard_word=std_word.strip(), synonym_word=syn_word.strip()))
                    db.commit()
                    st.success("✅ 성공!")
                    st.cache_resource.clear()
                except Exception as e: st.error(f"오류: {e}")
                finally: db.close()
        
        st.markdown("---")
        st.subheader("📋 등록된 동의어 목록")
        db = SessionLocal()
        syns = db.query(Synonym).filter(Synonym.is_active == True).all()
        if syns: st.dataframe(pd.DataFrame([{"기준 단어": s.standard_word, "동의어": s.synonym_word} for s in syns]), use_container_width=True)
        db.close()

    with tab2:
        st.subheader("새로운 제외 키워드 등록")
        with st.form("keyword_form", clear_on_submit=True):
            new_keyword = st.text_input("제외할 키워드 입력", placeholder="예: (무료배송)")
            submit_kw = st.form_submit_button("AWS DB에 추가하기")
            
            if submit_kw and new_keyword:
                db = SessionLocal()
                try:
                    db.add(Keyword(keyword_text=new_keyword.strip()))
                    db.commit()
                    st.success("✅ 성공!")
                    st.cache_resource.clear()
                except Exception as e: st.error(f"오류: {e}")
                finally: db.close()
        
        st.markdown("---")
        st.subheader("📋 등록된 제외 키워드 목록")
        db = SessionLocal()
        kws = db.query(Keyword).all()
        if kws: st.dataframe(pd.DataFrame([{"방해물 키워드": k.keyword_text} for k in kws]), use_container_width=True)
        db.close()

elif menu == "📊 DB 연동 상태":
    st.title("📊 AWS DB 연동 상태")
    if engine.brand_data is not None:
        st.success("🟢 AWS RDS Database 정상 연결됨")
        st.metric("로드된 데이터", f"{len(engine.brand_data):,}건")
    else:
        st.error("🔴 DB 연결에 문제가 있습니다.")
