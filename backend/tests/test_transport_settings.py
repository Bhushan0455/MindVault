from contextlib import redirect_stdout
from io import StringIO
import os
import sys
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch

from app.services.transport_settings import request_timeout_ms,remaining_timeout_ms,temporary_timeout
from examples.gemini_setup import probe_connection


class TransportSettingsTests(unittest.TestCase):
    def test_default_is_thirty_seconds_in_sdk_milliseconds(self):
        with patch.dict(os.environ,{},clear=True):self.assertEqual(request_timeout_ms(),30000)

    def test_configured_timeout(self):
        with patch.dict(os.environ,{"GEMINI_TIMEOUT_SECONDS":"45"}):self.assertEqual(request_timeout_ms(),45000)

    def test_invalid_timeouts_rejected(self):
        for value in ["0","-1","61","nan","inf","abc"]:
            with patch.dict(os.environ,{"GEMINI_TIMEOUT_SECONDS":value}),self.assertRaises(ValueError):request_timeout_ms()

    def test_remaining_budget_limits_a_request(self):
        with patch.dict(os.environ,{"GEMINI_TIMEOUT_SECONDS":"45"}),patch("app.services.transport_settings.time.monotonic",return_value=100):
            self.assertEqual(remaining_timeout_ms(110),10000)

    def test_exhausted_budget_stops_before_another_request(self):
        with patch("app.services.transport_settings.time.monotonic",return_value=100),self.assertRaises(TimeoutError):remaining_timeout_ms(99)

    def test_temporary_override_restored_on_exception(self):
        with patch.dict(os.environ,{"GEMINI_TIMEOUT_SECONDS":"30"}):
            with self.assertRaises(RuntimeError):
                with temporary_timeout(45):
                    self.assertEqual(request_timeout_ms(),45000)
                    raise RuntimeError("test")
            self.assertEqual(request_timeout_ms(),30000)

    def test_temporary_override_not_persisted(self):
        with patch.dict(os.environ,{},clear=True):
            with temporary_timeout(45):pass
            self.assertNotIn("GEMINI_TIMEOUT_SECONDS",os.environ)

    def test_probe_passes_configured_sdk_timeout(self):
        options=[]
        class Client:
            def __init__(self,**kwargs):options.append(kwargs["http_options"]);self.models=self
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def generate_content(self,**kwargs):return SimpleNamespace(text="OK")
        google=ModuleType("google");google.genai=SimpleNamespace(Client=Client)
        with patch.dict(sys.modules,{"google":google}),temporary_timeout(45),redirect_stdout(StringIO()):
            self.assertTrue(probe_connection("test-key","test-model"))
        self.assertEqual(options[0]["timeout"],45000)


if __name__=="__main__":unittest.main()
