"""Optional real Gemini knowledge adapter. No API key or document content logged.

Live provider behaviour requires a configured account; unit tests use fakes only
at the provider boundary. This is not yet a generic content-review AI wrapper.
"""

import json
import os
import re
import time
from copy import deepcopy

from .knowledge_extract import RESPONSE_SCHEMA, SYSTEM_PROMPT
from .transport_settings import request_timeout_ms, remaining_timeout_ms


def knowledge_provider_schema():
    """Keep the model's decoding schema small; enforce item limits locally.

    A large array bound combined with the 16 required payload fields can make
    Gemini's structured-output schema too complex. The canonical schema and
    validate_candidates still impose the 100-candidate application limit.
    This compatibility adjustment does not establish the cause of a generic
    provider INVALID_ARGUMENT response without a successful live retry.
    """
    schema=deepcopy(RESPONSE_SCHEMA)
    schema['properties']['candidates'].pop('maxItems',None)
    return schema


def safe_provider_message(exc, secret=""):
    """Diagnostic for the fictional setup test only; never persist in audit rows."""
    message = getattr(exc, "message", None)
    if not isinstance(message, str): message = str(exc)
    # Redact before truncation, including keys accidentally repeated by a server.
    for value in (secret, os.getenv("GEMINI_API_KEY", ""), os.getenv("GOOGLE_API_KEY", "")):
        if value: message = message.replace(value, "[REDACTED_KEY]")
    message = re.sub(r"AIza[\w-]+", "[REDACTED_KEY]", message)
    message = re.sub(r"https?://\S+", "[REDACTED_URL]", message)
    message = re.sub(r"(?i)Bearer\s+\S+", "Bearer [REDACTED_KEY]", message)
    message = redact(message)
    return " ".join(message.split())[:500]


def redact(text):
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", text)
    def phone(match):
        return "[REDACTED_PHONE]" if sum(c.isdigit() for c in match.group()) >= 10 else match.group()
    return re.sub(r"(?<![\w₹])\+?\d[\d ()-]{8,}\d(?!\w)", phone, text)


class GeminiKnowledgeGenerator:
    def __init__(self, *, org_id, brand_id):
        if not org_id.strip() or not brand_id.strip(): raise ValueError("Organisation and brand required.")
        self.org_id, self.brand_id = org_id, brand_id
        self.events = []  # Backend A persists these metadata-only audit entries.
        self.last_error = None  # Sanitised, ephemeral setup diagnostic; not audit content.

    def __call__(self, document):
        self.last_error = None
        key, model = os.getenv("GEMINI_API_KEY", ""), os.getenv("GEMINI_MODEL", "")
        if not key or not model:
            raise RuntimeError("Set GEMINI_API_KEY and GEMINI_MODEL in the environment.")
        blocks = [{"block_index": i, "text": redact(b.text)} for i, b in enumerate(document.blocks)]
        prompt = json.dumps({"untrusted_source_blocks": blocks}, ensure_ascii=False)
        if len(prompt) > 30000: raise RuntimeError("Input exceeds this version's 30,000-character AI budget; use manual entry.")
        redacted = any(blocks[i]["text"] != b.text for i,b in enumerate(document.blocks))
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("Install optional requirements-ai.txt for Gemini.") from exc
        # Bound individual requests and the adapter's overall analysis budget.
        deadline=time.monotonic()+40
        try:
            with genai.Client(api_key=key, http_options={"timeout": request_timeout_ms(), "retry_options": {"attempts": 1}}) as client:
                for attempt in range(1, 4):
                    timeout=remaining_timeout_ms(deadline)
                    event = {"event_type": "ai_call", "purpose": "knowledge_extraction", "model": model,
                             "org_id": self.org_id, "brand_id": self.brand_id,
                             "redacted": redacted, "attempt": attempt, "success": False}
                    try:
                        response = client.models.generate_content(model=model, contents=prompt,
                            config={"http_options":{"timeout":timeout,"retry_options":{"attempts":1}},
                                    "system_instruction": SYSTEM_PROMPT, "temperature": 0,
                                    "response_mime_type": "application/json", "response_json_schema": knowledge_provider_schema(),
                                    "max_output_tokens": 6000})
                        if not isinstance(response.text, str):
                            raise ValueError("No JSON text returned")
                        output = json.loads(response.text)
                        if not isinstance(output, dict) or not isinstance(output.get("candidates"), list):
                            raise ValueError("Invalid candidate response")
                        event["success"] = True
                        return output
                    except Exception as exc:
                        self.last_error = safe_provider_message(exc, key)
                        code = getattr(exc, "code", None)
                        event["error_code"] = code if isinstance(code, int) else None
                        event["failure_kind"] = "invalid_response" if isinstance(exc, (ValueError, TypeError)) else "provider_or_transport"
                        retryable = isinstance(exc, (ValueError, TimeoutError)) or code == 429 or isinstance(code, int) and code >= 500
                        if attempt == 3 or not retryable: raise RuntimeError("Gemini extraction failed.") from None
                    finally:
                        self.events.append(event)
                    time.sleep(0.5 * 2**(attempt-1))
        except RuntimeError:
            raise
        except Exception as exc:
            self.last_error = safe_provider_message(exc, key)
            raise RuntimeError("Gemini setup or transport failed.") from None
