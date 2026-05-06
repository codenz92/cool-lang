# Language Reference

This page is the stable 1.x language map. The README remains the broad feature
tour; this page names the areas that users can rely on and that conformance
tests should protect.

## Core Syntax

- Indentation-based blocks.
- Comments with `#`.
- Integers, floats, strings, booleans, nil, lists, dicts, tuples, and structs.
- Arithmetic, comparison, logical, bitwise, power, floor-division, membership,
  and slicing expressions.
- `if` / `elif` / `else`, `while`, `for`, `break`, and `continue`.
- `def`, `return`, closures, lambdas, default arguments, keyword arguments,
  `*args`, and `**kwargs`.
- `class`, `self`, inheritance, `super()`, methods, and common operator hooks.
- `try` / `except` / `else` / `finally`, `raise`, `assert`, and `with`.

## Typed Surface

- Typed bindings: `name: Type = expr`.
- Constants: `const NAME: Type = expr`.
- Function signatures: `def f(x: int) -> int`.
- `struct`, `packed struct`, `union`, `enum`, `match`, `trait`, `implements`,
  generic definitions, trait bounds, and typed collection surfaces.

The interpreter and VM accept the typed syntax for parity. Native builds lower
ABI-compatible annotations to LLVM types where supported.

## Modules

- Built-in imports such as `math`, `os`, `sys`, `path`, `platform`, `core`,
  `json`, `re`, `time`, `random`, `collections`, `socket`, `http`, `sqlite`,
  `subprocess`, `argparse`, `logging`, and `test`.
- Source-relative imports: `import "helper.cool"`.
- Project/package imports: `import foo.bar`.
- Top-level `public` / `private` controls module export visibility.

## Compatibility

Stable hosted behavior should match across interpreter, VM, and native runtime
when the selected runtime supports the feature. See `docs/COMPATIBILITY.md` and
`docs/CONFORMANCE.md` for the executable compatibility contract.
