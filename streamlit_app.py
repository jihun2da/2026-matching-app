import streamlit as st
import pandas as pd
from io import BytesIO
from brand_matching_system import BrandMatchingSystem
from database import SessionLocal, Synonym, Keyword

# 1. 페이지 기본 설정 (가장 상단에 위치해야 함)
st.set_page_config(page_title="2026 브랜드 매칭 시스템", layout="wide", initial_sidebar_state="expanded")

# --- 🌟 왼쪽 사이드바 메뉴 ---
with st.sidebar:
    st.title("⚙️ 2026 시스템 메뉴")
    st.markdown("---")
    menu = st.radio(
        "작업 메뉴를 선택하세요", 
        ["✅ 발주서 자동 매칭", "📚 동의어/키워드 관리", "📊 DB 연동 상태"]
    )
    st.markdown("---")
    st.info("💡 **Tip:** 매칭 실패 건은 다운로드한 엑셀의 두 번째 시트에서 도매가와 추천 상품을 확인하세요!")

# 2. 매칭 엔진 초기화 (캐싱하여 속도 향상)
@st.cache_resource
def load_engine():
    return BrandMatchingSystem()

engine = load_engine()

# ==========================================
# 🚀 메인 화면 1: 발주서 자동 매칭 메뉴
# ==========================================
if menu == "✅ 발주서 자동 매칭":
    st.title("🚀 2026 브랜드 매칭 시스템 (다중 파일 일괄 처리)")
    st.markdown("여러 개의 발주 엑셀 파일을 한 번에 업로드하시면, 통합하여 매칭 후 하나의 결과 파일로 만들어 드립니다.")
    st.markdown("---")

    st.subheader("📁 발주서 일괄 업로드")
    # 🌟 [다중 파일 기능 추가] accept_multiple_files=True 로 설정
    uploaded_files = st.file_uploader(
        "작업할 발주 엑셀 파일들을 모두 드래그해서 올려주세요 (최대 권장: 합산 1만 행)", 
        type=['xlsx', 'xls'], 
        accept_multiple_files=True
    )

    if uploaded_files: # 파일이 1개라도 업로드 되었다면
        st.info(f"📁 총 {len(uploaded_files)}개의 파일을 병합하여 분석 중입니다...")
        try:
            # 🌟 [핵심] 여러 개의 엑셀 파일을 읽어서 하나의 표(DataFrame)로 합치기
            dfs = []
            for file in uploaded_files:
                df = pd.read_excel(file)
                dfs.append(df)
            
            # 모든 파일의 데이터를 세로로 쭉 이어 붙입니다.
            sheet1_df = pd.concat(dfs, ignore_index=True)
            
            with st.spinner(f"🤖 총 {len(sheet1_df):,}행 통합 매칭 엔진 가동 중... (AWS DB 연동)"):
                # 매칭 프로세스 실행 (합쳐진 데이터로 한 번에 실행!)
                sheet2_df, failed_products = engine.process_matching(sheet1_df)
                
            st.success("🎉 모든 파일의 통합 매칭 작업이 완료되었습니다!")
            
            # 매칭 통계 보여주기
            total_count = len(sheet2_df)
            failed_count = len(failed_products)
            success_count = total_count - failed_count
            
            col1, col2, col3 = st.columns(3)
            col1.metric("총 발주 건수 (병합됨)", f"{total_count:,}건")
            col2.metric("매칭 성공 (정확/유사)", f"{success_count:,}건")
            col3.metric("매칭 실패 (추천 필요)", f"{failed_count:,}건")
            
            # 결과 미리보기 화면
            st.markdown("---")
            st.subheader("📊 매칭 결과 미리보기 (상위 50개)")
            st.dataframe(sheet2_df.head(50))
            
            st.markdown("---")
            st.subheader("💡 통합 엑셀 다운로드 (스마트 추천 시트 포함)")
            st.write("업로드하신 모든 파일의 결과가 하나로 합쳐진 파일입니다. **두 번째 시트**에서 실패 건 및 추천 상품을 확인하세요.")

            # 엑셀 다운로드 생성 (2개 시트 분리 로직)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 첫 번째 시트: 전체 매칭 결과
                sheet2_df.to_excel(writer, index=False, sheet_name='통합_전체_매칭결과')
                
                # 두 번째 시트: 실패 건 및 스마트 추천
                if failed_products:
                    failed_df = pd.DataFrame(failed_products)
                    failed_df.to_excel(writer, index=False, sheet_name='실패건_유사상품추천')
            
            # 다운로드 버튼
            st.download_button(
                label="📥 통합 매칭 완료 엑셀 다운로드",
                data=output.getvalue(),
                file_name="통합_매칭완료_스마트결과.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"엑셀 파일 병합 또는 처리 중 에러가 발생했습니다: {e}")

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
        st.write("매칭 실패 엑셀(Sheet2)에서 확인한 오타나 별명을 추가해 주세요.")
        
        with st.form("synonym_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                std_word = st.text_input("기준 단어 (DB에 있는 진짜 브랜드명)", placeholder="예: 나이키")
            with col2:
                syn_word = st.text_input("동의어 (발주서에 자주 적히는 오타)", placeholder="예: 나이기, 나이키(신발)")
            
            submit_syn = st.form_submit_button("AWS DB에 추가하기")
            
            if submit_syn:
                if std_word and syn_word:
                    db = SessionLocal()
                    try:
                        new_syn = Synonym(standard_word=std_word.strip(), synonym_word=syn_word.strip())
                        db.add(new_syn)
                        db.commit()
                        st.success(f"✅ 성공! 앞으로 발주서에 [{syn_word}] 라고 적혀도 무조건 [{std_word}] 로 매칭됩니다.")
                        st.cache_resource.clear()
                    except Exception as e:
                        st.error(f"데이터베이스 오류: {e}")
                    finally:
                        db.close()
                else:
                    st.warning("기준 단어와 동의어를 모두 입력해주세요.")
        
        st.markdown("---")
        st.subheader("📋 현재 등록된 동의어 목록")
        db = SessionLocal()
        syns = db.query(Synonym).filter(Synonym.is_active == True).all()
        if syns:
            syn_data = [{"기준 단어 (정답)": s.standard_word, "동의어 (오타/별명)": s.synonym_word} for s in syns]
            st.dataframe(pd.DataFrame(syn_data), use_container_width=True)
        else:
            st.info("아직 등록된 동의어가 없습니다.")
        db.close()

    with tab2:
        st.subheader("새로운 제외 키워드 등록")
        st.write("상품명에서 아예 무시하고 지워버릴 방해물 단어를 등록합니다.")
        
        with st.form("keyword_form", clear_on_submit=True):
            new_keyword = st.text_input("제외할 키워드 입력", placeholder="예: (무료배송), 당일발송, 특가")
            submit_kw = st.form_submit_button("AWS DB에 추가하기")
            
            if submit_kw:
                if new_keyword:
                    db = SessionLocal()
                    try:
                        kw = Keyword(keyword_text=new_keyword.strip())
                        db.add(kw)
                        db.commit()
                        st.success(f"✅ 성공! 앞으로 상품명에 [{new_keyword}] 라는 글자가 있으면 자동으로 삭제하고 매칭합니다.")
                        st.cache_resource.clear()
                    except Exception as e:
                        st.error(f"데이터베이스 오류: {e}")
                    finally:
                        db.close()
                else:
                    st.warning("키워드를 입력해주세요.")
        
        st.markdown("---")
        st.subheader("📋 현재 등록된 제외 키워드 목록")
        db = SessionLocal()
        kws = db.query(Keyword).all()
        if kws:
            kw_data = [{"등록된 방해물 키워드": k.keyword_text} for k in kws]
            st.dataframe(pd.DataFrame(kw_data), use_container_width=True)
        else:
            st.info("아직 등록된 방해물 키워드가 없습니다.")
        db.close()

# ==========================================
# 📊 서브 화면 3: DB 상태
# ==========================================
elif menu == "📊 DB 연동 상태":
    st.title("📊 AWS DB 연동 상태")
    if engine.brand_data is not None:
        st.success("🟢 AWS RDS Database 정상 연결됨")
        st.metric("현재 로드된 브랜드/상품 데이터", f"{len(engine.brand_data):,}건")
        st.metric("현재 엔진이 기억하는 동의어 세트", f"{len(engine.synonym_dict):,}건")
    else:
        st.error("🔴 DB 연결에 문제가 있습니다.")
