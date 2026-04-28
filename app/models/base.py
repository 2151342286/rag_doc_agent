from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import  DateTime,func
class Base(DeclarativeBase):
    creat_time:Mapped[datetime] = mapped_column(
        DateTime, #参数类型
        insert_default= func.now(), # 默认插入值（sql层面）
        comment="创建时间" # 注释
    )
    update_time:Mapped[datetime] = mapped_column(
        DateTime,
        insert_default= func.now(), 
        onupdate= func.now(), # 更新时自动更新为当前时间
        comment="更新时间"
    )