from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Base class for all models
Base = declarative_base()

# Feedback model
class Feedback(Base):
    __tablename__ = 'feedback'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_input = Column(Text, nullable=False)
    model_response = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # optional: allow users to rate the answer
    comment = Column(Text, nullable=True)    # optional: allow extra comments
    timestamp = Column(DateTime, default=datetime.utcnow)

# Hazard report model
class HazardReport(Base):
    __tablename__ = 'hazard_reports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    reported_by = Column(String(100), nullable=True)  # optional name or ID
    timestamp = Column(DateTime, default=datetime.utcnow)
