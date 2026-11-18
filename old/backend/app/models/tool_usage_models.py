from datetime import date

from sqlalchemy import Column, Date, Integer, String, Index, UniqueConstraint

from app.models.config_models import Base


class ToolDailyUsage(Base):
    __tablename__ = "tool_daily_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False)
    tool_name = Column(String(100), nullable=False)
    usage_date = Column(Date, nullable=False, default=date.today)
    count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "tool_name", "usage_date", name="uniq_tool_daily_usage"),
        Index("idx_tool_daily_usage_user_date", "user_id", "usage_date"),
        Index("idx_tool_daily_usage_tool_date", "tool_name", "usage_date"),
    )
