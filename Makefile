.PHONY: test test-unit test-integration test-cli test-all check fmt clippy clean

# Run all tests
test:
	cargo test --workspace

# Run unit tests only (inline #[cfg(test)] modules)
test-unit:
	cargo test --workspace --lib

# Run integration tests only (tests/ directory)
test-integration:
	cargo test --workspace --test '*'

# Run CLI integration tests
test-cli:
	cargo test -p ralph

# Run all checks (test + clippy + fmt)
test-all: test clippy fmt-check

# Clippy lint
clippy:
	cargo clippy --workspace -- -D warnings

# Format check
fmt-check:
	cargo fmt --all -- --check

# Format fix
fmt:
	cargo fmt --all

# Clean build artifacts
clean:
	cargo clean
