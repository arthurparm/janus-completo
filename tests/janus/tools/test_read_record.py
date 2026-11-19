import unittest

from janus.tools.read_record import ReadRecordTool


class ReadRecordTest(unittest.TestCase):
    def test_known_record_is_data_and_missing_record_is_error(self) -> None:
        tool = ReadRecordTool({"alpha": "conteudo-alpha"})
        found = tool.execute({"record_id": "alpha"})
        self.assertEqual(found.label, "dado")
        self.assertEqual(found.text, "conteudo-alpha")
        missing = tool.execute({"record_id": "beta"})
        self.assertEqual(missing.label, "erro")
        self.assertEqual(missing.text, "registro ausente")
        self.assertEqual(tool.calls(), ("alpha", "beta"))


if __name__ == "__main__":
    unittest.main()
