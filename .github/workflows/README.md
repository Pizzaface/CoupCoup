# GitHub Actions Workflows

This directory contains automated CI/CD workflows for the CoupCoup project.

## Available Workflows

### 1. Tests (`tests.yml`)

**Triggers:**
- Push to: `main`, `master`, `develop`, `claude/*` branches
- Pull requests to: `main`, `master`, `develop`

**What it does:**
- Sets up Python 3.11 environment
- Installs all dependencies (core + test dependencies)
- Runs full test suite with pytest
- Generates coverage reports (XML, HTML, terminal)
- Uploads coverage to Codecov
- Uploads test results as artifacts
- Comments coverage on pull requests

**Artifacts:**
- `coverage-report-*`: HTML and XML coverage reports (30 days retention)
- `test-results-*`: pytest cache and results (7 days retention)

### 2. Coverage Report (`coverage-report.yml`)

**Triggers:**
- Push to: `main`, `master`
- Pull requests to: `main`, `master`

**What it does:**
- Runs core tests for critical modules
- Generates detailed coverage reports
- Creates coverage badge
- Publishes coverage summary to workflow summary

**Focus:**
- `utils/text.py` (100% coverage)
- `utils/config.py` (100% coverage)
- `lib/RetryTransport.py` (98.81% coverage)

### 3. Lint (`lint.yml`)

**Triggers:**
- Push to: `main`, `master`, `develop`, `claude/*` branches
- Pull requests to: `main`, `master`, `develop`

**What it does:**
- Checks code formatting with Black
- Checks import sorting with isort
- Lints code with flake8
- Type checks with mypy

**Note:** All linting checks are non-blocking (won't fail the build)

## Viewing Results

### On Pull Requests

When you create a pull request, you'll see:
1. **Check runs** in the "Checks" tab
2. **Coverage comment** posted automatically
3. **Test results** summary

### On Push

After pushing to a branch:
1. Go to **Actions** tab
2. Select the workflow run
3. View logs and download artifacts

### Coverage Reports

Coverage reports are available in multiple formats:

1. **Terminal output**: View in workflow logs
2. **HTML report**: Download artifact and open `htmlcov/index.html`
3. **Codecov**: View at https://codecov.io/gh/Pizzaface/CoupCoup (if configured)

## Local Testing

Before pushing, run tests locally:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/utils/test_text.py -v

# Run with markers
pytest tests/ -m unit
pytest tests/ -m integration
```

## Workflow Status Badges

Add these badges to your README.md:

```markdown
![Tests](https://github.com/Pizzaface/CoupCoup/workflows/Tests/badge.svg)
![Coverage](https://github.com/Pizzaface/CoupCoup/workflows/Coverage%20Report/badge.svg)
![Lint](https://github.com/Pizzaface/CoupCoup/workflows/Lint/badge.svg)
```

## Workflow Configuration

### Caching

All workflows use pip caching to speed up dependency installation:
```yaml
cache: 'pip'
```

### Matrix Strategy

The test workflow supports multiple Python versions:
```yaml
strategy:
  matrix:
    python-version: ['3.11']
```

To test on more versions, add them to the matrix:
```yaml
python-version: ['3.10', '3.11', '3.12']
```

### Dependency Installation

Dependencies are installed in tiers:

1. **Core dependencies** (required)
   - pytest, coverage tools
   - pandas, httpx, pydantic
   - Core utilities

2. **Optional dependencies** (best effort)
   - google-generativeai
   - google-cloud-aiplatform
   - folium, openrouteservice

Optional dependencies use `continue-on-error: true` to prevent workflow failure.

## Troubleshooting

### Workflow Fails on Dependency Installation

If a workflow fails during dependency installation:

1. Check the error in the workflow logs
2. Update the dependency installation step
3. Consider marking problematic dependencies as optional

### Tests Pass Locally but Fail in CI

Common causes:

1. **Missing dependencies**: Add to workflow YAML
2. **Environment differences**: Check Python version, OS
3. **File paths**: Use relative paths
4. **Timing issues**: Add delays or increase timeouts

### Coverage Report Not Uploading

Check:

1. **coverage.xml exists**: Ensure pytest generates it
2. **Codecov token**: Set in repository secrets
3. **File permissions**: Ensure files are readable

## Best Practices

### 1. Keep Workflows Fast

- Use caching
- Install only necessary dependencies
- Run expensive tests separately

### 2. Fail Fast

- Use `--maxfail=5` to stop after 5 failures
- Set reasonable timeouts

### 3. Provide Context

- Use descriptive step names
- Add comments for complex logic
- Upload relevant artifacts

### 4. Monitor Coverage

- Set minimum coverage thresholds
- Review coverage trends
- Add tests for uncovered code

## Customization

### Add New Workflow

Create a new `.yml` file in `.github/workflows/`:

```yaml
name: My Workflow

on:
  push:
    branches: [ main ]

jobs:
  my-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Add your steps here
```

### Modify Existing Workflow

1. Edit the workflow YAML file
2. Test changes on a feature branch
3. Monitor workflow runs
4. Merge when stable

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Codecov Documentation](https://docs.codecov.com/)
