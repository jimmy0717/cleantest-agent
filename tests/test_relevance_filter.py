"""Unit tests for relevance detection functions."""

import pytest
from cleantest_agent.parser_utils import (
    parse_java,
    extract_src_methods,
    extract_test_invocations,
    compute_relevance,
)


class TestExtractSrcMethods:
    def test_single_method(self):
        code = "public int add(int a, int b) { return a + b; }"
        root = parse_java(code)
        methods = extract_src_methods(root)
        assert len(methods) >= 1
        names = [m[0] for m in methods]
        assert "add" in names

    def test_method_param_count(self):
        code = "public String greet(String name) { return name; }"
        root = parse_java(code)
        methods = extract_src_methods(root)
        # Should find greet with 1 parameter
        assert any(m[0] == "greet" and m[1] == 1 for m in methods)


class TestExtractTestInvocations:
    def test_invocation_found(self):
        code = '@Test public void testAdd() { assertEquals(3, add(1, 2)); }'
        root = parse_java(code)
        invocations = extract_test_invocations(root)
        names = [inv[0] for inv in invocations]
        assert "add" in names or "assertEquals" in names

    def test_no_invocation(self):
        code = '@Test public void testEmpty() { int x = 1; }'
        root = parse_java(code)
        invocations = extract_test_invocations(root)
        # Should find no method invocations (only assignment)
        method_names = [inv[0] for inv in invocations]
        assert "add" not in method_names


class TestComputeRelevance:
    def test_overlap_exists(self):
        src = [("add", 2)]
        tgt = [("add", 2), ("assertEquals", 2)]
        assert compute_relevance(src, tgt) >= 1

    def test_no_overlap(self):
        src = [("add", 2)]
        tgt = [("length", 0), ("assertEquals", 2)]
        assert compute_relevance(src, tgt) == 0

    def test_empty_inputs(self):
        assert compute_relevance([], []) == 0
        assert compute_relevance([("add", 1)], []) == 0
