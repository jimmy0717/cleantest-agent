# Noise Rules Reference

This document defines the 7+1 noise types detected by the syntax filter.

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

## N2: Empty Exception Handler

**Detection**: `catch_clause` or `finally_clause` with a `block` child that has < 3 AST children (i.e., only `{` and `}`).

**Example**:
```java
try { doWork(); }
catch (IOException e) { }  // empty catch
```

## N3: Empty Method

**Detection**: `method_declaration` with a `block` child that has < 3 AST children.

**Example**:
```java
public void initialize() { }
```

**LLM Enhancement**: Some minimal methods (e.g., `return;` or `return null;`) may be intentional. LLM is asked to confirm.

## N4: Ambiguous Generic Type

**Detection**: `method_declaration` contains `type_parameters` with `<` and `>` but without `extends`.

**Example**:
```java
public <T> T deserialize(String json) { ... }
```

The type `T` is completely unconstrained, making the method's behavior ambiguous.

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

These annotations describe API/deployment metadata irrelevant to the focal method's test-generation behavior.

## N6: Non-English Literals

**Detection**: Regex matching CJK Unicode ranges:
- Chinese: `\u4e00-\u9fa5`
- Korean: `\uac00-\ud7ff`
- Japanese Katakana: `\u30a0-\u30ff`
- Japanese Hiragana: `\u3040-\u309f`

**Example**:
```java
// 计算个人所得税
public double calculateTax(double income) { ... }
```

## N7: Synchronized Keywords

**Detection**: Substring match for `"synchronized"` in focal method source code.

**Example**:
```java
public synchronized void incrementCounter() { this.counter++; }
```

The concurrency keyword adds noise orthogonal to the method's core behavior.
