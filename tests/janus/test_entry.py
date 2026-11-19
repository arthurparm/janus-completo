import unittest

from janus.entry import Budget, OpenRunRequest
from janus.util.codec import JanusError


class EntryTest(unittest.TestCase):
    def test_voice_disclosure_is_required(self) -> None:
        with self.assertRaises(JanusError) as caught:
            OpenRunRequest("arthur", "read_record", Budget(2, 1000, 2), False, "model-a", "ler")
        self.assertEqual(caught.exception.reason, "a entrada tem de registrar que a voz é um modelo")

    def test_identity_keeps_requester(self) -> None:
        request = OpenRunRequest("arthur", "read_record", Budget(2, 1000, 2), True, "model-a", "ler")
        self.assertEqual(request.requester, "arthur")
        self.assertTrue(request.voice_is_model)


if __name__ == "__main__":
    unittest.main()
