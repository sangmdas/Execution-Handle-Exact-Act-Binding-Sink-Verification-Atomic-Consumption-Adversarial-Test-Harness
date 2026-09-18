# Recorded Test Results

These results are checked-in evidence from one execution environment. They should be reproduced on the target platform before making deployment claims.

## Environment

- Platform: `Linux-6.18.44-x86_64-with-glibc2.41`
- Machine: `x86_64`
- Python: `3.13.5`
- Node.js: `v22.16.0`
- Go: `go version go1.23.2 linux/amd64`

## Conformance/adversarial suite

- Tests: **36/36 passed**
- Cross-language canonicalization: **Python = Node.js = Go** for all golden vectors
- Golden-vector match: **passed**

## Variable/domain matrix

- Matrix cases: **12/12 passed**
- Profiles: agent-tool, payment, cloud-egress, industrial
- Concurrency levels: 2, 8, 32, 64
- SINGLE_USE result at each concurrency level: exactly one successful commit, all remaining attempts rejected with `EF-005`

## Deterministic mutation probe

- Seed: `0xEFA11`
- Cases: **2000**
- Reordered-equivalent values retaining identical digest: **2000/2000**
- Single-argument mutations changing digest: **2000/2000**

## Local durability benchmark

- Iterations: **1000**
- End-to-end issue + protected local commit: **1041.3 ops/s**
- Protected local commit p50: **0.570 ms**
- p95: **0.698 ms**
- p99: **1.001 ms**
- max: **2.310 ms**

This benchmark is a Python/SQLite reference measurement only. It excludes network, distributed consensus, real payment/actuation systems, HSM/TEE operations, and external irreversible-effect coordination.

## Cross-platform status

The GitHub Actions workflow is configured for Ubuntu, Windows, and macOS with Python 3.11–3.13. The checked-in result above is only the environment actually executed here. Do not describe Windows/macOS as verified until those CI jobs have run successfully.
