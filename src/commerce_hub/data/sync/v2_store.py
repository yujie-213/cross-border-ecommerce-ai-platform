"""D01 task-scoped acquisition checkpoints, never a global cache."""
from sqlalchemy import Table,Column,String,Integer,JSON,MetaData,select,insert,update

metadata=MetaData()
acquisitions=Table('d01_v2_acquisitions',metadata,
    Column('tenant_id',String(64),primary_key=True),Column('task_id',String(64),primary_key=True),
    Column('request_count',Integer,nullable=False),Column('content',JSON,nullable=False),
    mysql_engine='InnoDB',mysql_charset='utf8mb4',mysql_collate='utf8mb4_bin')


class AcquisitionCheckpoint:
    def __init__(self,context):self.context=context
    def load(self):
        def op(c):
            row=c.execute(select(acquisitions).filter_by(tenant_id=self.context.task['tenant_id'],task_id=self.context.task['task_id'])).mappings().first()
            if row:return dict(row['content'],requestCount=row['request_count'])
            c.execute(insert(acquisitions).values(tenant_id=self.context.task['tenant_id'],task_id=self.context.task['task_id'],request_count=0,content={}))
            return dict(requestCount=0)
        return self.context.commit_data(op)
    def save(self,value):
        content={k:v for k,v in value.items() if k!='requestCount'}
        self.context.commit_data(lambda c:c.execute(update(acquisitions).filter_by(tenant_id=self.context.task['tenant_id'],task_id=self.context.task['task_id'])
            .values(request_count=value['requestCount'],content=content)))
