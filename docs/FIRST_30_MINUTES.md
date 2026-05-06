# First 30 Minutes With Cool

This walkthrough is the adoption smoke path for new users and package-manager
maintainers. It should work after installing from a public release archive,
Homebrew formula, Winget manifest, or Debian/apt package.

## 1. Confirm The Tool

```bash
cool help
printf 'print("hello from Cool")\n' > hello.cool
cool hello.cool
```

The banner and help output should report the installed release version.

## 2. Create A Small Project

Use a scaffolded project as the install-independent path:

```bash
cd "$(mktemp -d)"
cool new first30
cd first30
cool src/main.cool
cool --vm src/main.cool
cool check src/main.cool
cool build
./first30
```

## 3. What This Proves

- Interpreter and VM paths run the same user program.
- `cool check` accepts the source before native build.
- `cool build` creates a native binary from a project manifest.
- The installed binary can compile and run code without relying on repository
  internals.

The repository also keeps `examples/first_30_minutes/` as a deterministic CI
fixture for this workflow.

## 4. Package-Manager Smoke

After a package-manager submission is published, run the same path from a clean
shell where `cool` comes from that package manager:

```bash
cool help
cool check src/main.cool
cool build
./first30
```

Record failures in a hotfix issue if the package installs but cannot execute
the first-30-minutes path.
