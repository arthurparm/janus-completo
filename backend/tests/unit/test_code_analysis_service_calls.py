import ast

from app.services.code_analysis_service import CodeAnalysisService, CodeParser


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


def test_parse_python_file_handles_utf8_bom(tmp_path):
    source = "\ufeffdef hello():\n    return 42\n"
    file_path = tmp_path / "_tmp_bom_file.py"
    file_path.write_text(source, encoding="utf-8")

    service = CodeAnalysisService()
    parser = service.parse_python_file(str(file_path))

    assert parser is not None
    assert any(item["name"] == "hello" for item in parser.functions)
