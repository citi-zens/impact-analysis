from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Repository(Base):
    __tablename__ = "repositories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String)
    status = Column(String, default="Pending") # Pending, Onboarded

class AnalysisReport(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"))
    type = Column(String) # 'FR' or 'PR'
    content = Column(Text) # JSON string or text summary
    impact_score = Column(Integer)