# database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

import streamlit as st  # 👈 바로 이 줄을 추가해 주세요!

# 🚨 클라이언트님의 AWS RDS 정보로 세팅된 주소입니다!
# 주의: <여기에비밀번호입력> 부분을 지우고, 처음에 설정하셨던 마스터 비밀번호로 꼭 바꿔주세요! (괄호 <>도 지우셔야 합니다)
SQLALCHEMY_DATABASE_URL = st.secrets["DB_URL"]

# DB 연결 엔진 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 👑 1. 마스터 데이터 테이블
class MasterProduct(Base):
    __tablename__ = "master_products"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, index=True)            # H열(브랜드)
    product_name = Column(String, index=True)     # I열(상품명)
    options = Column(String)                      # 옵션입력
    wholesale_name = Column(String)               # N열(중도매명)
    supply_price = Column(Float)                  # O열(도매가격/공급가)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 📖 2. 동의어 사전 테이블
class Synonym(Base):
    __tablename__ = "synonyms"

    id = Column(Integer, primary_key=True, index=True)
    standard_word = Column(String, index=True)    # 표준 단어
    synonym_word = Column(String, unique=True)    # 유사어
    is_active = Column(Boolean, default=True)

# 🚫 3. 제외 키워드 테이블
class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword_text = Column(String, unique=True, index=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

# 데이터베이스 테이블 생성 함수
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 성공! AWS 클라우드 데이터베이스에 테이블이 완벽하게 생성되었습니다!")
    except Exception as e:
        print(f"❌ 연결 실패. 에러 내용: {e}")
        print("방화벽(보안 그룹) 설정이나 비밀번호가 맞는지 다시 한번 확인해 주세요.")

if __name__ == "__main__":
    init_db()
