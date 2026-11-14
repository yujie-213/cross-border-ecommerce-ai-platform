"""Bounded, resumable teaching ERP reads. Raw responses stay private."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re,time
from urllib.parse import urlencode
from commerce_hub.adapters.erp import ERPConfig,ERPError,AUTH_PATH,READ_GET,https_transport


def now():return datetime.now(timezone.utc).isoformat()


class V2Reader:
    def __init__(self,config,root,checkpoint,check,*,transport=https_transport,request_limit=400,page_size=200,max_records=50000,sleeper=time.sleep):
        if not 1<=request_limit<=2000 or not 1<=page_size<=200 or not 1<=max_records<=100000:raise ValueError('V2_READ_LIMIT_INVALID')
        self.config,self.root,self.checkpoint,self.check=config,Path(root),checkpoint,check
        self.transport,self.sleeper=transport,sleeper
        self.limit,self.page_size,self.max_records=request_limit,page_size,max_records
        self.state=checkpoint.load()
        if 'startedAt' not in self.state and not self.state.get('resources'):
            self.state['admissionVersion']='s01-runtime-v1'
            self.state['decisionVersion']='s01-product-demand-v1'
        self.state.setdefault('resources',{});self.state.setdefault('events',[])
        self.state.setdefault('startedAt',now());self.root.mkdir(parents=True,exist_ok=True)
        self.token=config.access_token

    def request(self,path,parameters=None,*,auth=False):
        if not (auth and path==AUTH_PATH or path in READ_GET or path=='/api/v1/me'
            or re.fullmatch(r'/api/v1/(sales-workflow|suppliers)/[1-9][0-9]{0,19}',path)):
            raise ERPError('V2_OPERATION_NOT_ALLOWLISTED')
        for attempt in range(1 if auth else 2):
            self.check()
            if self.state['requestCount']>=self.limit:raise ERPError('V2_REQUEST_BUDGET_EXHAUSTED')
            self.state['requestCount']+=1
            e=dict(method='POST' if auth else 'GET',path=path,at=now(),attempt=attempt+1)
            self.state['events'].append(e);self.checkpoint.save(self.state)
            headers={'Accept':'application/json'}
            params=parameters or {}
            body=None
            if auth:
                body=json.dumps(dict(appId=self.config.username,appSecret=self.config.password)).encode()
                headers['Content-Type']='application/json'
            else:headers['Authorization']='Bearer '+self.token
            target=path+('?' + urlencode(params,doseq=True) if params else '')
            self.sleeper(self.config.interval if not attempt else 1)
            try:
                status,raw=self.transport(e['method'],target,headers,body,self.config)
                e['httpStatus']=status;e['completedAt']=now()
                if not auth:
                    digest=hashlib.sha256(raw).hexdigest();p=self.root/(digest+'.json')
                    if p.exists():
                        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ERPError('V2_CAPTURE_DIGEST_MISMATCH')
                    else:
                        temporary=p.with_suffix('.part')
                        temporary.write_bytes(raw);temporary.replace(p)
                    e.update(sha256=digest,file=p.name)
                self.checkpoint.save(self.state)
                if status!=200:raise ERPError('ERP_AUTH_REJECTED' if status in {401,403} else 'ERP_503' if status in {503,504} else 'ERP_HTTP_ERROR',status)
                data=json.loads(raw)
                if not isinstance(data,dict):raise ERPError('ERP_INVALID_ENVELOPE')
                self.check();return data,e
            except (TimeoutError,ConnectionError,OSError) as exc:
                e['error']='ERP_TIMEOUT' if isinstance(exc,TimeoutError) else 'ERP_TRANSPORT_FAILURE'
                self.checkpoint.save(self.state)
                if not attempt and not auth:continue
                raise ERPError(e['error']) from None
            except ERPError as exc:
                e['error']=exc.code;self.checkpoint.save(self.state)
                if not attempt and not auth and exc.code=='ERP_503':continue
                raise
            except (ValueError,UnicodeError):raise ERPError('ERP_INVALID_JSON') from None

    def authenticate(self,tenant):
        if not self.token:
            data,_=self.request(AUTH_PATH,auth=True)
            self.token=data.get('data',{}).get('access_token')
            if not isinstance(self.token,str) or not 1<=len(self.token)<=8192 or any(c in self.token for c in '\r\n'):raise ERPError('ERP_AUTH_ENVELOPE_REJECTED')
        me,_=self.request('/api/v1/me')
        me=me.get('data',me)
        if str(me.get('tenant_id'))!=str(tenant):raise ERPError('V2_SOURCE_TENANT_MISMATCH')
        policy={k:me.get(k) for k in ['tenant_id','id','user_id','account_id','username','role','permissions','store_ids','warehouse_ids','resource_permissions']}
        digest=hashlib.sha256(json.dumps(policy,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        previous=self.state.get('sourceAuthorizationDigest')
        if previous is not None and previous!=digest:raise ERPError('V2_SOURCE_AUTHORIZATION_CHANGED')
        self.state['sourceAuthorizationDigest']=digest;self.checkpoint.save(self.state)

    def resource(self,name,path,parameters=None,*,detail=False):
        parameters=parameters or {}
        binding=dict(path=path,parameters=parameters,detail=detail)
        entry=self.state['resources'].setdefault(name,dict(binding=binding,pages=[],complete=False,total=None))
        if entry['binding']!=binding:raise ERPError('V2_ACQUISITION_PARAMETERS_CHANGED')
        rows=[];ids=set()
        for page in entry['pages']:
            raw=(self.root/page['file']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=page['sha256']:raise ERPError('V2_CAPTURE_DIGEST_MISMATCH')
            data=json.loads(raw);values=[data] if detail else data['items']
            rows.extend(values)
        for r in rows:
            key=str(r.get('id'))
            if key in ids:raise ERPError('ERP_DUPLICATE_RECORD')
            ids.add(key)
        if entry['complete']:return dict(rows=rows,complete=True,total=entry['total'],observedAt=entry.get('observedAt'),bindingDigest=hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest())
        entry.pop('error',None)
        try:
            while len(rows)<=self.max_records:
                size=min(self.page_size,100) if path=='/api/v1/supplier-quotes' else self.page_size
                if path=='/api/v1/stock/ledger' and self.state.get('admissionVersion')=='s01-runtime-v1':
                    size=min(size,25)
                query={} if detail else dict(parameters,limit=size,offset=len(rows))
                data,event=self.request(path,query)
                values,total=([data],1) if detail else (data.get('items'),data.get('total'))
                if not isinstance(values,list) or type(total) is not int or total<0 or len(values)>self.page_size or any(not isinstance(r,dict) or not detail and r.get('id') is None for r in values):raise ERPError('ERP_INVALID_PAGE')
                if entry['total'] is not None and entry['total']!=total:raise ERPError('ERP_PAGINATION_DRIFT')
                page_ids=[path if detail else str(r['id']) for r in values]
                if len(set(page_ids))!=len(page_ids) or ids.intersection(page_ids):raise ERPError('ERP_DUPLICATE_RECORD')
                if len(rows)+len(values)>total or not values and len(rows)<total:raise ERPError('ERP_PAGINATION_INCOMPLETE')
                if len(rows)+len(values)>self.max_records:raise ERPError('V2_RECORD_LIMIT_REACHED')
                rows.extend(values);ids.update(page_ids)
                entry.update(total=total,complete=len(rows)==total,observedAt=event['completedAt'])
                entry['pages'].append({k:event[k] for k in ['sha256','file']});self.checkpoint.save(self.state)
                if entry['complete']:break
        except ERPError as exc:
            if exc.code in {'ERP_AUTH_REJECTED','V2_CAPTURE_DIGEST_MISMATCH'}:raise
            entry.update(complete=False,error=exc.code,httpStatus=exc.status);self.checkpoint.save(self.state)
        return dict(rows=rows,complete=entry['complete'],total=entry['total'],observedAt=entry.get('observedAt'),
            bindingDigest=hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest(),**{k:entry[k] for k in ['error','httpStatus'] if k in entry})

    def receipt(self):
        return dict(startedAt=self.state['startedAt'],completedAt=(self.state['events'][-1].get('completedAt') or self.state['events'][-1]['at']) if self.state['events'] else self.state['startedAt'],requestCount=self.state['requestCount'],requestLimit=self.limit,
            resources={k:{p:v for p,v in e.items() if p!='binding'} for k,e in self.state['resources'].items()},events=self.state['events'],
            atomicAcrossInterfaces=False,businessMutations=0,**({'monitoring':self.state['monitoring']} if self.state.get('monitoring') else {}))
