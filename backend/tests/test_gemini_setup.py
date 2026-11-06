from contextlib import redirect_stdout
from io import StringIO
import json
import os
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from app.services.extraction import extract_document
from app.services.llm import GeminiKnowledgeGenerator
from examples.gemini_setup import (SAMPLE, choose_model, connect, list_generation_models,
                                    temporary_credentials)


class GeminiSetupTests(unittest.TestCase):
    def provider(self, generate=None, models=None):
        class Client:
            def __init__(self, **kwargs): self.models=self
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def list(self, **kwargs): return iter(models or [])
            def generate_content(self, **kwargs): return generate()
        module=ModuleType("google"); module.genai=SimpleNamespace(Client=Client)
        return module

    def test_only_generation_models_listed_and_prefix_removed(self):
        models=[SimpleNamespace(name="models/text-demo",supported_actions=["generateContent"]),
                SimpleNamespace(name="models/embedding",supported_actions=["embedContent"])]
        client=SimpleNamespace(models=SimpleNamespace(list=lambda **kwargs: iter(models)))
        self.assertEqual(list_generation_models(client), ["text-demo"])

    def test_model_selection_rejects_unknown_choice(self):
        self.assertEqual(choose_model(["demo"], "1"), "demo")
        self.assertEqual(choose_model(["demo"], "demo"), "demo")
        for choice in ["0", "2", "unknown"]:
            with self.assertRaises(ValueError): choose_model(["demo"], choice)

    def test_temporary_credentials_restore_even_on_failure(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY":"old", "GEMINI_MODEL":"original"}):
            with self.assertRaises(RuntimeError):
                with temporary_credentials("temporary", "demo"):
                    self.assertEqual(os.environ["GEMINI_API_KEY"],"temporary")
                    raise RuntimeError("test")
            self.assertEqual(os.environ["GEMINI_API_KEY"],"old")

    def test_temporary_credentials_remove_previously_absent_values(self):
        with patch.dict(os.environ, {}, clear=True):
            with temporary_credentials("temporary", "demo"): pass
            self.assertNotIn("GEMINI_API_KEY", os.environ)

    def test_noninteractive_key_input_is_refused(self):
        output=StringIO()
        with patch.dict(sys.modules,{"google": self.provider()}), patch.dict(os.environ,{},clear=True), \
             patch("sys.stdin.isatty",return_value=False), redirect_stdout(output):
            self.assertEqual(connect(),1)
        self.assertIn("interactive",output.getvalue())

    def test_invalid_json_budget_is_three_calls_and_no_raw_exception(self):
        calls=[]
        def generate():
            calls.append(1)
            return SimpleNamespace(text="not-json")
        with patch.dict(sys.modules,{"google":self.provider(generate)}), \
             patch.dict(os.environ,{"GEMINI_API_KEY":"fake-private-key", "GEMINI_MODEL":"test-model"}), \
             patch("app.services.llm.time.sleep"):
            adapter=GeminiKnowledgeGenerator(org_id="org",brand_id="brand")
            with self.assertRaises(RuntimeError): adapter(extract_document("demo.txt",SAMPLE.encode()))
        self.assertEqual(len(calls),3)
        self.assertEqual(adapter.events[-1]["failure_kind"],"invalid_response")
        self.assertNotIn("fake-private-key",str(adapter.events))

    def test_authentication_error_does_not_retry_and_key_not_printed(self):
        class Denied(Exception): code=403
        calls=[]
        def generate():
            calls.append(1); raise Denied("fake-private-key must never appear")
        output=StringIO()
        with patch.dict(sys.modules,{"google":self.provider(generate)}), \
             patch.dict(os.environ,{"GEMINI_API_KEY":"fake-private-key", "GEMINI_MODEL":"test-model"}), redirect_stdout(output):
            self.assertEqual(connect(),1)
        self.assertEqual(len(calls),1)
        self.assertNotIn("fake-private-key",output.getvalue())
        self.assertIn("NOT VERIFIED",output.getvalue())

    def test_fake_valid_response_exercises_live_verification_branch(self):
        # This is a unit-test fake, not a production response or live verification.
        from app.services.knowledge_extract import _offline
        doc=extract_document("demo.txt",SAMPLE.encode())
        def generate(): return SimpleNamespace(text=json.dumps(_offline(doc)))
        output=StringIO()
        with patch.dict(sys.modules,{"google":self.provider(generate)}), \
             patch.dict(os.environ,{"GEMINI_API_KEY":"fake-private-key", "GEMINI_MODEL":"test-model"}), redirect_stdout(output):
            self.assertEqual(connect(),0)
        self.assertIn("Validated pending candidates: 5",output.getvalue())
        self.assertNotIn("fake-private-key",output.getvalue())


if __name__ == "__main__": unittest.main()
