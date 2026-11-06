"""Explicit direct REST diagnostics for two official Google API routes.

No SDK dependency, proxy bypass, redirect following, account changes or files.
py -m examples.gemini_routes --model gemini-3.8-flash --timeout-seconds 45
"""

import argparse
from dataclasses import asdict,dataclass
import getpass
import json
import math
import os
import re
import sys
import time
from urllib.error import HTTPError,URLError
from urllib.request import Request,build_opener,HTTPRedirectHandler

from app.services.llm import safe_provider_message


PROMPT="Reply only with OK. This is a connection test."


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


@dataclass(frozen=True)
class RouteResult:
    route:str
    http_status:int | None
    elapsed_seconds:float
    usable_text:bool
    response_status:str | None
    detail:str | None


def _usable(route,data):
    if not isinstance(data,dict):return False
    if route=="interactions":
        if data.get("status")!="completed":return False
        for step in data.get("steps",[]):
            if isinstance(step,dict) and step.get("type")=="model_output":
                if any(isinstance(p,dict) and p.get("type")=="text" and isinstance(p.get("text"),str)
                       and p["text"].strip() for p in step.get("content",[])):return True
        return False
    for candidate in data.get("candidates",[]):
        if not isinstance(candidate,dict):continue
        for part in candidate.get("content",{}).get("parts",[]):
            if isinstance(part,dict) and not part.get("thought") and isinstance(part.get("text"),str) and part["text"].strip():return True
    return False


def probe_route(route,key,model,timeout_seconds,opener=None):
    if route not in ("interactions","generateContent"):raise ValueError("Unknown probe route.")
    if not re.fullmatch(r"[A-Za-z0-9._-]+",model):raise ValueError("Use a model ID, not a URL or key.")
    if not math.isfinite(timeout_seconds) or not 5<=timeout_seconds<=60:raise ValueError("Timeout must be 5 to 60 seconds.")
    if route=="interactions":
        url="https://generativelanguage.googleapis.com/v1beta/interactions"
        payload={"model":model,"input":PROMPT,"store":False}
    else:
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload={"contents":[{"parts":[{"text":PROMPT}]}],"generationConfig":{"maxOutputTokens":512}}
    request=Request(url,data=json.dumps(payload).encode(),method="POST",
                    headers={"Content-Type":"application/json","x-goog-api-key":key})
    opener=opener or build_opener(NoRedirect())
    start=time.monotonic()
    code=None
    try:
        with opener.open(request,timeout=timeout_seconds) as response:
            code=response.status
            raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise ValueError("Diagnostic response exceeds size limit.")
        data=json.loads(raw)
        usable=_usable(route,data)
        state=data.get("status") if isinstance(data,dict) and isinstance(data.get("status"),str) else None
        return RouteResult(route,code,round(time.monotonic()-start,2),usable,state,
                           None if usable else "Response received but no completed usable text; this route remains inconclusive.")
    except HTTPError as exc:
        code=exc.code
        try:
            raw=exc.read(65536)
            data=json.loads(raw)
            error=data.get("error",{}) if isinstance(data,dict) else {}
            message=error.get("message","HTTP request rejected.") if isinstance(error,dict) else "HTTP request rejected."
        except Exception:message="HTTP request rejected; no readable JSON error detail."
        detail=safe_provider_message(RuntimeError(str(message)),key)
    except (URLError,TimeoutError,OSError) as exc:
        detail="Network/transport failure: "+safe_provider_message(exc,key)
    except Exception as exc:
        detail="Diagnostic response could not be interpreted: "+safe_provider_message(exc,key)
    return RouteResult(route,code,round(time.monotonic()-start,2),False,None,detail)


def main():
    parser=argparse.ArgumentParser(description="Two real direct REST connection probes; no SDK or project documents.")
    parser.add_argument("--model",required=True)
    parser.add_argument("--timeout-seconds",type=float,default=45)
    args=parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._-]+",args.model) or not math.isfinite(args.timeout_seconds) or not 5<=args.timeout_seconds<=60:
        parser.error("Supply a model ID and a timeout from 5 to 60 seconds.")
    key=os.getenv("GEMINI_API_KEY","").strip()
    try:
        if not key:
            if not sys.stdin.isatty():parser.exit(1,"Run directly in interactive PowerShell for hidden key entry.\n")
            key=getpass.getpass("Paste Gemini API key (input hidden), then press Enter: ").strip()
        if not key:parser.exit(1,"No key entered; nothing sent.\n")
        print("DIRECT GOOGLE REST PROBES: two real requests, fictional prompt, no retries.")
        print("SDK base-URL override present:",any(os.getenv(name) for name in ("GOOGLE_GEMINI_BASE_URL","GOOGLE_VERTEX_BASE_URL")))
        print("Proxy environment present:",any(os.getenv(name) for name in ("HTTPS_PROXY","HTTP_PROXY","ALL_PROXY","https_proxy","http_proxy","all_proxy")))
        print("Values are hidden. Existing system proxy configuration is not changed or bypassed.")
        results=[]
        for route in ("interactions","generateContent"):
            print("Testing route:",route,flush=True)
            result=probe_route(route,key,args.model,args.timeout_seconds)
            results.append(result)
            print(json.dumps(asdict(result),ensure_ascii=False,indent=2),flush=True)
        print("REST PROBE SUMMARY")
        for r in results:print(f"{r.route}: {'TEXT RECEIVED' if r.usable_text else 'NOT VERIFIED'}; HTTP={r.http_status}; elapsed={r.elapsed_seconds}s")
        print("A working route does NOT verify structured knowledge/content/clarity services.")
        print("No key, response body or application records saved. Do not paste credentials into chat.")
        return 0 if any(r.usable_text for r in results) else 1
    except (KeyboardInterrupt,EOFError):
        print("\nCancelled. No credentials saved.");return 1


if __name__=="__main__":sys.exit(main())
