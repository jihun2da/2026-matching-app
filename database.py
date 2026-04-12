# database.py (AWS RDS 전용 전체 코드)
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
import urllib.parse  # 🌟 특수문자 처리를 위해 추가

# 비밀번호에 특수문자(**)가 있으므로 안전하게 인코딩합니다.
DB_PASSWORD = urllib.parse.quote_plus("Ppooii**9098") 

# 이제 주소에 안전하게 삽입됩니다.
SQLALCHEMY_DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@matching-db-2026.cozmuw2eq103.us-east-1.rds.amazonaws.com:5432/matching_db"

# AWS(PostgreSQL/MySQL) 연결 시에는 check_same_thread 옵션이 필요 없으므로 제거했습니다.
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class MasterProduct(Base):
    __tablename__ = "master_products"
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, index=True)
    product_name = Column(String, index=True)
    options = Column(String)
    wholesale_name = Column(String)
    supply_price = Column(String)

class Synonym(Base):
    __tablename__ = "synonyms"
    id = Column(Integer, primary_key=True, index=True)
    standard_word = Column(String, index=True)
    synonym_word = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    apply_brand = Column(Boolean, default=True)
    apply_product = Column(Boolean, default=True)
    apply_option = Column(Boolean, default=False)
    is_exact_match = Column(Boolean, default=False)

class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True, index=True)
    keyword_text = Column(String, unique=True, index=True)

# 테이블 생성 (AWS에 이미 테이블이 있다면 기존 데이터는 유지됩니다)
Base.metadata.create_all(bind=engine)
