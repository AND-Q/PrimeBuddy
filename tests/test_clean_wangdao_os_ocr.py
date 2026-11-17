import unittest

from scripts.clean_wangdao_os_ocr import clean_text


class CleanWangdaoOsOcrTest(unittest.TestCase):
    def test_skips_front_matter_and_adds_page_source_markers(self):
        raw_text = "\f".join(
            [
                "扉页\n1\n",
                "目 录\n2\n",
                "第1章   计算机系统概述\n1.1   操作系统的基本概念\n操作系统是指控制和管理\n整个计算机系统的硬件和软件资源。\n13\n",
            ]
        )

        cleaned = clean_text(raw_text, skip_pages=2, source_name="2025王道操作系统")

        self.assertNotIn("扉页", cleaned)
        self.assertNotIn("目 录", cleaned)
        self.assertIn("[来源：2025王道操作系统，第 3 页]", cleaned)
        self.assertIn("第1章 计算机系统概述", cleaned)
        self.assertIn("1.1 操作系统的基本概念", cleaned)
        self.assertIn("操作系统是指控制和管理整个计算机系统的硬件和软件资源。", cleaned)
        self.assertNotIn("\n13\n", cleaned)

    def test_keeps_exercise_and_answer_sections(self):
        raw_text = "\f".join(
            [
                "封面\n",
                "本节习题精选\n下列关于操作系统的说法\n正确的是（ ）。\n14\n",
                "答案与解析\n本题考查操作系统的目标和功能。\n15\n",
            ]
        )

        cleaned = clean_text(raw_text, skip_pages=1, source_name="2025王道操作系统")

        self.assertIn("本节习题精选", cleaned)
        self.assertIn("下列关于操作系统的说法正确的是（ ）。", cleaned)
        self.assertIn("答案与解析", cleaned)
        self.assertIn("本题考查操作系统的目标和功能。", cleaned)


if __name__ == "__main__":
    unittest.main()
