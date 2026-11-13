"""Reuse the accepted official DeepSeek transport; persist only private call artifacts.

O01/G02 own all task and shared-authorization accounting. This adapter has no
second budget ledger and cannot reset O01 allowance on process restart.
"""
import json
from pathlib import Path
from commerce_hub.adapters.models.evaluation import EvaluationProvider,EvaluationAuthorization
from decimal import Decimal

AUTHORIZATION_ID='s01-online-20261113-r1'
MVP_AUTHORIZATION_ID='s01-mvp-20261113-p1p2'

class OnlineDeepSeekProvider:
    def __init__(self,settings,private_root, *, authorization_id=AUTHORIZATION_ID):
        if authorization_id not in {AUTHORIZATION_ID, MVP_AUTHORIZATION_ID}:
            raise ValueError('UNKNOWN_ONLINE_MODEL_AUTHORIZATION')
        owned = authorization_id == MVP_AUTHORIZATION_ID
        self.delegate=EvaluationProvider(settings,authorization=EvaluationAuthorization(authorization_id,
            None if owned else 10, None if owned else Decimal('1'),Decimal('.05')))
        self.private_root=Path(private_root)

    def describe_capabilities(self):return self.delegate.describe_capabilities()
    def preflight(self,payload,cost):return self.delegate.preflight(payload,cost)

    def invoke(self,request):
        owner=request.control.taskRef
        path=self.private_root/owner.tenantId/owner.taskId
        path.mkdir(parents=True,exist_ok=True)
        stem=path/request.control.logicalCallId
        # A second provider process cannot overwrite a possibly sent artifact.
        with Path(str(stem)+'-request.json').open('x',encoding='utf-8',newline='\n') as f:
            json.dump(request.model_dump(mode='json'),f,ensure_ascii=False,indent=2)
        result=self.delegate.invoke(request)
        with Path(str(stem)+'-response.json').open('x',encoding='utf-8',newline='\n') as f:
            json.dump(result.model_dump(mode='json'),f,ensure_ascii=False,indent=2)
        return result
