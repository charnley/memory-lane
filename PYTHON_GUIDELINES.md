# Python Development Guidelines

This document outlines the best practices and guidelines for writing Python code in this project.

## Code Style

We adhere to the [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/). All code should be formatted to be compliant with this standard. We use `black` for automatic code formatting to ensure consistency.

## Type Hinting

All new code should include type hints as specified in [PEP 484 -- Type Hints](https://www.python.org/dev/peps/pep-0484/). Type hints improve code clarity and allow for static analysis.

Example:
```python
def greet(name: str) -> str:
    return f"Hello, {name}"
```

## Data Models with Pydantic

For defining data models, data transfer objects (DTOs), or configuration settings, we exclusively use [Pydantic](https://docs.pydantic.dev/). Pydantic enforces type hints at runtime and provides user-friendly validation errors.

### Why Pydantic?

- **Type Enforcement**: Ensures that the data conforms to the defined model.
- **Data Validation**: Provides clear and detailed error messages for invalid data.
- **Editor Support**: Great IDE and editor support for autocompletion and type checking.
- **Serialization**: Easily convert models to and from JSON.
- **Settings Management**: Create strongly-typed configuration models.

### Basic Example

Instead of using a plain `dict` or `dataclass`, define a Pydantic model.

```python
from pydantic import BaseModel, EmailStr, PositiveInt

class UserProfile(BaseModel):
    """
    Represents a user's profile.
    """
    username: str
    email: EmailStr
    age: PositiveInt | None = None

# Creating an instance
try:
    user = UserProfile(username="johndoe", email="johndoe@example.com", age=25)
    print(user.model_dump_json())
except ValueError as e:
    print(e)

# Invalid data will raise a ValidationError
try:
    invalid_user = UserProfile(username="jane", email="jane-not-an-email")
except ValueError as e:
    print(e)
```

All data structures that represent a fixed schema should be defined using Pydantic's `BaseModel`.

## Dependencies

Project dependencies are managed using `pip` and a `requirements.txt` file.

- To add a new dependency, add it to `requirements.txt`.
- To install dependencies, run: `pip install -r requirements.txt`

## Testing

We use `pytest` for writing and running tests. All new features should be accompanied by tests, and bug fixes should include a regression test.

## Linting and Formatting

We use `ruff` for linting and `black` for code formatting. It is recommended to run these tools before committing code.
