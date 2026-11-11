"""D01—D05文档专项自检；验证模拟设计样例，不执行业务链路或真实模型。"""
from pathlib import Path
import copy,hashlib,json,re,difflib
from decimal import Decimal
from datetime import datetime
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'ai-design';REV=OUT/'review-d01-d05';SRC=ROOT/'智慧中台AI应用项目_AI模块详细开发设计文档.md'
old=(REV/'before/AI模块详细开发设计文档_v0.1.md').read_text(encoding='utf-8');new=SRC.read_text(encoding='utf-8')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sect(t,a,b):return t[t.index(a):t.index(b,t.index(a))]
checks=[]
def check(name,value,details=None):checks.append({'check':name,'status':'pass' if value else 'fail','details':details})
check('S01—S10默认选型及全部业务场景设计正文不变',sect(old,'## 14 ','## 15 ')==sect(new,'## 14 ','## 15 '))
check('总体架构与技术范式决策正文不变',sect(old,'### 2.2 ','### 2.3 ')==sect(new,'### 2.2 ','### 2.3 ') and sect(old,'## 08 ','## 09 ')==sect(new,'## 08 ','## 09 '))
pre=read(REV/'pre-revision-manifest.json')
protected=[x for x in pre if x['path'] in ['智慧中台AI应用项目_概要开发设计文档.md','智慧中台AI应用项目_需求文档草案.md','智慧中台AI应用项目_总体逻辑架构与流程设计.md','智慧中台AI应用项目_可行性分析报告.md'] or x['path'].startswith('.archify/')]
check('四份基线及已认可交互架构图所有文件原字节不变',all(sha(ROOT/x['path'])==x['sha256'] for x in protected))
unchanged=[p for p in (REV/'before/mermaid').glob('*.mmd') if p.name[:2] not in ['02','04','05']]
check('14张不相关Mermaid源及SVG均原字节不变',all(sha(p)==sha(OUT/'mermaid'/p.name) and sha(OUT/'mermaid'/p.with_suffix('.svg').name)==next(x['sha256'] for x in pre if x['path']=='ai-design/mermaid/'+p.with_suffix('.svg').name) for p in unchanged))
ex=OUT/'examples/s03-voc';cases=read(ex/'voc-three-cases.json');inputs=read(ex/'voc-input-fixture.json');schema=read(ex/'voc-output-schema.json')
Draft202012Validator.check_schema(schema);validator=Draft202012Validator(schema)
required={'schemaVersion','logicalCallId','attemptId','taskRef','queryRef','planVersion','participantId','snapshotId','principalRef','purpose','policyContextRef','deploymentRef','promptRef','contextBundleRef','outputSchemaRef','requiredCapabilities','toolSpecRefs','parametersRef','allowanceRef','deadline','cachePolicyRef','traceId','parentSpanId'}
canonical=[];resolved=[];casechecks=[]
for c in cases['cases']:
    suffix={'success':'success','technical-failure':'failure','semantic-unknown':'unknown'}[c['caseId']]
    q=read(ex/(suffix+'-model-request.json'));p=read(ex/(suffix+'-provider-request.json'));ctx=read(ex/(suffix+'-context-bundle.json'));item=next(x for x in inputs['items'] if x['caseId']==c['caseId'])
    ok=set(q)==required and q['schemaVersion']=='0.2' and set(q['taskRef'])=={'tenantId','taskId'} and q['taskRef']['taskId']==c['taskId'] and q['planVersion']=='plan-voc-1' and q['queryRef'] is None
    ok=ok and all(set(q[k])=={'id','version'} for k in ['promptRef','parametersRef','outputSchemaRef','policyContextRef','deploymentRef','cachePolicyRef']) and q['toolSpecRefs']==[] and datetime.fromisoformat(q['deadline'].replace('Z','+00:00')).utcoffset().total_seconds()==0
    canonical.append(ok)
    def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    payload=p['payload'];control=p['control'];user=json.loads(payload['messages'][-1]['content'])
    resolved.append(payload['outputSchema']==schema and payload['toolSpecs']==[] and payload['parameters']=={'temperature':0,'maxOutputTokens':128} and control['attemptId']==q['attemptId'] and control['timeoutMs']==20000 and user['feedbackText']==item['text'] and user['contentId']==item['contentId'] and control['digests']['toolSpecsDigest']==digest([]) and control['digests']['contextDigest']==digest(ctx))
    usage=c['usage'];settle=c['budgetSettlement'];reserve=Decimal(cases['pricing']['reservedPerAttempt'])
    if c['technicalStatus']=='SUCCESS':
        errs=list(validator.iter_errors(c['validatedObject']));v=c['validatedObject']['items'][0]
        ok=not errs and v['contentId']==item['contentId'] and c['understandingRef'] is not None
        n=len(item['text'].encode('utf-16-le'))//2
        ok=ok and all(0<=s['start']<s['end']<=n for s in v['spans'])
        if c['caseId']=='success':ok=ok and item['text'][0:7]=='物流一直没更新' and v['semanticStatus']=='CLASSIFIED'
        else:ok=ok and v['semanticStatus']=='UNKNOWN' and all(v[k] is None for k in ['theme','intent','confidence']) and v['unknownReason']=='INSUFFICIENT_CONTEXT'
        amount=(Decimal(usage['inputTokens'])*Decimal(cases['pricing']['inputPerMillion'])+Decimal(usage['outputTokens'])*Decimal(cases['pricing']['outputPerMillion']))/Decimal(1000000)
        ok=ok and amount==Decimal(usage['actualCost'])==Decimal(settle['retained']) and amount+Decimal(settle['released'])==reserve
    else:
        ok=c['error']['code']=='TIMEOUT' and c['error']['stage']=='SENT' and c['validatedObject'] is None and c['understandingRef'] is None and c['derivedEvidenceId'] is None and usage['status']=='UNKNOWN' and all(usage[k] is None for k in ['inputTokens','outputTokens','actualCost']) and Decimal(settle['retained'])==reserve and Decimal(settle['released'])==0
    casechecks.append({'caseId':c['caseId'],'valid':ok})
check('三份ModelRequest使用唯一字段集合及类型',all(canonical))
check('三份解析后ProviderRequest与Prompt/Context/Schema/工具摘要一致',all(resolved))
check('三例Schema/语义位置/UNKNOWN区别及模拟Decimal结算自洽',all(x['valid'] for x in casechecks),casechecks)
bad=copy.deepcopy(cases['cases'][2]['validatedObject']);bad['items'][0]['theme']='LOGISTICS'
badextra=copy.deepcopy(cases['cases'][0]['validatedObject']);badextra['items'][0]['approve']=True
check('文档输出Schema拒绝UNKNOWN假确定值和额外危险字段',bool(list(validator.iter_errors(bad))) and bool(list(validator.iter_errors(badextra))))
loop=sect(new,'### 7.2 ','### 7.3 ')
check('Loop首轮与反馈轮均明确预留/Provider/G02/结算且Runtime只回Handler',all(x in loop for x in ['reserve attempt-1','reserve feedback-attempt','A->>M:','A->>L:','settle feedback-attempt','R-->>H: RunOutcome','H-->>O: 仅Handler生成DomainResult']) and not re.search(r'R-->>O:.*DomainResult',loop))
check('WAIT/VOC验收断言覆盖',all(f'| WAIT-{n:02d} ' in new for n in range(1,9)) and all(f'| VOC-{n:02d} ' in new for n in range(1,11)))
check('OFF无设施与实际输出分类门禁在正文/缓存图一致',all(x in new for x in ['OFF是“没有响应缓存执行路径”','outputClassification','UNVERIFIABLE','输入分类仅决定','OFF，不创建缓存设施','实际输出满足当前用户交付权限与安全规则']))
diff=''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='AI模块详细开发设计文档_v0.1.md',tofile='AI模块详细开发设计文档_v0.2.md',n=3))
(REV/'AI模块详细设计_v0.1_to_v0.2.diff').write_text(diff,encoding='utf-8')
report={'document':'AIH-AI-LLD-001 v0.2','status':'pass' if all(x['status']=='pass' for x in checks) else 'fail','checks':checks,'scope':'Only document/fixture/schema/arithmetic/diff consistency; no business implementation or model execution','sourceSha256':sha(SRC),'independentReview':'pending'}
(REV/'revision-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'checks':len(checks),'failures':[x for x in checks if x['status']=='fail']},ensure_ascii=False))
raise SystemExit(0 if report['status']=='pass' else 1)
