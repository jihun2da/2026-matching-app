import streamlit as st
import pandas as pd
from io import BytesIO
from brand_matching_system import BrandMatchingSystem
from database import SessionLocal, Synonym, Keyword, MasterProduct

# 1. 페이지 기본 설정 (가장 상단에 위치해야 함)
st.set_page_config(page_title="2026 브랜드 매칭 시스템", layout="wide", initial_sidebar_state="expanded")

# 🌟 세션 상태(기억 장치) 초기화: 화면이 날아가는 것을 완벽하게 방지합니다.
if 'match_state' not in st.session_state:
    st.session_state.match_state = {
        'completed': False,
        'final_df': None,
        'failed_products': [],
        'total_input_rows': 0
    }

# --- 🌟 왼쪽 사이드바 메뉴 ---
with st.sidebar:
    st.title("⚙️ 2026 시스템 메뉴")
    st.markdown("---")
    menu = st.radio(
        "작업 메뉴를 선택하세요", 
        ["✅ 발주서 자동 매칭", "📚 동의어/키워드 관리", "📊 DB 연동 상태"]
    )
    st.markdown("---")
    st.info("💡 **Tip:** 화면을 이동하거나 다운로드를 받아도 작업 내역은 초기화되지 않습니다. (새로고침 시에만 초기화)")
    
    if st.button("🗑️ 현재 작업내역 지우기", use_container_width=True):
        st.session_state.match_state['completed'] = False
        st.rerun()

# 2. 매칭 엔진 초기화
@st.cache_resource
def load_engine():
    return BrandMatchingSystem()

engine = load_engine()

# ==========================================
# 🚀 메인 화면 1: 발주서 자동 매칭 메뉴
# ==========================================
if menu == "✅ 발주서 자동 매칭":
    st.title("🚀 2026 브랜드 매칭 시스템 (통합 매칭 & 기억 유지)")
    st.markdown("발주 엑셀 파일을 여러 개 올리면 **각 파일의 '첫 번째 시트(Sheet1)'만 추출**하여 통합 매칭합니다. 결과는 메뉴 이동 후에도 계속 유지됩니다.")
    st.markdown("---")

    st.subheader("📁 발주서 일괄 업로드")
    uploaded_files = st.file_uploader(
        "작업할 발주 엑셀 파일들을 모두 드래그해서 올려주세요", 
        type=['xlsx', 'xls', 'csv'], 
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("🏁 통합 매칭 시작 (진행률 보기)", use_container_width=True):
            st.info(f"📁 총 {len(uploaded_files)}개의 파일에서 '첫 번째 시트' 데이터를 안전하게 추출 중입니다...")
            try:
                dfs = []
                for file in uploaded_files:
                    # 무조건 첫 번째 시트만 읽기
                    if file.name.endswith('.csv'):
                        df = pd.read_csv(file)
                    else:
                        df = pd.read_excel(file) 
                    
                    df = df.dropna(how='all') # 유령 행 필터링
                    
                    if not df.empty:
                        converted_df = engine.convert_sheet1_to_sheet2(df)
                        dfs.append(converted_df)
                
                if not dfs:
                    st.warning("업로드된 파일들의 첫 번째 시트에 유효한 데이터가 없습니다.")
                    st.stop()

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
                
                with st.spinner(f"🤖 총 {total_input_rows:,}행 매칭 엔진 가동 중..."):
                    final_df, failed_products = engine.process_matching(combined_sheet2_df, progress_callback=update_progress)
                
                # 작업이 끝나면 결과를 세션(기억 장치)에 영구 저장
                st.session_state.match_state['final_df'] = final_df
                st.session_state.match_state['failed_products'] = failed_products
                st.session_state.match_state['total_input_rows'] = total_input_rows
                st.session_state.match_state['completed'] = True
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

    # 기억 장치에 데이터가 저장되어 있다면 항상 화면에 띄워줍니다 (무적 방어막)
    if st.session_state.match_state['completed']:
        final_df = st.session_state.match_state['final_df']
        failed_products = st.session_state.match_state['failed_products']
        
        st.success("🎉 매칭 작업이 완료되었으며, 결과가 안전하게 보존 중입니다! (메뉴를 이동해도 날아가지 않습니다)")
        
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
        st.write("다운로드 버튼을 눌러도 화면이 초기화되지 않습니다. 엑셀의 두 번째 시트에서 실패 건 및 추천 상품을 확인하세요.")
        
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

# ==========================================
# 📚 서브 화면 2: 동의어/키워드 관리
# ==========================================
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

# ==========================================
# 📊 서브 화면 3: DB 상태 (검색 및 업로드 완벽 지원)
# ==========================================
elif menu == "📊 DB 연동 상태":
    st.title("📊 AWS DB 연동 상태 및 데이터 관리")
    
    if engine.brand_data is not None:
        st.success("🟢 AWS RDS Database 정상 연결됨")
        st.metric("현재 로드된 브랜드/상품 데이터", f"{len(engine.brand_data):,}건")
    else:
        st.error("🔴 DB 연결에 문제가 있습니다.")

    st.markdown("---")
    
    st.subheader("🔍 마스터 DB 상품 검색")
    search_keyword = st.text_input("검색할 브랜드명 또는 상품명을 입력하세요 (예: 보니)")
    
    if search_keyword:
        if engine.brand_data is not None and not engine.brand_data.empty:
            mask = engine.brand_data['브랜드'].str.contains(search_keyword, na=False, case=False) | \
                   engine.brand_data['상품명'].str.contains(search_keyword, na=False, case=False)
            search_result = engine.brand_data[mask]
            
            st.write(f"💡 검색 결과: 총 **{len(search_result):,}**건이 발견되었습니다.")
            st.dataframe(search_result, use_container_width=True)
        else:
            st.warning("DB에 데이터가 없습니다.")

    st.markdown("---")
    
    st.subheader("📥 신규 마스터 DB 업로드")
    st.write("새로운 상품이 담긴 엑셀 파일을 업로드하여 AWS DB를 업데이트합니다.")
    st.info("※ 엑셀 파일에는 [브랜드, 상품명, 옵션입력, 중도매, 공급가] 열이 포함되어 있어야 합니다.")
    
    db_upload_file = st.file_uploader("마스터 DB 엑셀 파일 선택", type=['xlsx', 'xls', 'csv'], key="db_uploader")
    
    if db_upload_file:
        if st.button("🚀 AWS DB에 데이터 추가하기", use_container_width=True):
            with st.spinner("데이터베이스에 저장 중입니다..."):
                try:
                    if db_upload_file.name.endswith('.csv'):
                        new_db_df = pd.read_csv(db_upload_file)
                    else:
                        new_db_df = pd.read_excel(db_upload_file)
                    
                    db = SessionLocal()
                    count = 0
                    for _, r in new_db_df.iterrows():
                        brand_val = str(r.get('브랜드', '')).strip()
                        product_val = str(r.get('상품명', '')).strip()
                        
                        if brand_val and brand_val != 'nan':
                            mp = MasterProduct(
                                brand=brand_val,
                                product_name=product_val,
                                options=str(r.get('옵션입력', '')).strip(),
                                wholesale_name=str(r.get('중도매', '')).strip(),
                                supply_price=str(r.get('공급가', '0')).strip()
                            )
                            db.add(mp)
                            count += 1
                    
                    db.commit()
                    st.success(f"✅ 총 {count:,}건의 데이터가 AWS DB에 성공적으로 저장되었습니다!")
                    st.cache_resource.clear()
                    db.close()
                    
                except Exception as e:
                    st.error(f"DB 업로드 중 에러가 발생했습니다: {e}")
