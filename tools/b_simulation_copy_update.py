"""Precise text-only corrections for the already verified 2026-11-16 B batch.

No creates/deletes, status transitions, inventory, economics, procurement, model
or external customer operations. Original batch journal and mappings stay intact.
Default prints the plan. A durable intent precedes each API PUT; a separate GET
verifies it. An uncertain send is reconciled by its original ID, never re-sent.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys,time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from tools.b_erp_simulation_dataset import BATCH,PRIVATE,NATURE,profiles,check,record,fingerprint,Client
from tools.s01_teaching_dataset import TeachingDatasetClient,canonical_bytes

def updates(journal):
    check(journal['batch']==BATCH and journal['state']=='REGISTERED_AND_READABLE'
        and all(o['state']=='VERIFIED' for o in journal['operations'].values()),'ORIGINAL_BATCH_NOT_VERIFIED')
    ops=journal['operations'];result=[]
    for pi,p in enumerate(profiles()):
        original=ops['products:'+p['sku']];name=p['name'].replace('（完全仿真）','')
        result.append(dict(resource='products',id=original['erpId'],key='sku',value=p['sku'],
            fields=dict(name=name,description=p['description'].split('；仅教学')[0])))
        listing=next(o for o in ops.values() if o.get('resource')=='listings' and o['payload'].get('sku')==p['sku'])
        result.append(dict(resource='listings',id=listing['erpId'],key='listing_id',value=listing['payload']['listing_id'],fields=dict(title=name)))
        # Paid sales remain untouched, including their locked buyer fields.
        tickets=sorted((o for o in ops.values() if o.get('resource')=='customer-tickets' and o['payload']['ticket_no'].startswith(BATCH+'-T-'+str(pi+1)+'-')),key=lambda o:o['payload']['ticket_no'])
        for ti,o in enumerate(tickets):
            statement=p['tickets'][ti].replace('本地模拟物流记录','物流记录').replace('模拟包裹','包裹')
            result.append(dict(resource='customer-tickets',id=o['erpId'],key='ticket_no',value=o['payload']['ticket_no'],fields=dict(
                subject=statement,owner='客户服务组',created_time='2026-11-16T12:00:00+08:00')))
    return result


def conversations(journal):
    """Supplemental fictional customer statements; never presented as ERP text."""
    result=[]
    for o in journal['operations'].values():
        if o.get('resource')!='customer-tickets':continue
        pi,ti=map(int,o['payload']['ticket_no'].split('-')[-2:]);p=profiles()[pi-1]
        lead=p['tickets'][ti-1].replace('本地模拟物流记录','物流记录').replace('模拟包裹','包裹')
        details=(
          ['我买的是藏青色M码，试穿前没有看到明显破损。开线位置在袖口内侧，能看到缝线松开；目前已经暂停穿着，衣服还在我手上。请问需要拍哪些位置给你们核实？',
           '衣服刚拆封还没有洗，也没有正式穿过。左侧靠近下摆的接缝有一段线头，轻轻展开时能看到缝线不紧。我可以补拍平铺照片和接缝近照，请帮忙看看下一步怎么办。',
           '我按照衣标轻柔手洗，没有机洗、甩干或烘干。晾干后发现下摆侧边接缝松开，衣服还没有寄出。洗护标签和开线处都可以补照片，想请客服先核实退货申请。',
           '包裹收到后试着整理衣服，发现一侧袖口有脱线。还没有清洗或外穿，也没有自行修补。如果需要核实，我可以提供袖口内外两面的照片。',
           '穿过一次后发现肩部内侧接缝松了，衣服没有被拉扯过，也还没有寄回。希望先了解需要哪些照片和处理材料，等你们核实后再安排。',
           '试穿时发现衣服侧缝有一小段开线，我已经脱下来没有继续穿。包装和衣标都保留着，想先确认这是怎么处理，需要我补充哪些信息。',
           '第一次穿完整理时看到下摆有缝线脱落，暂时没有清洗或修补。衣服仍在我这里，能补拍全貌和局部照片，请帮我核实能否申请退换。'][ti-1]
          if pi==1 else [
           '订单里是灰色USB-C编织线。物流页面停在转运节点，没有显示签收，我本人也还没收到，所以目前无法检查商品。请先帮我核对配送进度。',
           '收到时外包装一角压扁，封口还完整。我先保留包装、没有拆开，也不知道里面的数据线是否受损。可以提供外盒和面单照片，请问应该怎样配合核实？',
           '配送已经超过页面预计时间，物流还有更新但尚未交到我手中。是想咨询包裹进度，还没有反馈充电或连接问题，请帮忙查看。'][ti-1]
          if pi==2 else [
           '买的是米白色帆布收纳袋，日常装小件用品，目前袋身和拉链都正常。我想提前了解日常污渍应该怎么清洗，能不能浸泡，以及晾晒时需要注意什么。',
           '实物颜色比我在屏幕上看到的偏暖一些，不是破损。收纳袋还没使用、没清洗，吊牌和包装都保留着。想先咨询这种情况是否有退换渠道，需要准备什么材料。'][ti-1])
        sale=next(s for s in journal['operations'].values() if s.get('resource')=='sales-orders' and s['payload']['order_sn']==o['payload']['order_sn'])
        product=journal['operations']['products:'+p['sku']]
        result.append(dict(erpTicketId=str(o['erpId']),erpStoreName=BATCH+'-SHOP',sourceNature=NATURE,
            sourceTenant='1',storeId='13',orderId=str(sale['erpId']),orderNumber=o['payload']['order_sn'],
            productId=str(product['erpId']),sku=p['sku'],at='2026-11-16T12:00:00+08:00',
            provenance='SUPPLEMENTAL_SIMULATED_CUSTOMER_STATEMENT',text=lead+'\n\n'+details,
            attachmentRefs=['simulation:'+BATCH+':ticket:'+str(o['erpId'])]))
    return result


class CopyClient(Client):
    def __init__(self,root,plan):
        super().__init__(root)
        self.allowed={f"/api/v1/{p['resource']}/{p['id']}":p['fields'] for p in plan}

    def _allow(self,method,path,*,auth):
        check(not auth and (method in {'GET','PUT'} and path in self.allowed or method=='GET' and path in {'/api/v1/me','/api/v1/data-contract'}),'COPY_OPERATION_DENIED')

    def request(self,method,path,values=None):
        self._allow(method,path,auth=False);time.sleep(.35)
        check(method!='PUT' or values==self.allowed[path],'COPY_FIELDS_DENIED')
        return record(TeachingDatasetClient.request(self,method,path,values)[0])


def execute(client,plan,root):
    root.mkdir(parents=True,exist_ok=True);path=root/'copy-journal.json'
    j=json.loads(path.read_bytes()) if path.exists() else dict(batch=BATCH,sourceNature=NATURE,planHash=fingerprint(plan),operations={})
    check(j['planHash']==fingerprint(plan),'COPY_PLAN_CHANGED')
    def save():
        tmp=path.with_suffix('.part');tmp.write_bytes(canonical_bytes(j));tmp.replace(path)
    check(client.request('GET','/api/v1/data-contract')['kind']=='synthetic','SYNTHETIC_TEACHING_ERP_REQUIRED')
    check(str(client.request('GET','/api/v1/me')['tenant_id'])=='1','TEACHING_SCOPE_DENIED')
    for item in plan:
        key=f"/api/v1/{item['resource']}/{item['id']}";before=client.request('GET',key)
        check(str(before['id'])==str(item['id']) and str(before['tenant_id'])=='1' and before[item['key']]==item['value'],'COPY_OWNERSHIP_MISMATCH')
        prior=j['operations'].get(key)
        matches=all(before.get(k)==v for k,v in item['fields'].items())
        if prior:
            check(matches,'COPY_UNKNOWN_REQUIRES_RECONCILIATION')
        elif not matches:
            j['operations'][key]=dict(state='SENDING',intent=item,before=before,at=datetime.now(timezone.utc).isoformat());save()
            client.request('PUT',key,item['fields'])
        after=client.request('GET',key)
        check(all(after.get(k)==v for k,v in item['fields'].items()),'COPY_READBACK_MISMATCH')
        # Every unrelated field except source updated_at must remain byte-equivalent.
        baseline=(prior or j['operations'].get(key) or {}).get('before',before)
        check(all(after.get(k)==v for k,v in baseline.items() if k not in {*item['fields'],'updated_at'}),'COPY_UNRELATED_FIELD_CHANGED')
        j['operations'][key]=dict(state='VERIFIED',intent=item,before=baseline,readback=after);save()
    j['state']='VERIFIED';save()
    return dict(state=j['state'],verified=len(j['operations']),batch=BATCH,noBusinessTransitions=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute-live',action='store_true');args=parser.parse_args()
    original=json.loads((PRIVATE/'journal.json').read_bytes());plan=updates(original)
    root=PRIVATE/'copy-remediation-v2';root.mkdir(parents=True,exist_ok=True)
    (root/'supplemental-conversations.json').write_bytes(canonical_bytes(conversations(original)))
    if not args.execute_live:print(json.dumps(dict(textUpdates=len(plan),conversations=12,noCreates=True,noStockChanges=True)));return
    client=CopyClient(root,plan);client.authenticate()
    result=execute(client,plan,root)
    # Only publish local narrative after all text updates have independent GETs.
    manifest=dict(schemaVersion='1.0.0',datasetId='b-s01-simulated-20261116-r1',version='customer-context-v1',
        sourceNature=NATURE,batch=BATCH,items=conversations(original))
    target=ROOT/'data/private/b-after-sales/customer-context.json'
    if target.exists():check(json.loads(target.read_bytes())==manifest,'CUSTOMER_CONTEXT_VERSION_CONFLICT')
    else:
        tmp=target.with_suffix('.part');tmp.write_bytes(canonical_bytes(manifest));tmp.replace(target)
    print(json.dumps(dict(**result,localSupplementalClaims=len(manifest['items']))))

if __name__=='__main__':main()
