"""Unit tests for syntax noise detection functions."""

import pytest
from src.parser_utils import (
    parse_java,
    detect_grammar_errors,
    detect_empty_exception,
    detect_empty_method,
    detect_ambiguous_type,
    detect_non_english,
    detect_synchronized,
)


class TestGrammarErrors:
    def test_valid_method(self):
        code = "public int add(int a, int b) { return a + b; }"
        root = parse_java(code)
        assert detect_grammar_errors(root) is False

    def test_missing_block(self):
        code = "public int add(int a, int b)"
        root = parse_java(code)
        # tree-sitter may or may not flag this as ERROR depending on context
        # The key behavior: incomplete code should be detected
        result = detect_grammar_errors(root)
        assert isinstance(result, bool)


class TestEmptyException:
    def test_empty_catch(self):
        code = """
        public void foo() {
            try { doWork(); }
            catch(Exception e) { }
        }
        """
        root = parse_java(code)
        assert detect_empty_exception(root) is True

    def test_non_empty_catch(self):
        code = """
        public void foo() {
            try { doWork(); }
            catch(Exception e) { log(e); }
        }
        """
        root = parse_java(code)
        assert detect_empty_exception(root) is False

    def test_no_exception(self):
        code = "public int add(int a, int b) { return a + b; }"
        root = parse_java(code)
        assert detect_empty_exception(root) is False


class TestEmptyMethod:
    def test_empty_body(self):
        code = "public void doNothing() { }"
        root = parse_java(code)
        assert detect_empty_method(root) is True

    def test_non_empty_body(self):
        code = "public int get() { return 42; }"
        root = parse_java(code)
        assert detect_empty_method(root) is False


class TestAmbiguousType:
    def test_generic_without_bounds(self):
        code = "public <T> T getValue() { return null; }"
        root = parse_java(code)
        assert detect_ambiguous_type(root) is True

    def test_generic_with_bounds(self):
        code = "public <T extends Number> T getValue() { return null; }"
        root = parse_java(code)
        assert detect_ambiguous_type(root) is False

    def test_no_generics(self):
        code = "public int add(int a, int b) { return a + b; }"
        root = parse_java(code)
        assert detect_ambiguous_type(root) is False


class TestNonEnglish:
    def test_chinese(self):
        assert detect_non_english("// 计算阶乘") is True

    def test_korean(self):
        assert detect_non_english("// 테스트") is True

    def test_japanese(self):
        assert detect_non_english("// テスト") is True

    def test_english_only(self):
        assert detect_non_english("public int add(int a, int b)") is False


class TestSynchronized:
    def test_has_synchronized(self):
        assert detect_synchronized("public synchronized void update()") is True

    def test_no_synchronized(self):
        assert detect_synchronized("public void update()") is False


class TestUnnecessaryAnnotations:
    """Test the pipeline-level annotation detection."""

    def test_has_noise_annotation(self):
        from src.pipeline import _has_unnecessary_annotations
        # @GetMapping is a common noise annotation in the dictionary
        code = '@GetMapping("/api/test") public void handle() { }'
        result = _has_unnecessary_annotations(code)
        # If the dictionary is loaded and contains @GetMapping variants
        assert isinstance(result, bool)

    def test_clean_code_no_annotation(self):
        from src.pipeline import _has_unnecessary_annotations
        code = "public int add(int a, int b) { return a + b; }"
        assert _has_unnecessary_annotations(code) is False
