# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import urllib.parse

DB_PASSWORD = urllib.parse.quote_plus("Ppooii**9098")
SQLALCHEMY_DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@matching-db-2026.cozmuw2eq103.us-east-1.rds.amazonaws.com:5432/matching_db"

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
    supply_price = Column(Float) # 숫자로 완벽 보존

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

Base.metadata.create_all(bind=engine)
