"""Bound request bytes before multipart/JSON parsing, including chunked bodies."""
from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self,app,upload_limit):
        self.app,self.upload_limit=app,upload_limit

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] not in ('POST','PATCH','PUT'):
            return await self.app(scope,receive,send)
        limit=self.upload_limit+65536 if scope['path']=='/api/documents' else 262144
        headers=dict(scope.get('headers',[]))
        try: declared=int(headers.get(b'content-length',b'0'))
        except ValueError: declared=0
        async def reject():
            response=JSONResponse({'detail':'Request exceeds the size limit','code':'request_too_large'},status_code=413)
            await response(scope,receive,send)
        if declared>limit: return await reject()
        chunks=[]; total=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect': return
            part=message.get('body',b''); total+=len(part)
            if total>limit: return await reject()
            chunks.append(part)
            if not message.get('more_body',False): break
        body=b''.join(chunks)
        delivered=False
        async def replay():
            nonlocal delivered
            if delivered: return await receive()
            delivered=True
            return {'type':'http.request','body':body,'more_body':False}
        await self.app(scope,replay,send)
