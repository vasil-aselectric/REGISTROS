from sqlalchemy import Column, Float, Integer, String

from .database import Base


class MinuteAvg(Base):
    __tablename__ = "minute_avg"

    # tu script guarda minute_iso como "YYYY-MM-DDTHH:MM"
    minute_iso = Column(String, primary_key=True)

    avg_ch0 = Column(Float, nullable=False)
    avg_ch1 = Column(Float, nullable=False)
    avg_ch2 = Column(Float, nullable=False)
    avg_ch3 = Column(Float, nullable=False)

    samples_count = Column(Integer, nullable=False)
    computed_at_iso = Column(String, nullable=False)