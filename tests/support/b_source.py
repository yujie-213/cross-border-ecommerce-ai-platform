"""Synthetic B source transport. Never used by the daily product launcher."""
import json
from urllib.parse import urlsplit,parse_qs
from tests.support.v2 import SyntheticERP

class BSourceERP(SyntheticERP):
    def __init__(self):
        super().__init__(3)
        self.voice_events=[];self.voice_writes=0;self.voice_failure=None;self.voice_hide_history=False
        self.data['products'][0]['category']='APPAREL'
        self.tickets=[dict(id=91,tenant_id=1,ticket_no='SYN-TICKET-91',store_name='Synthetic Store',subject='上衣尺码需核实',order_sn='SYN-ORDER',platform='TEACHING')]
        self.data['sales']=[dict(id=81,tenant_id=1,order_sn='SYN-ORDER',store_name='Synthetic Store',item_list=[dict(sku='V2-SKU-0')],payment_status='已支付')]
        self.voices=dict(reviews=[dict(id=71,store_id=1,store_name='Synthetic Store',sku='V2-SKU-0',title='上衣评价',body='尺寸偏小，请核对描述',rating=2,business_date='2026-09-05',platform='TEACHING',related_id=99999)],
            feedback=[dict(id=72,store_id=1,store_name='Synthetic Store',order_id=81,body='包装需要改善',rating=3,business_date='2026-09-05',platform='TEACHING')])
    def transport(self,method,target,headers,body,config):
        path=urlsplit(target).path;q={k:v[0] for k,v in parse_qs(urlsplit(target).query).items()}
        def out(v):return 200,json.dumps(v,ensure_ascii=False).encode()
        if path=='/api/v1/customer-tickets':return out(dict(items=self.tickets,total=len(self.tickets)))
        if path.startswith('/api/v1/customer-tickets/'):return out(next(t for t in self.tickets if str(t['id'])==path.split('/')[-1]))
        if path=='/api/v1/customer-voice':
            if method=='POST':
                self.voice_writes+=1
                payload=json.loads(body)
                if self.voice_failure=='reject':return 403,b'{}'
                if self.voice_failure=='before':raise TimeoutError()
                prior=next((r for r in self.voice_events if r['request_key']==payload['request_key']),None)
                if prior:return out(dict(data=prior))
                rows=[r for r in self.voice_events if r['kind']==payload['kind'] and r['record_id']==payload['record_id']]
                version=max((r['version'] for r in rows),default=0)
                if payload['expected_version']!=version:return 409,b'{}'
                event=dict(id=len(self.voice_events)+1,kind=payload['kind'],record_id=payload['record_id'],version=version+1,
                    handling_status=payload['handling_status'],note=payload['note'],actor='synthetic-actor',created_at='2026-11-17T12:00:00Z',request_key=payload['request_key'])
                self.voice_events.append(event)
                if self.voice_failure=='after':raise TimeoutError()
                return 201,json.dumps(dict(data=event),ensure_ascii=False).encode()
            if q.get('history')=='1':
                rows=[] if self.voice_hide_history else [r for r in self.voice_events if r['kind']==q['kind'] and str(r['record_id'])==q.get('record_id')]
                return out(dict(items=rows,total=len(rows)))
            rows=self.voices[q['kind']]
            if q.get('record_id'):rows=[r for r in rows if str(r['id'])==q['record_id']]
            return out(dict(items=rows,total=len(rows)))
        if path.startswith('/api/v1/sales-workflow/'):return out(dict(data={}))
        return super().transport(method,target,headers,body,config)
