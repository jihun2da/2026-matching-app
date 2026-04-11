# streamlit_app.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 우리가 만든 엔진과 DB 불러오기
from brand_matching_system import BrandMatchingSystem
from database import SessionLocal, MasterProduct, Synonym, Keyword

# 🌟 페이지 기본 설정
st.set_page_config(page_title="2026 주문 매칭 시스템", page_icon="🚀", layout="wide")

# 시스템 초기화 (캐싱하여 매번 DB를 새로 읽지 않도록 속도 향상)
@st.cache_resource
def init_system():
    return BrandMatchingSystem()

system = init_system()

# 🌟 사이드바 (메뉴 네비게이션)
st.sidebar.title("📌 2026 매칭 시스템")
menu = st.sidebar.radio("메뉴를 선택하세요", ["🚀 일일 주문 매칭", "👑 마스터 데이터 관리", "⚙️ 스마트 학습 대시보드"])

st.sidebar.markdown("---")
st.sidebar.info("💡 **시스템 상태**\n\n🟢 AWS RDS 연결 완료\n\n🟢 매칭 엔진 정상 작동 중")
if st.sidebar.button("🔄 엔진 데이터 새로고침"):
    system.load_synonyms_from_db()
    system.load_keywords_from_db()
    system.load_brand_data_from_db()
    st.sidebar.success("최신 DB 데이터로 갱신되었습니다!")

# ==========================================
# 🚀 메뉴 1: 일일 주문 매칭
# ==========================================
if menu == "🚀 일일 주문 매칭":
    st.title("🚀 일일 주문 매칭")
    st.markdown("매일 들어오는 발주 엑셀 파일을 업로드하면, AWS DB의 마스터 데이터와 초고속으로 매칭합니다.")

    uploaded_files = st.file_uploader("발주 엑셀 파일 업로드 (여러 개 가능)", type=['xlsx', 'xls'], accept_multiple_files=True)

    if uploaded_files:
        if st.button("⚡ 매칭 시작", type="primary", use_container_width=True):
            with st.spinner("AWS 클라우드 엔진에서 매칭을 수행 중입니다..."):
                # 업로드된 파일들을 하나로 합치기
                df_list = []
                for file in uploaded_files:
                    df_list.append(pd.read_excel(file))
                combined_df = pd.concat(df_list, ignore_index=True)
                
                # 매칭 수행 (엔진 내부에서 Sheet1 -> Sheet2 변환까지 자동 수행됨)
                matched_df, failed_list = system.process_matching(combined_df)
                
                st.success(f"🎉 매칭 완료! (총 {len(matched_df)}건 처리)")
                
                # 매칭 성공률 계산
                success_count = len(matched_df[matched_df['매칭_상태'].isin(['정확매칭', '유사매칭'])])
                total_count = len(matched_df)
                st.info(f"📊 **매칭 성공률:** {success_count}/{total_count}건 ({(success_count/total_count)*100:.1f}%)")
                
                # 다운로드 버튼
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    matched_df.to_excel(writer, sheet_name='매칭결과', index=False)
                st.download_button(
                    label="📥 23열 매칭 엑셀 다운로드",
                    data=output.getvalue(),
                    file_name=f"매칭결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

                st.markdown("---")
                
                # 결과 탭
                tab1, tab2, tab3 = st.tabs(["✅ 정확 매칭 (90% 이상)", "🟡 유사 매칭 (60~89%)", "❌ 매칭 실패 (수동확인 요망)"])
                
                with tab1:
                    exact_df = matched_df[matched_df['매칭_상태'] == '정확매칭']
                    st.dataframe(exact_df, use_container_width=True)
                
                with tab2:
                    similar_df = matched_df[matched_df['매칭_상태'] == '유사매칭']
                    st.dataframe(similar_df, use_container_width=True)

                with tab3:
                    if failed_list:
                        failed_df = pd.DataFrame(failed_list)
                        st.warning(f"{len(failed_list)}건의 매칭 실패가 있습니다. '스마트 학습 대시보드'에서 이 브랜드/상품의 동의어를 추가해주세요.")
                        st.dataframe(failed_df, use_container_width=True)
                    else:
                        st.info("매칭 실패 건이 없습니다! 완벽합니다.")

# ==========================================
# 👑 메뉴 2: 마스터 데이터 관리 (중복 해결 기능 포함)
# ==========================================
elif menu == "👑 마스터 데이터 관리":
    st.title("👑 마스터 데이터 관리")
    
    tab_upload, tab_view = st.tabs(["📥 마스터 일일 추가 업로드", "🗄️ DB 조회 및 검색"])
    
    with tab_upload:
        st.markdown("새로운 마스터 데이터 엑셀(`2026주문매칭.xlsx` 양식)을 업로드하여 DB를 최신화합니다.")
        master_file = st.file_uploader("새 마스터 엑셀 업로드", type=['xlsx', 'xls'])
        
        if master_file:
            if st.button("데이터 분석 및 비교"):
                with st.spinner("DB와 중복 데이터를 비교 중입니다..."):
                    new_df = pd.read_excel(master_file).fillna("")
                    db = SessionLocal()
                    
                    st.session_state['new_items'] = []
                    st.session_state['conflict_items'] = []
                    
                    for _, row in new_df.iterrows():
                        brand = str(row.get('브랜드', '')).strip()
                        product = str(row.get('상품명', '')).strip()
                        options = str(row.get('옵션입력', '')).strip()
                        if not brand and not product: continue
                        
                        price_raw = row.get('공급가', 0)
                        try: price = float(price_raw) if price_raw != "" else 0.0
                        except: price = 0.0
                        
                        # 기존 DB 확인 (브랜드+상품명+옵션이 같은지)
                        existing = db.query(MasterProduct).filter(
                            MasterProduct.brand == brand,
                            MasterProduct.product_name == product,
                            MasterProduct.options == options
                        ).first()
                        
                        if existing:
                            # 가격이나 도매처가 다르면 충돌로 간주
                            if existing.supply_price != price or existing.wholesale_name != str(row.get('중도매', '')).strip():
                                st.session_state['conflict_items'].append({
                                    'id': existing.id,
                                    'brand': brand, 'product': product, 'options': options,
                                    'old_price': existing.supply_price, 'new_price': price,
                                    'old_wholesale': existing.wholesale_name, 'new_wholesale': str(row.get('중도매', '')).strip(),
                                    'updated_at': existing.updated_at.strftime('%Y-%m-%d')
                                })
                        else:
                            st.session_state['new_items'].append({
                                'brand': brand, 'product': product, 'options': options,
                                'wholesale': str(row.get('중도매', '')).strip(), 'price': price
                            })
                    db.close()
                    st.session_state['analyzed'] = True
        
        # 분석 완료 후 UI
        if st.session_state.get('analyzed', False):
            st.success(f"분석 완료! 🟢 신규: {len(st.session_state.get('new_items', []))}건 / 🟡 변경됨: {len(st.session_state.get('conflict_items', []))}건")
            
            # 🟢 신규 데이터 즉시 추가
            if st.session_state.get('new_items'):
                if st.button("✨ 신규 데이터 DB에 일괄 추가하기", type="primary"):
                    db = SessionLocal()
                    count = 0
                    for item in st.session_state['new_items']:
                        db.add(MasterProduct(
                            brand=item['brand'], product_name=item['product'], options=item['options'],
                            wholesale_name=item['wholesale'], supply_price=item['price']
                        ))
                        count += 1
                        if count % 500 == 0: db.commit()
                    db.commit()
                    db.close()
                    st.session_state['new_items'] = []
                    system.load_brand_data_from_db() # 엔진 리로드
                    st.success("신규 데이터가 성공적으로 DB에 저장되었습니다!")
            
            # 🟡 중복 데이터 해결 UI
            if st.session_state.get('conflict_items'):
                st.markdown("---")
                st.markdown("### ⚠️ 데이터 변경사항 발견 (가격/도매처 충돌)")
                st.markdown("기존 DB의 정보와 새 엑셀의 정보가 다릅니다. 새 엑셀의 데이터로 덮어쓰시겠습니까?")
                
                conflict_df = pd.DataFrame(st.session_state['conflict_items'])
                conflict_df['적용선택'] = True # 기본적으로 덮어쓰기에 체크
                
                edited_df = st.data_editor(
                    conflict_df[['적용선택', 'brand', 'product', 'old_price', 'new_price', 'old_wholesale', 'new_wholesale', 'updated_at']],
                    column_config={
                        "적용선택": st.column_config.CheckboxColumn("새 데이터로 덮어쓰기", default=True)
                    },
                    disabled=["brand", "product", "old_price", "new_price", "old_wholesale", "new_wholesale", "updated_at"],
                    use_container_width=True
                )
                
                if st.button("💾 체크된 항목 DB에 덮어쓰기"):
                    db = SessionLocal()
                    update_count = 0
                    for idx, row in edited_df.iterrows():
                        if row['적용선택']: # 체크된 것만 업데이트
                            item_id = st.session_state['conflict_items'][idx]['id']
                            new_price = st.session_state['conflict_items'][idx]['new_price']
                            new_wholesale = st.session_state['conflict_items'][idx]['new_wholesale']
                            
                            db_item = db.query(MasterProduct).filter(MasterProduct.id == item_id).first()
                            if db_item:
                                db_item.supply_price = new_price
                                db_item.wholesale_name = new_wholesale
                                update_count += 1
                    db.commit()
                    db.close()
                    st.session_state['conflict_items'] = []
                    st.session_state['analyzed'] = False
                    system.load_brand_data_from_db() # 엔진 리로드
                    st.success(f"총 {update_count}건의 데이터가 최신 정보로 업데이트 되었습니다!")

    with tab_view:
        st.markdown("현재 AWS DB에 저장된 모든 마스터 데이터를 조회합니다.")
        search = st.text_input("🔍 브랜드 또는 상품명 검색")
        
        db = SessionLocal()
        query = db.query(MasterProduct)
        if search:
            query = query.filter((MasterProduct.brand.contains(search)) | (MasterProduct.product_name.contains(search)))
        
        # 전체 개수 표시
        total_items = query.count()
        st.caption(f"검색 결과: 총 {total_items}건 (속도를 위해 화면에는 100건만 표시됩니다)")
        
        results = query.limit(100).all()
        db.close()
        
        if results:
            view_df = pd.DataFrame([{
                'ID': r.id, '브랜드': r.brand, '상품명': r.product_name, 
                '옵션': r.options, '도매처': r.wholesale_name, '공급가': r.supply_price, '최종수정일': r.updated_at.strftime('%Y-%m-%d')
            } for r in results])
            st.dataframe(view_df, use_container_width=True)

# ==========================================
# ⚙️ 메뉴 3: 스마트 학습 대시보드
# ==========================================
elif menu == "⚙️ 스마트 학습 대시보드":
    st.title("⚙️ 스마트 학습 대시보드")
    st.markdown("여기에 추가된 데이터는 즉시 **AWS 클라우드 DB에 영구 저장**되며, 다음 매칭부터 실시간으로 적용됩니다.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📖 동의어 사전 추가")
        st.info("브랜드명, 상품명, 색상 등의 오타나 이명을 학습시킵니다.")
        std_word = st.text_input("표준 단어 (예: CON, 나나뷔스티에)")
        syn_word = st.text_input("유사어/오타 (예: 콘, 나나비스티)")
        
        if st.button("✨ 동의어 DB에 저장", use_container_width=True):
            if std_word and syn_word:
                db = SessionLocal()
                try:
                    exists = db.query(Synonym).filter(Synonym.synonym_word == syn_word).first()
                    if not exists:
                        db.add(Synonym(standard_word=std_word.strip(), synonym_word=syn_word.strip()))
                        db.commit()
                        system.load_synonyms_from_db() # 즉시 엔진에 반영
                        st.success(f"'{syn_word}' -> '{std_word}' 학습 완료!")
                    else:
                        st.warning("이미 등록된 유사어입니다.")
                finally:
                    db.close()
            else:
                st.warning("표준 단어와 유사어를 모두 입력하세요.")
                
        st.markdown("---")
        st.markdown("**현재 등록된 동의어 목록**")
        syn_list = []
        for std, syns in system.synonym_dict.items():
            for syn in syns:
                syn_list.append({"표준 단어": std, "유사어": syn})
        st.dataframe(pd.DataFrame(syn_list), height=400, use_container_width=True)

    with col2:
        st.markdown("### 🚫 노이즈 필터 (제외 키워드) 추가")
        st.info("상품명에서 불필요한 단어를 괄호째 날려버리는 강력한 필터입니다.")
        new_kw = st.text_input("새 키워드 입력 (예: *S~XL*, 특가)")
        
        if st.button("✨ 키워드 DB에 저장", use_container_width=True):
            if system.add_keyword(new_kw):
                st.success(f"'{new_kw}' 추가 완료!")
            else:
                st.warning("이미 존재하거나 오류가 발생했습니다.")
                
        st.markdown("---")
        st.markdown("**현재 등록된 키워드 목록**")
        st.dataframe(pd.DataFrame(system.keyword_list, columns=["키워드"]), height=400, use_container_width=True)
