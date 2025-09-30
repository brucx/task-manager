# Test Suite Documentation

## Overview

Comprehensive test suite for the task-manager project covering unit tests, integration tests, and end-to-end workflows.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (75% of test coverage)
│   ├── test_models.py       # Task model validation
│   ├── test_storage.py      # Storage utilities
│   ├── test_cpu_worker.py   # CPU worker logic
│   └── test_gpu_worker.py   # GPU worker logic
├── integration/             # Integration tests (20% of test coverage)
│   ├── test_task_manager.py # Task manager coordination
│   └── test_api.py          # API endpoint integration
└── e2e/                     # End-to-end tests (5% of test coverage)
    └── test_workflow.py     # Complete workflows
```

## Prerequisites

### Install Test Dependencies

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Or install manually
uv pip install pytest pytest-asyncio httpx
```

### Redis Requirement

Integration and E2E tests require Redis:

```bash
# Start Redis (Docker)
docker run -d -p 6379:6379 redis:7

# Or use system Redis
redis-server
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### By Test Category

```bash
# Unit tests only (no external dependencies)
pytest tests/unit/ -v

# Integration tests (requires Redis)
pytest tests/integration/ -v -m integration

# E2E tests (requires full system)
pytest tests/e2e/ -v -m e2e

# Performance tests
pytest -m performance -v

# Exclude slow tests
pytest -m "not slow"
```

### By Component

```bash
# Test specific component
pytest tests/unit/test_models.py -v
pytest tests/unit/test_storage.py -v
pytest tests/unit/test_cpu_worker.py -v
pytest tests/unit/test_gpu_worker.py -v

# Test API endpoints
pytest tests/integration/test_api.py -v

# Test task manager
pytest tests/integration/test_task_manager.py -v
```

### Advanced Options

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Run specific test
pytest tests/unit/test_models.py::TestTaskState::test_task_state_values

# Show local variables on failure
pytest -l

# Capture output
pytest -s
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (requires Redis)
- `@pytest.mark.e2e` - End-to-end tests (requires full system)
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.stress` - Stress and load tests

## Test Fixtures

### Shared Fixtures (conftest.py)

- `async_client` - FastAPI async test client
- `sync_client` - FastAPI sync test client
- `temp_storage` - Temporary storage directory
- `task_id` - Generate unique task ID
- `sample_image` - Sample test image (800x600)
- `portrait_image` - Portrait aspect ratio image
- `landscape_image` - Landscape aspect ratio image
- `celery_app_eager` - Celery in eager mode for unit tests
- `skip_if_no_redis` - Skip test if Redis unavailable
- `skip_if_no_gpu` - Skip test if GPU unavailable

## Coverage Goals

| Component | Target | Current Status |
|-----------|--------|----------------|
| Core Logic | 95%+ | ⚠️ To be measured |
| Workers | 90%+ | ⚠️ To be measured |
| API Endpoints | 90%+ | ⚠️ To be measured |
| Utils | 85%+ | ⚠️ To be measured |
| Models | 80%+ | ⚠️ To be measured |

### Generate Coverage Report

```bash
# HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=src --cov-report=term-missing

# XML report (for CI)
pytest --cov=src --cov-report=xml
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/ -v

  integration-tests:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: pytest tests/integration/ -v
```

## Test Development Guidelines

### Writing New Tests

1. **Location**: Place tests in appropriate directory (unit/integration/e2e)
2. **Naming**: Use descriptive test names starting with `test_`
3. **Markers**: Apply appropriate pytest markers
4. **Fixtures**: Use existing fixtures from conftest.py
5. **Isolation**: Ensure tests are independent and can run in any order

### Example Test Structure

```python
import pytest
from src.models import TaskState

@pytest.mark.unit
class TestMyComponent:
    """Test my component functionality."""

    def test_basic_functionality(self, task_id):
        """Test should do X when Y happens."""
        # Arrange
        input_data = "test"

        # Act
        result = my_function(input_data)

        # Assert
        assert result == expected_output

    @pytest.mark.slow
    def test_complex_scenario(self, temp_storage, sample_image):
        """Test complex scenario requiring more setup."""
        # Test implementation
        pass
```

## Troubleshooting

### Common Issues

**Redis Connection Error**
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG
```

**Import Errors**
```bash
# Ensure PYTHONPATH is set correctly
export PYTHONPATH="${PYTHONPATH}:."
# Or run with pytest from project root
```

**Async Test Failures**
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio
# Check pytest.ini has: asyncio_mode = auto
```

**Fixture Not Found**
```bash
# Ensure conftest.py exists in tests/ directory
ls tests/conftest.py
```

## Performance Benchmarking

```bash
# Run performance tests with timing
pytest tests/performance/ -v --durations=10

# Profile test execution
pytest --profile

# Memory profiling (requires pytest-memray)
pytest --memray
```

## Test Data Management

Test data locations:
- Temporary files: Use `tmp_path` fixture (auto-cleaned)
- Test images: Use `sample_image`, `portrait_image`, `landscape_image` fixtures
- Storage: Use `temp_storage` fixture (isolated, auto-cleaned)

## Best Practices

1. **Fast Unit Tests**: Keep unit tests under 100ms each
2. **Isolated Tests**: No shared state between tests
3. **Clear Assertions**: One logical assertion per test
4. **Descriptive Names**: Test names should describe expected behavior
5. **Mock External Services**: Use mocks for external dependencies in unit tests
6. **Real Integration**: Use real services (Redis, etc.) in integration tests

## Continuous Improvement

### Adding New Tests

When adding new features:
1. Write unit tests first (TDD approach)
2. Add integration tests for component interactions
3. Add E2E test for complete workflow
4. Update this README if adding new test categories

### Maintaining Tests

- Review and update tests when changing code
- Remove obsolete tests
- Refactor common test patterns into fixtures
- Keep test coverage above 80%

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-Asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Celery Testing](https://docs.celeryproject.org/en/stable/userguide/testing.html)