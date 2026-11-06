from contextlib import redirect_stdout
from io import StringIO
import os
import sys
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch

from examples.gemini_setup import probe_connection,verify_all_services


class LiveVerificationTests(unittest.TestCase):
    def sdk(self,generate):
        class Client:
            def __init__(self,**kwargs):self.models=self
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def generate_content(self,**kwargs):return generate(**kwargs)
        module=ModuleType("google");module.genai=SimpleNamespace(Client=Client)
        return module

    def test_plain_probe_uses_no_schema_or_private_data(self):
        calls=[]
        def generate(**kwargs):calls.append(kwargs);return SimpleNamespace(text="OK")
        with patch.dict(sys.modules,{"google":self.sdk(generate)}),redirect_stdout(StringIO()):
            self.assertTrue(probe_connection("fictional-test-key","test-model"))
        self.assertNotIn("response_json_schema",calls[0]["config"])
        self.assertNotIn("fictional-test-key",str(calls))

    def test_plain_probe_error_is_redacted(self):
        class Denied(Exception):code=403
        def generate(**kwargs):raise Denied("fictional-secret-do-not-print")
        output=StringIO()
        with patch.dict(sys.modules,{"google":self.sdk(generate)}),redirect_stdout(output):
            self.assertFalse(probe_connection("fictional-secret-do-not-print","test-model"))
        self.assertNotIn("fictional-secret-do-not-print",output.getvalue())

    def test_empty_response_is_inconclusive_not_verified(self):
        with patch.dict(sys.modules,{"google":self.sdk(lambda **kwargs:SimpleNamespace(text=None))}),redirect_stdout(StringIO()):
            self.assertFalse(probe_connection("test-key","test-model"))

    def test_failed_probe_prevents_expensive_service_calls(self):
        with patch("examples.gemini_setup.probe_connection",return_value=False), \
             patch("examples.gemini_setup.extract_candidates") as knowledge:
            self.assertEqual(verify_all_services("test-key","test-model"),1)
        knowledge.assert_not_called()

    def test_fallback_does_not_become_live_success_and_environment_restores(self):
        output=StringIO()
        with patch.dict(os.environ,{},clear=True),patch("examples.gemini_setup.probe_connection",return_value=True), \
             patch("examples.gemini_setup.extract_candidates",return_value=SimpleNamespace(method="deterministic_fallback",candidates=[1],issues=[])), \
             patch("app.services.ai_review.run_review",return_value=SimpleNamespace(ai_used=False,ai_status="unavailable",findings=[])), \
             patch("app.services.ai_clarity.run_clarity_audit",return_value=SimpleNamespace(ai_used=False,ai_status="unavailable",findings=[])),redirect_stdout(output):
            self.assertEqual(verify_all_services("test-secret","test-model"),1)
            self.assertNotIn("GEMINI_API_KEY",os.environ)
        self.assertIn("knowledge_extraction: NOT VERIFIED",output.getvalue())
        self.assertIn("content_review: NOT VERIFIED",output.getvalue())
        self.assertNotIn("test-secret",output.getvalue())

    def test_each_service_needs_actual_retained_ai_output_in_fixture(self):
        # Explicit unit mocks only. This does not establish a real live call.
        output=StringIO()
        with patch("examples.gemini_setup.probe_connection",return_value=True), \
             patch("examples.gemini_setup.extract_candidates",return_value=SimpleNamespace(method="ai",candidates=[1],issues=[])), \
             patch("app.services.ai_review.run_review",return_value=SimpleNamespace(ai_used=True,ai_status="completed",findings=[SimpleNamespace(origin="ai")])), \
             patch("app.services.ai_clarity.run_clarity_audit",return_value=SimpleNamespace(ai_used=True,ai_status="completed",findings=[SimpleNamespace(method="ai")])),redirect_stdout(output):
            self.assertEqual(verify_all_services("test-secret","test-model"),0)
        self.assertIn("clarity_audit: VERIFIED",output.getvalue())
        self.assertNotIn("test-secret",output.getvalue())


if __name__=="__main__":unittest.main()
