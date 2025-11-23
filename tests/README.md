# CoupCoup Test Suite

Comprehensive test framework for the CoupCoup project, designed to achieve 90%+ code coverage.

## Overview

This test suite provides comprehensive coverage of the CoupCoup codebase, including:

- **Unit Tests**: Testing individual functions and classes in isolation
- **Integration Tests**: Testing interactions between multiple components
- **Fixtures & Factories**: Reusable test data generators using Factory Boy

## Test Structure

```
tests/
├── conftest.py                  # Shared fixtures and configuration
├── factories.py                 # Factory Boy factories for test data
├── README.md                    # This file
├── unit/                        # Unit tests
│   ├── lib/                     # Tests for lib/ modules
│   │   └── test_retry_transport.py
│   ├── stores/                  # Tests for store implementations
│   │   ├── test_base_store.py
│   │   └── test_flipp.py
│   ├── utils/                   # Tests for utility modules
│   │   ├── test_call_ai_model_gemini.py
│   │   ├── test_config.py
│   │   ├── test_jinja.py
│   │   ├── test_matching.py
│   │   ├── test_random_utils.py
│   │   └── test_text.py
│   ├── test_all_imports.py     # Smoke tests for all modules
│   └── test_main.py             # Tests for main orchestration
└── integration/                 # Integration tests
    └── test_store_workflow.py   # End-to-end workflow tests
```

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/ -m integration

# Specific module
pytest tests/unit/utils/test_text.py
```

### Run Tests in Parallel
```bash
pytest tests/ -n auto
```

## Test Coverage Goals

### Current Coverage by Module

#### High Coverage (90%+)
- `utils/text.py` - 100%
- `utils/config.py` - 100%
- `lib/RetryTransport.py` - 98.81%

#### Moderate Coverage (50-89%)
- Tests implemented but pending dependency resolution

#### Low Coverage (<50%)
- Modules requiring integration with external services
- Browser-based store scrapers (Pyppeteer dependency)
- Geocoding/routing modules (OpenRouteService integration)

### Path to 90%+ Coverage

To achieve 90%+ overall coverage:

1. **Install All Dependencies**
   ```bash
   pip install -e .
   pip install -r requirements-dev.txt
   ```

2. **Run Complete Test Suite**
   - All existing tests cover critical paths
   - Import tests exercise module-level code
   - Integration tests cover workflows

3. **Add Store-Specific Tests**
   - Tests for individual Flipp store implementations
   - Tests for standalone stores (Walgreens, Publix, etc.)
   - Tests for coupon scrapers

4. **Add Workflow Tests**
   - End-to-end scraping workflows
   - AI extraction pipelines
   - Matching and comparison logic

## Test Categories

### Unit Tests

#### Utils Module Tests
- **test_text.py**: Text cleaning and sanitization
  - 15 test cases covering all edge cases
  - Parametrized tests for common patterns
  - 100% coverage of utils/text.py

- **test_config.py**: Configuration management
  - Config file reading/parsing
  - Error handling for missing configs
  - Type conversions (int, float, boolean)
  - 100% coverage of utils/config.py

- **test_matching.py**: Fuzzy string matching
  - Multi-column matching logic
  - Brand filtering
  - Threshold testing
  - Real-world scenario tests
  - Comprehensive coverage of matching algorithms

- **test_call_ai_model_gemini.py**: AI model integration
  - Vertex AI and AI Studio calls
  - Retry logic testing
  - Response parsing
  - Error handling
  - Tool definition validation

#### Lib Module Tests
- **test_retry_transport.py**: HTTP retry logic
  - Exponential backoff calculation
  - Jitter implementation
  - Retry-After header handling
  - Async and sync request handling
  - 98.81% coverage

#### Store Module Tests
- **test_base_store.py**: Core store functionality
  - Excel I/O operations
  - Worksheet management
  - Data validation
  - Queue processing
  - Async context manager

- **test_flipp.py**: Flipp API integration
  - API URL generation
  - Flyer retrieval
  - Product parsing
  - Date/price handling
  - Retry logic

### Integration Tests

- **test_store_workflow.py**: End-to-end workflows
  - Complete store scraping cycle
  - Data processing pipeline
  - Excel file generation

### Fixtures and Factories

#### Key Fixtures (conftest.py)
- `temp_config_file`: Temporary test configuration
- `mock_config`: Mocked configuration parser
- `temp_excel_file`: Temporary Excel workbooks
- `sample_product_data`: Product data dictionaries
- `sample_dataframe`: Pandas DataFrames for testing
- `mock_httpx_client`: Mocked HTTP client
- `mock_gemini_response`: Mocked AI responses
- `mock_logger`: Mocked logging

#### Factories (factories.py)
- `ProductFactory`: Generate product test data
- `CouponFactory`: Generate coupon test data
- `FlippFlyerFactory`: Generate Flipp flyer data
- `FlippProductFactory`: Generate Flipp product data
- `StoreConfigFactory`: Generate store configurations
- `GeminiResponseFactory`: Generate AI responses

## Writing New Tests

### Test Naming Convention
```python
def test_<function_name>_<scenario>():
    """Test that <function_name> <expected_behavior>."""
    pass
```

### Using Fixtures
```python
def test_example(mock_config, sample_product_data):
    """Test using fixtures."""
    # Fixtures are automatically provided
    assert mock_config['config']['GOOGLE_API_KEY'] == 'test-api-key'
    assert sample_product_data['brand_name'] == 'Test Brand'
```

### Using Factories
```python
from tests.factories import ProductFactory

def test_with_factory():
    """Test using factories."""
    product = ProductFactory()
    assert 'brand_name' in product
    assert 'price' in product
```

### Async Tests
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality."""
    result = await some_async_function()
    assert result is not None
```

### Parametrized Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
])
def test_parametrized(input, expected):
    """Test with multiple inputs."""
    assert input.upper() == expected
```

## Coverage Analysis

### Generate HTML Coverage Report
```bash
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

### View Coverage in Terminal
```bash
pytest tests/ --cov=. --cov-report=term-missing
```

### Coverage Configuration
Coverage settings are defined in `pyproject.toml`:
- Minimum coverage threshold (configurable)
- Excluded files (tests, venv, etc.)
- Excluded lines (pragma: no cover, etc.)

## Dependencies

### Core Test Dependencies
- pytest: Test framework
- pytest-asyncio: Async test support
- pytest-cov: Coverage reporting
- pytest-mock: Mocking support
- pytest-timeout: Test timeout handling
- factory-boy: Test data factories
- faker: Fake data generation
- respx: HTTP mocking
- freezegun: Time mocking

### Install Test Dependencies
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-xdist \
            factory-boy faker respx freezegun pytest-timeout
```

## Best Practices

### 1. Test Independence
- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 2. Descriptive Test Names
- Use clear, descriptive names
- Follow naming conventions
- Include docstrings

### 3. Comprehensive Coverage
- Test happy paths
- Test error conditions
- Test edge cases
- Test boundary conditions

### 4. Mock External Dependencies
- Mock API calls
- Mock file I/O when appropriate
- Mock time-dependent functions
- Use fixtures for consistent mocks

### 5. Keep Tests Fast
- Mock slow operations
- Use in-memory databases
- Minimize file I/O
- Run slow tests separately

## Troubleshooting

### Common Issues

#### Import Errors
If you encounter import errors, ensure all dependencies are installed:
```bash
pip install -e .
```

#### Async Test Failures
Ensure pytest-asyncio is installed and configured in pyproject.toml:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

#### Coverage Too Low
1. Check which files are not covered: `pytest --cov=. --cov-report=term-missing`
2. Add tests for uncovered modules
3. Review coverage report: `open htmlcov/index.html`

#### Test Timeouts
Increase timeout in pyproject.toml:
```toml
[tool.pytest.ini_options]
timeout = 600
```

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Ensure tests pass: `pytest tests/`
3. Check coverage: `pytest --cov=.`
4. Update this README if needed

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: pip install pytest pytest-cov pytest-asyncio
      - run: pytest tests/ --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

## License

Same as main project.
