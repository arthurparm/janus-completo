import ast

from app.services.code_analysis_service import CodeParser


def _parse(source: str) -> CodeParser:
    parser = CodeParser("/repo/app/example.py")
    parser.visit(ast.parse(source))
    return parser


def test_code_parser_extracts_qualified_names_and_calls():
    parser = _parse(
        """
class Engine:
    def run(self):
        self.helper()
        helper()

    def helper(self):
        pass

def helper():
    pass
"""
    )

    function_qualified_names = {f["qualified_name"] for f in parser.functions}
    assert "Engine.run" in function_qualified_names
    assert "Engine.helper" in function_qualified_names
    assert "helper" in function_qualified_names

    call_pairs = {(c["caller_qualified"], c["callee_qualified"]) for c in parser.calls}
    assert ("Engine.run", "Engine.helper") in call_pairs
    assert ("Engine.run", "helper") in call_pairs


def test_code_parser_handles_async_functions():
    parser = _parse(
        """
async def runner():
    helper()

def helper():
    pass
"""
    )

    function_qualified_names = {f["qualified_name"] for f in parser.functions}
    assert "runner" in function_qualified_names

    call_pairs = {(c["caller_qualified"], c["callee_qualified"]) for c in parser.calls}
    assert ("runner", "helper") in call_pairs
