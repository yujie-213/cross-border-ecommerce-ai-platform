"""只读取Markdown任务台账的文档工具；不创建业务任务或改变任务状态。"""
from pathlib import Path
import hashlib,json,re

ROOT=Path(__file__).resolve().parents[2]
LEDGER=ROOT/'docs/TASKS.md'
STATUSES=('TODO','IN_PROGRESS','BLOCKED','REVIEW','ACCEPTED')

def read_tasks():
    text=LEDGER.read_text(encoding='utf-8')
    return [json.loads(m) for m in re.findall(r'```json\s*\n(.*?)```',text,re.S)]

def source_hash():return hashlib.sha256(LEDGER.read_bytes()).hexdigest()

def cycles(tasks):
    index={t['id']:t for t in tasks};seen=set();active=[];found=[]
    def visit(k):
        if k in active:found.append(active[active.index(k):]+[k]);return
        if k in seen:return
        active.append(k)
        for d in index[k].get('dependsOn',[]):
            if d in index:visit(d)
        active.pop();seen.add(k)
    for k in index:visit(k)
    return found
