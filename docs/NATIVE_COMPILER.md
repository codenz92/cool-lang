# Native Compiler

Cool's primary identity is native-first. Interpreter and VM modes are
development and parity tools; release binaries come from `cool build`.

## Common Builds

```bash
cool build hello.cool
cool build --profile dev
cool build --profile strict hello.cool
cool build --debug --reproducible hello.cool
cool build --emit object hello.cool
cool build --emit staticlib
cool build --emit sharedlib
```

## Targets And CPU Features

```bash
cool build --target x86_64-unknown-linux-gnu --emit llvm-ir hello.cool
cool build --cpu native --cpu-features +sse4.2,+popcnt hello.cool
```

Project defaults live under `[build]` in `cool.toml`, including `profile`,
`emit`, `target`, `cpu`, `cpu_features`, `incremental`, `reproducible`, and
`debug`.

## Freestanding And No-Libc

```bash
cool build --freestanding hello.cool
cool build --no-libc --entry _start hello.cool
cool build --linker-script=link.ld hello.cool
```

Freestanding programs use declaration-style top-level code and can emit objects
or linked kernel images without the hosted runtime.

## Release Expectations

Native compiler changes should run:

```bash
bash scripts/release_gate.sh
bash scripts/conformance_suite.sh
bash scripts/performance_baseline.sh --filter integer_loop --runs 1 --warmups 0 --output-dir /tmp/cool-perf
```

Use the benchmark baseline as a regression signal, not as a universal
performance claim.
