"""Step 7: local diagnostics and explicit interactive live Gemini verification.

py -m examples.gemini_setup             # no network, no secret output
py -m examples.gemini_setup --connect   # private key input + fictional live test
"""

import argparse
from contextlib import contextmanager
import getpass
from importlib.metadata import PackageNotFoundError, version
from itertools import islice
import os
import sys

from app.services.extraction import extract_document
from app.services.knowledge_extract import extract_candidates
from app.services.llm import GeminiKnowledgeGenerator, safe_provider_message
from app.services.transport_settings import request_timeout_ms, temporary_timeout


SAMPLE = ("Avoid cheap; use affordable.\nPaid ads must include T&C apply.\n"
          "Veyra Beat 200: price INR 999.\nVeyra Beat 200: battery life up to 40 hours.\n"
          "Veyra Beat 200: warranty 1 year.")


@contextmanager
def temporary_credentials(key, model):
    """Restore the process environment on success, failure or Ctrl+C."""
    previous = {name: os.environ.get(name) for name in ("GEMINI_API_KEY", "GEMINI_MODEL")}
    try:
        os.environ["GEMINI_API_KEY"], os.environ["GEMINI_MODEL"] = key, model
        yield
    finally:
        for name, value in previous.items():
            if value is None: os.environ.pop(name, None)
            else: os.environ[name] = value


def list_generation_models(client):
    """Read a bounded catalogue; listing does not guarantee generation quota."""
    found = set()
    for model in islice(client.models.list(config={"page_size": 100}), 100):
        if "generateContent" in (getattr(model, "supported_actions", None) or []):
            name = getattr(model, "name", None)
            if name:
                found.add(name.removeprefix("models/"))
    return sorted(found)


def choose_model(names, choice):
    if choice.isdigit() and 1 <= int(choice) <= len(names):
        return names[int(choice)-1]
    if choice in names:
        return choice
    raise ValueError("Choose a listed model number or exact ID.")


def error_help(code):
    if code in (401, 403): return "Check the API key, project permissions and account access in Google AI Studio."
    if code == 404: return "The model is unavailable; choose another model exposed to this account."
    if code == 429: return "Quota/rate limit reached. Check AI Studio usage and retry later or choose an available model."
    if code == 400: return "Google rejected a request parameter or credential. See the redacted provider detail below."
    if code==504:return "The request exceeded a deadline. Try a longer configured timeout; a provider-side deadline can still recur."
    if isinstance(code, int) and code >= 500: return "Google returned a server-side failure; retry later if it persists."
    return "Check network access, SDK installation, key and model availability. Raw provider errors are hidden to protect credentials."


def check_local():
    print("Python:", sys.version.split()[0])
    print("Team deployment target: Python 3.12; the current modules have also passed the user's tests on 3.14.")
    installed = True
    for package in ("pypdf", "python-docx", "google-genai"):
        try: print(package + ": " + version(package))
        except PackageNotFoundError:
            print(package + ": NOT INSTALLED")
            installed = False
    print("GEMINI_API_KEY:", "present (hidden)" if os.getenv("GEMINI_API_KEY") else "not set")
    print("GEMINI_MODEL:", "set" if os.getenv("GEMINI_MODEL") else "not set")
    if not installed: print("Install: py -m pip install -r requirements-ai.txt")
    print("No API calls made by local diagnostics.")
    return installed


def probe_connection(key,model):
    """One explicit plaintext request: no schema, user documents or fallback."""
    from google import genai
    print(f"STAGE 1/4: checking a small plain-text Gemini request (timeout {request_timeout_ms()/1000:g}s)...")
    try:
        with genai.Client(api_key=key,http_options={"timeout":request_timeout_ms(),"retry_options":{"attempts":1}}) as client:
            response=client.models.generate_content(model=model,contents="Reply only with OK. This is a connection test.",
                                                     config={"max_output_tokens":512})
        if not isinstance(response.text,str) or not response.text.strip():
            print("CONNECTION INCONCLUSIVE: response contains no usable text. Model output/timeout settings need review.")
            return False
        print("PLAIN-TEXT CONNECTION VERIFIED. This alone does not verify structured extraction or review.")
        return True
    except Exception as exc:
        code=getattr(exc,"code",None)
        print("PLAIN-TEXT CONNECTION FAILED. "+error_help(code if isinstance(code,int) else None))
        print("Redacted provider detail:",safe_provider_message(exc,key))
        return False


def verify_all_services(key,model):
    """One private key entry; separate verification states for three real services."""
    if not probe_connection(key,model):return 1
    from app.services.ai_review import GeminiContentGenerator,run_review
    from app.services.ai_clarity import GeminiClarityGenerator,run_clarity_audit
    from examples.review_demo import demo_inputs
    from examples.ai_clarity_demo import demo_rules
    outcomes={}
    def diagnose(adapter):
        if getattr(adapter,"last_error",None):print("Redacted provider detail:",adapter.last_error)
        else:print("Inspect model output/schema support and any validation issues shown above.")
    with temporary_credentials(key,model):
        print("STAGE 2/4: source-validated knowledge extraction (fictional document)...")
        adapter=GeminiKnowledgeGenerator(org_id="demo-org",brand_id="veyra")
        document=extract_document("fictional_live_test.txt",SAMPLE.encode())
        knowledge=extract_candidates(document,org_id="demo-org",brand_id="veyra",document_id="demo-live-document",generator=adapter)
        outcomes["knowledge_extraction"]=knowledge.method=="ai" and bool(knowledge.candidates)
        print(f"method={knowledge.method}; pending candidates={len(knowledge.candidates)}")
        print("Validation issues:",sum(i.startswith("Candidate ") for i in knowledge.issues))
        if not outcomes["knowledge_extraction"]:diagnose(adapter)
        print("STAGE 3/4: content review (fictional investor draft)...")
        adapter=GeminiContentGenerator(org_id="demo-org",brand_id="veyra")
        review=run_review(**demo_inputs(),generator=adapter)
        retained=sum(f.origin=="ai" for f in review.findings)
        outcomes["content_review"]=review.ai_used and retained>0
        print(f"ai_used={review.ai_used}; ai_status={review.ai_status}; retained AI findings={retained}")
        if not outcomes["content_review"]:diagnose(adapter)
        print("STAGE 4/4: clarity audit (fictional rules)...")
        adapter=GeminiClarityGenerator(org_id="demo-org",brand_id="veyra")
        clarity=run_clarity_audit(demo_rules(),org_id="demo-org",brand_id="veyra",generator=adapter)
        retained=sum(f.method=="ai" for f in clarity.findings)
        outcomes["clarity_audit"]=clarity.ai_used and retained>0
        print(f"ai_used={clarity.ai_used}; ai_status={clarity.ai_status}; retained AI proposals={retained}")
        if not outcomes["clarity_audit"]:diagnose(adapter)
    print("\nLIVE VERIFICATION SUMMARY")
    print("plain_text_connection: VERIFIED")
    for name,passed in outcomes.items():print(name+": "+("VERIFIED" if passed else "NOT VERIFIED"))
    print("VERIFIED requires retained source-validated AI output for this fictional fixture, not fallback.")
    print("An empty legitimate model response is inconclusive for the fixture, not proof the provider is broken.")
    print("No key saved to disk or parent shell. No knowledge/content approved or persisted.")
    print("This is a smoke test, not a general accuracy evaluation. Review model usage in your account.")
    return 0 if all(outcomes.values()) else 1


def connect(model_override=None,all_services=False):
    try:
        from google import genai
    except ImportError:
        print("Install first: py -m pip install -r requirements-ai.txt")
        return 1
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        if not sys.stdin.isatty():
            print("Run --connect directly in an interactive PowerShell window for private key entry.")
            return 1
        key = getpass.getpass("Paste Gemini API key (input hidden), then press Enter: ").strip()
    if not key:
        print("No key entered; nothing sent."); return 1
    model = (model_override or os.getenv("GEMINI_MODEL", "")).strip()
    if not model:
        print("Checking this account's model catalogue...")
        try:
            with genai.Client(api_key=key, http_options={"timeout": request_timeout_ms(), "retry_options": {"attempts": 1}}) as client:
                names = list_generation_models(client)
        except Exception as exc:
            code = getattr(exc, "code", None)
            print("Model catalogue check failed. " + error_help(code if isinstance(code, int) else None))
            print("Redacted provider detail:", safe_provider_message(exc, key))
            return 1
        if not names:
            print("No generation models found in the first 100 catalogue entries. Check account/model access.")
            return 1
        print("Generation-capable model IDs (listing alone does not verify text/JSON support or free quota):")
        for i, name in enumerate(names, 1): print(f"  {i}. {name}")
        print("Choose a text-capable model supported by your account; do not choose an image/audio-only model.")
        try: model = choose_model(names, input("Model number or exact listed ID: ").strip())
        except ValueError as exc:
            print(str(exc)); return 1
    if all_services:
        return verify_all_services(key,model)
    # Do not print the raw configured model: a user might accidentally store a key there.
    print("Running a live request with the built-in FICTIONAL sample only...")
    adapter = GeminiKnowledgeGenerator(org_id="demo-org", brand_id="veyra")
    doc = extract_document("fictional_live_test.txt", SAMPLE.encode())
    with temporary_credentials(key, model):
        result = extract_candidates(doc, org_id="demo-org", brand_id="veyra",
                                     document_id="demo-live-document", generator=adapter)
    # Never print raw adapter events, SDK exceptions, source payloads or credentials.
    print("method=" + result.method)
    print("Validated pending candidates:", len(result.candidates))
    print("Validation issues:", sum(issue.startswith("Candidate ") for issue in result.issues))
    if result.method != "ai":
        print("LIVE GEMINI NOT VERIFIED: deterministic fallback was used.")
        codes = [e.get("error_code") for e in adapter.events if isinstance(e.get("error_code"), int)]
        print(error_help(codes[-1] if codes else None))
        if adapter.last_error:
            print("Redacted provider detail:", adapter.last_error)
        return 1
    if not result.candidates:
        print("Gemini responded, but no source-validated candidates were produced. Review model/output support.")
        return 1
    print("LIVE GEMINI VERIFIED: a real response produced source-validated pending candidates.")
    print("Candidates still require admin review. This does not measure general extraction accuracy.")
    print("No key saved to disk or to the parent PowerShell session. Re-run --connect for another private test.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Check Gemini setup without exposing credentials.")
    parser.add_argument("--connect", action="store_true", help="Explicit live test using fictional sample data")
    parser.add_argument("--model", help="Explicit model ID; skips catalogue selection during --connect")
    parser.add_argument("--all-services",action="store_true",help="Plain-text probe then real knowledge/content/clarity tests, using fictional data only")
    parser.add_argument("--timeout-seconds",type=float,help="Per-request timeout from 5 to 60 seconds; service retry budget remains 40 seconds")
    args = parser.parse_args()
    try:
        if args.connect:
            with temporary_timeout(args.timeout_seconds):
                return connect(model_override=args.model,all_services=args.all_services)
        check_local()
        print("Next: py -m examples.gemini_setup --connect")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. No credentials saved.")
        return 1
    except ValueError as exc:
        parser.exit(2,str(exc)+"\n")


if __name__ == "__main__": sys.exit(main())
