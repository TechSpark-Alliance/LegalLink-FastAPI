# LegalLink-FastAPI

LegalLink-FastAPI is a FastAPI application designed to provide a robust and scalable backend solution for legal services. This project structure is organized to facilitate development, testing, and deployment.

## Project Structure

```
LegalLink-FastAPI
├── main_app
│   ├── main.py               # Entry point of the FastAPI application
│   ├── __init__.py          # Marks main_app as a Python package
│   ├── api                   # Contains API-related code
│   │   ├── __init__.py      # Marks api as a Python package
│   │   ├── deps.py          # Dependency functions for API routes
│   │   └── v1                # Version 1 of the API
│   │       ├── __init__.py  # Marks v1 as a Python package
│   │       ├── routes.py     # API route definitions
│   │       └── schemas.py    # Pydantic models for request/response
│   ├── core                  # Core application logic
│   │   ├── __init__.py      # Marks core as a Python package
│   │   ├── config.py        # Configuration settings
│   │   └── security.py      # Security-related functions
│   ├── db                    # Database-related code
│   │   ├── __init__.py      # Marks db as a Python package
│   │   ├── base.py          # Base class for database models
│   │   ├── models.py        # Database models
│   │   └── session.py       # Database session management
│   ├── services              # Business logic and services
│   │   └── __init__.py      # Marks services as a Python package
│   └── utils                 # Utility functions
│       └── __init__.py      # Marks utils as a Python package
├── tests                     # Test suite for the application
│   ├── __init__.py          # Marks tests as a Python package
│   ├── conftest.py          # Configuration for pytest
│   └── test_health.py       # Tests for health check endpoint
├── requirements.txt          # Project dependencies
├── Dockerfile                # Docker image instructions
├── .env.example              # Example environment variables
├── pyproject.toml           # Project configuration
└── README.md                 # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd LegalLink-FastAPI
   ```

2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables by copying `.env.example` to `.env` and modifying as needed.

## Usage

To run the application, execute the following command:
```
uvicorn main_app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` to access the interactive API documentation.

## Testing

To run the tests, use:
```
pytest
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.