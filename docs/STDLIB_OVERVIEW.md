# Standard Library Overview

Cool ships a broad standard library under `stdlib/`, plus built-in runtime
modules implemented in Rust for host integration.

## Data And Text

Use `json`, `csv`, `toml`, `yaml`, `xml`, `html`, `bytes`, `base64`, `codec`,
`unicode`, `locale`, `config`, and `schema` for structured data and text
processing.

## Filesystem, OS, And Processes

Use `path`, `glob`, `tempfile`, `fswatch`, `process`, `platform`, `subprocess`,
`daemon`, `sandbox`, `sync`, and `store` for hosted automation and project
state.

## Networking And Services

Use `http`, `socket`, `websocket`, `rpc`, `graphql`, `url`, `mail`, `feed`,
`calendar`, and `cluster` for service and automation workflows.

## Runtime, Tooling, And Observability

Use `event`, `workflow`, `agent`, `retry`, `metrics`, `trace`, `profile`,
`bench`, `notebook`, `secrets`, `doc`, `template`, `lexer`, `parser`, `ast`,
`inspect`, `diff`, `patch`, `project`, `release`, `repo`, `modulegraph`,
`plugin`, `lsp`, `ffiutil`, and `shell`.

## Math, Data Science, And Media

Use `decimal`, `money`, `stats`, `vector`, `matrix`, `geom`, `graph`, `tree`,
`pipeline`, `stream`, `table`, `search`, `embed`, `ml`, `image`, `audio`,
`sprite`, and `game`.

## Compatibility Practice

When a stdlib behavior becomes part of the stable user contract, add either a
focused Rust regression test or a conformance case. Prefer deterministic tests
that avoid real network services, wall-clock timing, terminal state, or external
credentials.
