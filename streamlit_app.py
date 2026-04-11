import streamlit as st
import pandas as pd
from io import BytesIO
from brand_matching_system import BrandMatchingSystem

# 1. 페이지 기본 설정 (가장 상단에 위치해야 함)
st.set_page_config(page_title="2026 브랜드 매칭 시스템", layout="wide")

st.title("🚀 2026 브랜드 매칭 시스템 (스마트 추천 탑재)")
st.markdown("발주 엑셀 파일을 업로드하면 AWS DB와 연동하여 초고속으로 매칭을 완료합니다.")
st.markdown("---")

# 2. 매칭 엔진 초기화 (캐싱하여 속도 향상)
@st.cache_resource
def load_engine():
    return BrandMatchingSystem()

engine = load_engine()

# 3. 파일 업로드 섹션
st.subheader("📁 발주서 업로드")
uploaded_file = st.file_uploader("작업할 발주 엑셀 파일(Sheet1)을 업로드하세요", type=['xlsx', 'xls'])

if uploaded_file is not None:
    st.info("파일을 분석하고 있습니다...")
    try:
        # 엑셀 파일 읽기
        sheet1_df = pd.read_excel(uploaded_file)
        
        with st.spinner("🤖 매칭 엔진 가동 중... (AWS DB 데이터 비교 중)"):
            # 매칭 프로세스 실행 (brand_matching_system.py의 기능 호출)
            sheet2_df, failed_products = engine.process_matching(sheet1_df)
            
        st.success("🎉 매칭 작업이 완료되었습니다!")
        
        # 매칭 통계 보여주기
        total_count = len(sheet2_df)
        failed_count = len(failed_products)
        success_count = total_count - failed_count
        
        col1, col2, col3 = st.columns(3)
        col1.metric("총 발주 건수", f"{total_count}건")
        col2.metric("매칭 성공 (정확/유사)", f"{success_count}건")
        col3.metric("매칭 실패 (추천 필요)", f"{failed_count}건")
        
        # 4. 결과 미리보기 화면
        st.markdown("---")
        st.subheader("📊 매칭 결과 미리보기 (상위 50개)")
        st.dataframe(sheet2_df.head(50))
        
        st.markdown("---")
        st.subheader("💡 엑셀 다운로드 (스마트 추천 시트 포함)")
        st.write("다운로드하신 엑셀 파일의 **두 번째 시트**에서 실패 건에 대한 유사 상품 추천을 확인하실 수 있습니다.")

        # 5. 엑셀 다운로드 생성 (2개 시트 분리 로직)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 첫 번째 시트: 전체 매칭 결과 (기존 양식)
            sheet2_df.to_excel(writer, index=False, sheet_name='전체_매칭결과')
            
            # 두 번째 시트: 실패 건 및 스마트 추천 (실패건이 1개라도 있을 경우에만 생성)
            if failed_products:
                failed_df = pd.DataFrame(failed_products)
                failed_df.to_excel(writer, index=False, sheet_name='실패건_유사상품추천')
        
        # 6. 다운로드 버튼
        st.download_button(
            label="📥 매칭 완료 엑셀 다운로드",
            data=output.getvalue(),
            file_name="매칭완료_스마트결과.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        st.error(f"엑셀 처리 중 에러가 발생했습니다: {e}")
