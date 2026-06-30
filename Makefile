.PHONY: test test-python test-all check clean rust-test rust-test-unit rust-test-integration rust-test-cli rust-clippy rust-fmt-check rust-fmt rust-clean

# Run Python tests
test: test-python

test-python:
	python3 -c "import sys, unittest; sys.path.insert(0, 'src'); suite = unittest.defaultTestLoader.discover('tests_python'); result = unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())"

# Run all Python checks
test-all: test-python

check: test-all

# Clean Python build artifacts
clean:
	python3 -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"

# Legacy Rust targets kept while the repository is migrated to Python.
rust-test:
	cargo test --workspace

rust-test-unit:
	cargo test --workspace --lib

rust-test-integration:
	cargo test --workspace --test '*'

rust-test-cli:
	cargo test -p ralph

rust-clippy:
	cargo clippy --workspace -- -D warnings

rust-fmt-check:
	cargo fmt --all -- --check

rust-fmt:
	cargo fmt --all

rust-clean:
	cargo clean
