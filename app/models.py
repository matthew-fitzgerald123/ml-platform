from sqlalchemy import Column, String, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class FeatureSet(Base):
    __tablename__ = "feature_sets"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String, unique=True, nullable=False)
    schema     = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class FeatureValue(Base):
    __tablename__ = "feature_values"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    entity_id   = Column(String, nullable=False, index=True)
    feature_set = Column(String, nullable=False, index=True)
    features    = Column(JSON, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
