"""从唯一TASKS生成只读状态；不改变任务状态。"""
import sys
sys.dont_write_bytecode=True
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
from collections import Counter
import argparse,json
from task_io import ROOT,STATUSES,read_tasks,source_hash

def expected(tasks):
    h=source_hash();index={t['id']:t for t in tasks};counts=Counter(t['status'] for t in tasks)
    md=f'# 近期任务视图（自动生成）\n\n唯一源：[TASKS](../TASKS.md)，SHA-256=`{h}`。不要手工编辑；候选不是执行授权。\n\n'
    md+='任务 '+str(len(tasks))+' 项；'+'；'.join(f'{s} {counts[s]}' for s in STATUSES)+'。\n\n'
    md+='| 轨道 | 数量 | TODO | IN_PROGRESS | BLOCKED | REVIEW | ACCEPTED |\n|---|---|---|---|---|---|---|\n'
    for st in ['SETUP','A','B','C','D']:
        sub=[t for t in tasks if t['stage']==st];c=Counter(t['status'] for t in sub)
        md+='| '+st+' | '+str(len(sub))+' | '+' | '.join(str(c[s]) for s in STATUSES)+' |\n'
    md+='\n## 当前活动记录\n\n'
    for t in tasks:
        if t['status'] in ['IN_PROGRESS','REVIEW','BLOCKED']:md+=f"- {t['id']} {t['title']}：{t['status']}；实际执行者={t['assignee'] or '未指派'}。\n"
    md+='\n## 全部近期记录\n\n| ID | 内容 | 状态 | 直接依赖 |\n|---|---|---|---|\n'
    for t in tasks:md+=f"| {t['id']} | {t['title']} | {t['status']} | {', '.join(t['dependsOn']) or '无；仍核对入口指令'} |\n"
    md+='\nD-S01-01下一条指令即可进入；不依赖A/B/C/S02。C任务仅实际用途需要时选择。旧96项只读映射见TASK_MAPPING，不汇入当前任务完成率。\n'
    lines=['%% TASKS sourceSha256='+h,'flowchart TB']
    for t in tasks:lines.append('  '+t['id'].replace('-','_')+'['+json.dumps(t['id']+' '+t['title'],ensure_ascii=False)+']')
    for t in tasks:
        for d in t['dependsOn']:lines.append('  '+d.replace('-','_')+' --> '+t['id'].replace('-','_'))
    return {ROOT/'docs/generated/STATUS.md':md,ROOT/'docs/generated/DEPENDENCIES.mmd':'\n'.join(lines)+'\n'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--task');a=p.parse_args();ts=read_tasks()
    if a.task:
        t=next((t for t in ts if t['id']==a.task),None)
        if not t:raise SystemExit('Unknown ID')
        print(json.dumps(t,ensure_ascii=False,indent=2));raise SystemExit(0)
    bad=[]
    for path,text in expected(ts).items():
        if a.check:
            if not path.exists() or path.read_text(encoding='utf-8')!=text:bad.append(path.relative_to(ROOT).as_posix())
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
    print(json.dumps({'tasks':len(ts),'stale':bad},ensure_ascii=False));raise SystemExit(bool(bad))
