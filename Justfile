default: tests

# normalize Python code
black:
    pipx run black delb_existdb tests

# verifies testable code snippets in the HTML documentation
doctest:
    pipx run hatch run docs:clean
    pipx run hatch run docs:doctest

# code & data & document linting with doc8 & flake8 & yamllint
lint:
    pipx run doc8 --ignore-path docs/build --max-line-length=80 docs
    pipx run hatch run linting:check
    pipx run yamllint $(find . -name "*.yaml" -or -name "*.yml")

# run static type checks with mypy
mypy:
    pipx run hatch run mypy:check

# run the complete testsuite
pytest:
    pipx run hatch run tests:check

# run the complete testsuite and report code coverage
pytest-coverage-report:
    pipx run hatch run tests:coverage-report

# watch, build and serve HTML documentation at 0.0.0.0:8000
serve-docs:
    mkdir -p {{ justfile_directory() }}/docs/_build/html || true
    pipx run hatch run docs:serve

tests: black lint mypy pytest doctest
