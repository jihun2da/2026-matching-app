import streamlit as st
import pandas as pd
from io import BytesIO
from brand_matching_system import BrandMatchingSystem

st.set_page_config(page_title="2026 브랜드 매칭 시스템", layout="wide")

@st.cache_resource
def load_engine():
    return BrandMatchingSystem()

engine = load_engine()

# --- 사이드바 ---
with st.sidebar:
    st.title("⚙️ 시스템 메뉴")
    menu = st.radio("메뉴", ["✅ 발주서 자동 매칭", "📚 동의어 관리", "📊 DB 상태"])

if menu == "✅ 발주서 자동 매칭":
    st.title("🚀 통합 매칭 서비스")
    files = st.file_uploader("엑셀 파일들을 선택하세요", type=['xlsx','xls'], accept_multiple_files=True)

    if files:
        if st.button("🏁 일괄 매칭 시작"):
            all_df = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
            total_rows = len(all_df)
            
            st.markdown("---")
            st.subheader("⚙️ 실시간 작업 진행 현황")
            
            # 🌟 [게이지 및 퍼센트 UI 생성]
            progress_bar = st.progress(0)
            status_text = st.empty() # 글자를 실시간으로 바꿀 빈 공간
            
            # 엔진에 넘겨줄 진행률 업데이트 함수
            def update_progress(current, total):
                percent = int((current / total) * 100)
                progress_bar.progress(percent / 100)
                status_text.markdown(f"**진행률: {percent}%** ({current:,} / {total:,} 행 처리 중...)")

            # 매칭 실행
            try:
                sheet2_df, failed_products = engine.process_matching(all_df, progress_callback=update_progress)
                
                st.success("✅ 모든 작업이 완료되었습니다!")
                
                # 결과 요약 및 다운로드 버튼 (기존과 동일)
                st.metric("총 작업 건수", f"{len(sheet2_df):,}건")
                st.dataframe(sheet2_df.head(50))
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    sheet2_df.to_excel(writer, index=False, sheet_name='매칭결과')
                    if failed_products:
                        pd.DataFrame(failed_products).to_excel(writer, index=False, sheet_name='추천상품')
                
                st.download_button("📥 통합 결과 다운로드", output.getvalue(), "통합결과.xlsx")
                
            except Exception as e:
                st.error(f"오류 발생: {e}")

# ... (나머지 동의어 관리/DB 상태 메뉴 코드는 기존과 동일하게 유지)
