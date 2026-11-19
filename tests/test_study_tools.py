import threading
import time
import unittest
from unittest.mock import patch
from agent.tools import study_tools


class GetRagServiceTest(unittest.TestCase):
    def setUp(self):
        study_tools._build_rag_service.cache_clear()
        self.addCleanup(study_tools._build_rag_service.cache_clear)

    def test_concurrent_first_calls_create_service_once(self):
        created = []

        class SlowRagService:
            def __init__(self):
                time.sleep(0.05)
                created.append(self)

        thread_count = 4
        barrier = threading.Barrier(thread_count)
        results = []

        def first_call():
            barrier.wait()
            results.append(study_tools.get_rag_service())

        with patch.object(study_tools, "RagSummarizeService", SlowRagService):
            threads = [threading.Thread(target=first_call) for _ in range(thread_count)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(len(created), 1)
        self.assertEqual(len(results), thread_count)
        self.assertTrue(all(service is created[0] for service in results))


if __name__ == "__main__":
    unittest.main()
