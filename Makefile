.PHONY: test test-python test-all check clean

# Run Python tests
test: test-python

test-python:
	python3 -c "import sys, unittest; sys.path.insert(0, 'src'); suite = unittest.defaultTestLoader.discover('tests_python'); result = unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())"

# Run all checks
test-all: test-python

check: test-all

# Clean Python build artifacts
clean:
	python3 -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
