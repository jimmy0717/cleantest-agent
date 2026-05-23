# Noise Rules Reference

This document defines the noise types detected by the syntax filter: 6 types from the original CleanTest paper (N1–N6).

## N1: Syntax Errors

**Detection**: tree-sitter AST contains `ERROR` node, or `method_declaration` lacks a `block` child.

**Example**:
```java
public int getCount(List<Item> items) {
    int count = 0;
    for (Item item : items) {
        if (item.isActive()) {
            count++;
    // missing closing braces → ERROR node
```

**LLM Enhancement**: When flagged, LLM confirms whether the code is truly broken or just uses unusual syntax that confuses the parser.

## N2: Empty Exception Handling Statement

**Detection**: `catch_clause` or `finally_clause` with a `block` child that has < 3 AST children (i.e., only `{` and `}`).

**Example**:
```java
try { doWork(); }
catch (IOException e) { }  // empty catch — exception caught but not handled
```

## N3: Missing Implementation (Empty Function)

**Detection**: `method_declaration` with a `block` child that has < 3 AST children.

**Example**:
```java
public void initialize() { }
```

This noise type occurs when a method lacks implementation details, often because the function is defined elsewhere in the project, resulting in incomplete information in the dataset.

**LLM Enhancement**: Some minimal methods (e.g., `return;` or `return null;`) may be intentional. LLM is asked to confirm.

## N4: Ambiguous Data Type

**Detection**: `method_declaration` contains `type_parameters` with generic markers like `<E>`, `<T>`, `<K>`, `<V>`, `<N>`, `<?>`.

**Example**:
```java
public <T> T deserialize(String json) { ... }
```

Unclear parameters and return values (e.g., type `Object` or unbounded generics) make it challenging for test generation models to understand the method's purpose and behavior.

## N5: Unnecessary Annotations

**Detection**: Aho-Corasick automaton built from 21,954 patterns in `noise_modifier_fm.txt`.

**Common patterns** (top 10 by frequency):
1. `@RequestMapping(...)`
2. `@GetMapping(...)`
3. `@PostMapping(...)`
4. `@ApiOperation(...)`
5. `@ApiResponses(...)`
6. `@ApiParam(...)`
7. `@PreAuthorize(...)`
8. `@Produces(...)`
9. `@PathParam(...)`
10. `@Description(...)`

These annotations describe API/deployment metadata irrelevant to the focal method's test-generation behavior. The original paper removes all annotations uniformly to avoid the complexity of evaluating each annotation individually.

## N6: Non-English Literals

**Detection**: Regex matching CJK Unicode ranges (from the original paper):
- `[\uac00-\ud7ff]+` (Korean)
- `[\u4e00-\u9fa5]+` (Chinese)
- `[\u30a0-\u30ff\u3040-\u309f]+` (Japanese)

**Example**:
```java
// 计算个人所得税
public double calculateTax(double income) { ... }
```
