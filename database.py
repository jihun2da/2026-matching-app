from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./matching_system.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
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
    
    # [스마트 태그용 신규 칼럼]
    apply_brand = Column(Boolean, default=True)
    apply_product = Column(Boolean, default=True)
    apply_option = Column(Boolean, default=False)
    is_exact_match = Column(Boolean, default=False)

class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True, index=True)
    keyword_text = Column(String, unique=True, index=True)

Base.metadata.create_all(bind=engine)
