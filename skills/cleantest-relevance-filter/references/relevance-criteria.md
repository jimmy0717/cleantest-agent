# Relevance Criteria

## Definition

A test case `t` is considered **relevant** to its focal method `f` if `t` exercises the behavior defined by `f`, either directly or indirectly.

## Stage A: AST Name Matching (Deterministic)

**Relevant** if:
- At least one `(method_name, parameter_count)` tuple from `f`'s method declarations
  appears in `t`'s method invocations.

**Irrelevant** (proceed to Stage B) if:
- Zero intersection between the two sets.

## Stage B: LLM Semantic Judgment (Borderline)

The following cases are considered **indirectly relevant** and should be labeled "RELEVANT":

1. **Wrapper methods**: `t` calls a method that internally delegates to `f`.
   - Example: `t` calls `order.getTotal()` which internally calls `calculateTotal()`.

2. **Inheritance**: `t` calls an overridden version of `f` in a subclass.
   - Example: `f` is `Base.process()`, `t` calls `Derived.process()`.

3. **Aliases**: `t` calls a method with a different name that is semantically equivalent.
   - Example: `f` is `save()`, `t` calls `persist()` which is an alias.

4. **Side effects**: `t` observes a side effect caused by `f` without calling it directly.
   - Example: `f` is `incrementCounter()`, `t` checks `getCounter() == 1` after setup.

The following cases should be labeled "IRRELEVANT":

1. **Completely unrelated**: `t` tests a different method with no connection to `f`.
2. **Same class, different method**: `t` tests another method in the same class.
3. **Shared utility only**: `t` and `f` both call `assertEquals` but have no other overlap.
