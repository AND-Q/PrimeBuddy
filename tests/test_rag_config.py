import importlib
import os
import unittest
from unittest.mock import Mock, patch

from rag import rag_service
from rag import vector_store


class RagConfigTest(unittest.TestCase):
    def test_maybe_log_prompt_does_not_print_when_debug_disabled(self):
        prompt = Mock()
        prompt.to_string.return_value = "sensitive prompt text"

        with patch.dict(rag_service.rag_conf, {"debug_rag_prompt": False}, clear=False):
            with patch("builtins.print") as print_mock:
                result = rag_service.maybe_log_prompt(prompt)

        self.assertIs(result, prompt)
        print_mock.assert_not_called()
        prompt.to_string.assert_not_called()

    def test_maybe_log_prompt_logs_when_debug_enabled(self):
        prompt = Mock()
        prompt.to_string.return_value = "debug prompt text"

        with patch.dict(rag_service.rag_conf, {"debug_rag_prompt": True}, clear=False):
            with patch.object(rag_service.logger, "debug") as debug_mock:
                result = rag_service.maybe_log_prompt(prompt)

        self.assertIs(result, prompt)
        debug_mock.assert_called_once()
        prompt.to_string.assert_called_once()

    def test_chroma_persist_directory_is_absolute(self):
        with patch.dict(vector_store.chroma_conf, {"persist_directory": "chroma_db"}, clear=False):
            persist_directory = vector_store.get_chroma_persist_directory()

        self.assertTrue(os.path.isabs(persist_directory))
        self.assertTrue(persist_directory.endswith("chroma_db"))

    def test_model_and_rag_modules_import_without_credentials(self):
        with patch.dict(os.environ, {"MY_API_KEY": "", "MY_BASE_URL": "", "DASHSCOPE_API_KEY": ""}, clear=False):
            import model.factory as model_factory
            import rag.rag_service as reloaded_rag_service
            import rag.vector_store as reloaded_vector_store

            importlib.reload(model_factory)
            importlib.reload(reloaded_rag_service)
            importlib.reload(reloaded_vector_store)


if __name__ == "__main__":
    unittest.main()
