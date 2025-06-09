# Development

If you want to contribute to Wizarr, here is how

### Prerequisites

* [uv](https://docs.astral.sh/uv/)

### Development Environment

1. Clone the repository with `git clone git@github.com:Wizarrrr/wizarr.git`
2. Move into the directory `cd wizarr`
3. Start Wizarr with `uv run flask run`
4. Wizarr is now accessible at http://127.0.0.1:5000

### Running Tests

To run the test suite, ensure your dependencies (including development dependencies) are installed, then invoke pytest via `uv`:

```bash
uv sync --locked
uv run pytest
```
