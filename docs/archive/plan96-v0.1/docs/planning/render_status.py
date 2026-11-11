"""从唯一TASKS台账生成只读进度/依赖视图，不写任务状态。"""
import sys
sys.dont_write_bytecode=True
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
from collections import Counter
import argparse,json
from task_io import ROOT,LEDGER,STATUSES,read_tasks,source_hash

def expected(tasks):
    sh=source_hash();index={t['id']:t for t in tasks};counts=Counter(t['status'] for t in tasks)
    md=f'# 项目状态视图（自动生成）\n\n> 唯一源：[TASKS.md](../TASKS.md)；sourceSha256=`{sh}`。禁止手工编辑，本视图不构成实施授权。\n\n'
    md+=f"任务总数：{len(tasks)}。"+'；'.join(f'{s} {counts[s]}' for s in STATUSES)+'。\n\n这些是任务状态计数，不是业务完成比例/工期完成率。当前事实、Git与审查边界见[HANDOFF](../HANDOFF.md)。\n\n'
    md+='| 阶段 | 总数 | '+' | '.join(STATUSES)+' |\n|---|---|'+'---|'*len(STATUSES)+'\n'
    for stage in ['M0','M1','M2','M3','M4']:
        ts=[t for t in tasks if t['stage']==stage];c=Counter(t['status'] for t in ts)
        md+='| '+stage+' | '+str(len(ts))+' | '+' | '.join(str(c[s]) for s in STATUSES)+' |\n'
    md+='\n## 已领取或待审任务（只读）\n\n'
    active=[t for t in tasks if t['status'] in ['IN_PROGRESS','BLOCKED','REVIEW']]
    for t in active:md+=f"- {t['id']} {t['title']}：{t['status']}；owner={t['ownerRole']}；实际执行者={t['assignee'] or '未指派'}。\n"
    if not active:md+='无。\n'
    md+='\n## 硬依赖已满足的TODO候选（仍需入口签认/授权/所有权）\n\n'
    ready=[t for t in tasks if t['status']=='TODO' and all(index.get(d,{}).get('status')=='ACCEPTED' for d in t['dependsOn'])]
    for t in ready:
        md+=f"- {t['id']} {t['title']}。入口："+'；'.join(t['entryConditions'])+'。\n'
    if not ready:md+='暂无。\n'
    md+='\n## 任务索引（状态只从台账生成）\n\n| ID | 阶段/轨道 | 任务 | 状态 | 直接依赖 |\n|---|---|---|---|---|\n'
    for t in tasks:md+=f"| {t['id']} | {t['stage']}/{t['track']} | {t['title']} | {t['status']} | {', '.join(t['dependsOn']) or '无硬依赖；仍检查入口'} |\n"
    md+='\n完整细项执行 `python docs/planning/render_status.py --task <ID>` 提取；不复制成另一个可修改台账。\n'
    lines=['%% Generated from docs/TASKS.md; sourceSha256='+sh,'flowchart TB']
    for stage in ['M0','M1','M2','M3','M4']:
        lines.append(f'  subgraph stage_{stage}["{stage}"]')
        for t in tasks:
            if t['stage']==stage:lines.append(f"    {t['id'].replace('-','_')}[{json.dumps(t['id']+' '+t['title'],ensure_ascii=False)}]")
        lines.append('  end')
    for t in tasks:
        for d in t['dependsOn']:lines.append(f"  {d.replace('-','_')} --> {t['id'].replace('-','_')}")
    lines+=['  %% Edges show hard dependencies only; entryConditions and real permissions must also be checked.']
    return {ROOT/'docs/generated/STATUS.md':md,ROOT/'docs/generated/DEPENDENCIES.mmd':'\n'.join(lines)+'\n'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');ap.add_argument('--task');args=ap.parse_args();tasks=read_tasks()
    if args.task:
        t=next((t for t in tasks if t['id']==args.task),None)
        if not t:raise SystemExit('Unknown task ID')
        print(json.dumps(t,ensure_ascii=False,indent=2));raise SystemExit(0)
    stale=[]
    for p,text in expected(tasks).items():
        if args.check:
            if not p.exists() or p.read_text(encoding='utf-8')!=text:stale.append(p.relative_to(ROOT).as_posix())
        else:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
    print(json.dumps({'mode':'check' if args.check else 'generate','tasks':len(tasks),'sourceSha256':source_hash(),'stale':stale},ensure_ascii=False))
    raise SystemExit(1 if stale else 0)
