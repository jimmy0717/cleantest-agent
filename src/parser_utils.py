"""Tree-sitter based Java AST parsing utilities.

All AST traversals use iterative stack-based DFS to avoid RecursionError
on deeply nested code.
"""

import re
from typing import List, Tuple

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

# Initialize Java parser
JAVA_LANGUAGE = Language(tsjava.language())
_parser = Parser(JAVA_LANGUAGE)


def get_parser() -> Parser:
    """Return the shared Java parser instance."""
    return _parser


def parse_java(code: str):
    """Parse Java source code and return the root AST node."""
    tree = _parser.parse(bytes(code, "utf-8"))
    return tree.root_node


# ---------------------------------------------------------------------------
# Noise detection functions (iterative, stack-based)
# ---------------------------------------------------------------------------

def detect_grammar_errors(root_node) -> bool:
    """Check if the AST contains ERROR nodes or method_declarations without block."""
    stack = [root_node]
    while stack:
        node = stack.pop()
        if len(node.children) == 0 or node.type == "string":
            continue
        if node.type == "ERROR":
            return True
        if node.type == "method_declaration":
            child_types = [c.type for c in node.children]
            if "block" not in child_types:
                return True
        stack.extend(node.children)
    return False


def detect_empty_exception(root_node) -> bool:
    """Check if code has empty catch/finally blocks."""
    stack = [root_node]
    while stack:
        node = stack.pop()
        if len(node.children) == 0 or node.type == "string":
            continue
        if node.type in ("catch_clause", "finally_clause"):
            for child in node.children:
                if child.type == "block" and len(child.children) < 3:
                    return True
        stack.extend(node.children)
    return False


def detect_empty_method(root_node) -> bool:
    """Check if code has methods with empty bodies."""
    stack = [root_node]
    while stack:
        node = stack.pop()
        if len(node.children) == 0 or node.type == "string":
            continue
        if node.type == "method_declaration":
            for child in node.children:
                if child.type == "block" and len(child.children) < 3:
                    return True
        stack.extend(node.children)
    return False


def detect_ambiguous_type(root_node) -> bool:
    """Check if method uses generics without type bounds (extends)."""
    stack = [root_node]
    while stack:
        node = stack.pop()
        if len(node.children) == 0 or node.type == "string":
            continue
        if node.type == "method_declaration":
            for child in node.children:
                if child.type == "type_parameters":
                    text = child.text.decode("utf-8")
                    if "<" in text and ">" in text and "extends" not in text:
                        return True
        stack.extend(node.children)
    return False


def detect_non_english(source_code: str) -> bool:
    """Check if source code contains non-English (CJK) literals."""
    cjk_pattern = re.compile(
        r"[\u4e00-\u9fa5\uac00-\ud7ff\u30a0-\u30ff\u3040-\u309f]+"
    )
    return bool(cjk_pattern.search(source_code))


def detect_synchronized(source_code: str) -> bool:
    """Check if source code contains synchronized keywords."""
    return "synchronized" in source_code


def replace_unnecessary_annotations(
    source_code: str, noise_modifiers: List[str]
) -> Tuple[bool, str]:
    """Remove unnecessary annotations from source code.

    Returns (was_modified, cleaned_code).
    """
    modified = False
    for modifier in noise_modifiers:
        if modifier in source_code:
            modified = True
            source_code = source_code.replace(modifier, "")
    return modified, source_code


# ---------------------------------------------------------------------------
# Relevance detection (iterative)
# ---------------------------------------------------------------------------

def extract_src_methods(root_node) -> List[Tuple[str, int]]:
    """Extract (method_name, param_count) from focal method declarations."""
    methods: List[Tuple[str, int]] = []
    stack = [root_node]
    while stack:
        node = stack.pop()
        if len(node.children) == 0 or node.type == "string":
            continue
        if node.type == "method_declaration":
            name = ""
            num_params = 0
            for child in node.children:
                if child.type == "identifier":
                    name = child.text.decode("utf-8")
                if child.type == "formal_parameters":
                    num_params = sum(
                        1 for c in child.children
                        if c.type == "formal_parameter"
                    )
            if name:
                methods.append((name, num_params))
        stack.extend(node.children)
    return methods


def extract_test_invocations(root_node) -> List[Tuple[str, int]]:
    """Extract (invoked_method_name, arg_count) from test method invocations."""
    invocations: List[Tuple[str, int]] = []
    stack = [root_node]
    while stack:
        node = stack.pop()
        if len(node.children) == 0 or node.type == "string":
            continue
        if node.type == "method_invocation":
            name = ""
            num_args = 0
            for child in node.children:
                if child.type == "identifier":
                    name = child.text.decode("utf-8")
                if child.type == "argument_list":
                    num_args = sum(
                        1 for c in child.children
                        if c.type not in (",", "(", ")")
                    )
            if name:
                invocations.append((name, num_args))
        stack.extend(node.children)
    return invocations


def compute_relevance(
    src_methods: List[Tuple[str, int]],
    test_invocations: List[Tuple[str, int]]
) -> int:
    """Compute intersection size between focal methods and test invocations."""
    return len(set(src_methods) & set(test_invocations))
