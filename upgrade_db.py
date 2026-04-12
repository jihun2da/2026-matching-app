# -*- coding: utf-8 -*-
from database import engine, Synonym, Base
import sqlalchemy

print("🚀 [AWS RDS] DB 스마트 업그레이드 스크립트를 가동합니다...")

try:
    # 1. 연결 확인
    with engine.connect() as conn:
        print("✅ AWS 데이터베이스 연결에 성공했습니다.")

    # 2. 기존 동의어 테이블 삭제 (구형 규격 제거)
    # 마스터 상품(MasterProduct)과 키워드(Keyword)는 건드리지 않습니다!
    print("⏳ 기존 동의어 테이블(Synonym) 삭제 중...")
    try:
        Synonym.__table__.drop(engine)
        print("✔️ 구형 테이블 삭제 완료.")
    except Exception as e:
        print("ℹ️ 기존 테이블이 없거나 이미 삭제되었습니다.")

    # 3. 새로운 규격으로 테이블 생성
    # Synonym 테이블에 apply_brand, apply_product, apply_option, is_exact_match 칸이 생깁니다.
    print("⏳ 신형 스마트 동의어 테이블 생성 중...")
    Base.metadata.create_all(bind=engine)
    print("✔️ 신형 테이블 생성 성공!")

    print("\n🎉 모든 업그레이드가 완료되었습니다!")
    print("이제 'streamlit run streamlit_app.py'를 실행하여 시스템을 사용하세요.")

except Exception as e:
    print(f"\n❌ 오류가 발생했습니다: {e}")
    print("주로 DB 아이디/비밀번호가 틀렸거나 AWS 보안 그룹(인바운드) 문제일 수 있습니다.")
