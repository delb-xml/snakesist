default: tests

# normalize Python code
black:
    pipx run black snakesist tests

# verifies testable code snippets in the HTML documentation
doctest:
    pipx run hatch run docs:clean
    pipx run hatch run docs:doctest

# run static type checks with mypy
mypy:
    pipx run hatch run mypy:check

# run the complete testsuite
pytest:
    pipx run hatch run tests:check

# watch, build and serve HTML documentation at 0.0.0.0:8000
serve-docs:
    mkdir -p {{ justfile_directory() }}/docs/_build/html || true
    pipx run hatch run docs:serve

tests: black mypy pytest doctest
