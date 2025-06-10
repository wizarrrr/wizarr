# Development

If you want to contribute to Wizarr, here is how

### Prerequisites

* [uv](https://docs.astral.sh/uv/)
* Node.js/npm - [nvm](https://github.com/nvm-sh/nvm) recommended

### Development Environment

1. Clone the repository with `git clone https://github.com/wizarrrr/wizarr.git`
2. Move into the directory `cd wizarr`
3. Start Wizarr with `uv run dev.py`
4. Wizarr is now accessible at http://127.0.0.1:5000

### Running Tests

To run the test suite, ensure your dependencies (including development dependencies) are installed, then invoke pytest via `uv`:

```bash
uv sync --locked
uv run pytest
```
