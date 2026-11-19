import unittest

from janus.tools.delete_record import DELETE_RECORD, DeleteRecordTool, plain_language
from janus.util.codec import JanusError


class DeleteRecordTest(unittest.TestCase):
    def test_spec_is_irreversible_and_requires_an_idempotency_key(self) -> None:
        self.assertEqual(DELETE_RECORD.risk_class, "escrita_irreversivel")
        self.assertEqual(DELETE_RECORD.argument_names, ("record_id", "idempotency_key"))
        action, effect = plain_language("alpha")
        self.assertEqual(action, "Apagar o registro alpha")
        self.assertEqual(effect, "O registro alpha deixa de existir e não há como desfazer.")

    def test_execute_does_not_perform_the_write(self) -> None:
        tool = DeleteRecordTool()
        with self.assertRaises(JanusError) as caught:
            tool.execute({"record_id": "alpha", "idempotency_key": "chave-1"})
        self.assertEqual(caught.exception.reason, "escrita irreversível não executa")
        self.assertEqual(tool.calls(), ("chave-1",))


if __name__ == "__main__":
    unittest.main()
