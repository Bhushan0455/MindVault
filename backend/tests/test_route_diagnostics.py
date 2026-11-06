from io import BytesIO
import json
import unittest
from urllib.error import HTTPError

from examples.gemini_routes import NoRedirect,probe_route


class Response(BytesIO):
    status=200


class Opener:
    def __init__(self,data):self.data=data;self.requests=[]
    def open(self,request,timeout):
        self.requests.append(request)
        return Response(json.dumps(self.data).encode())


class RouteDiagnosticsTests(unittest.TestCase):
    def test_current_interactions_steps_text_detected(self):
        opener=Opener({"status":"completed","steps":[{"type":"model_output","content":[{"type":"text","text":"OK"}]}]})
        r=probe_route("interactions","test-key","test-model",45,opener)
        self.assertTrue(r.usable_text)
        req=opener.requests[0]
        self.assertEqual(req.full_url,"https://generativelanguage.googleapis.com/v1beta/interactions")
        self.assertFalse(json.loads(req.data)["store"])
        self.assertNotIn("test-key",str(r))

    def test_generation_text_detected_without_sdk(self):
        opener=Opener({"candidates":[{"content":{"parts":[{"text":"OK"}]}}]})
        r=probe_route("generateContent","test-key","test-model",45,opener)
        self.assertTrue(r.usable_text)
        self.assertNotIn("key=",opener.requests[0].full_url)

    def test_thought_or_in_progress_not_claimed_as_completed(self):
        for data in [{"status":"in_progress","steps":[{"type":"model_output","content":[{"type":"text","text":"partial"}]}]},
                     {"status":"completed","steps":[{"type":"thought","content":[{"type":"text","text":"thinking"}]}]}]:
            self.assertFalse(probe_route("interactions","test-key","test-model",45,Opener(data)).usable_text)

    def test_http_error_code_and_redacted_detail_retained(self):
        class ErrorOpener:
            def open(self,request,timeout):
                raise HTTPError(request.full_url,504,"timeout",{},BytesIO(json.dumps({"error":{"message":"deadline test-secret"}}).encode()))
        r=probe_route("generateContent","test-secret","test-model",45,ErrorOpener())
        self.assertEqual(r.http_status,504)
        self.assertNotIn("test-secret",r.detail)

    def test_model_cannot_change_endpoint(self):
        with self.assertRaises(ValueError):probe_route("interactions","test-key","https://other.invalid",45)

    def test_redirects_not_followed_with_key(self):
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,"redirect",{},"https://other.invalid"))


if __name__=="__main__":unittest.main()
