# Development

If you want to contribute to Wizarr, here is how

### Prerequisites

* Python3.11+

### Development Environment

1. Clone the repository with `git clone git@github.com:Wizarrrr/wizarr.git`
2. Move into the directory `cd wizarr`
3. (Optional but recommended) Create a python virtual environment with `python -m venv venv`
4. Enter the python venv with `source venv/bin/activate`
5. Install dependencies with `uv sync --locked`
6. Start Wizarr with `flask run`
7. Wizarr is now accessible at http://127.0.0.1:5000

### Running Tests

To run the test suite, ensure your dependencies (including development dependencies) are installed, then invoke pytest via `uv`:

```bash
uv sync --locked
uv run pytest
```
