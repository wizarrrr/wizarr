# Development

If you want to contribute to Wizarr, here is how

### Prerequisites

* Python3.11+

### Development Environment

1. Clone the repository with `git clone git@github.com:Wizarrrr/wizarr.git`
2. Move into the directory `cd wizarr`
3. (Optional but recommended) Create a python virtual environment with `python -m venv venv`
4. Enter the python venv with `source venv/bin/activate`
5. Install dependencies with `pip install -r requirements.txt`
6. Install static dependencies with `cd app/static && npm install && cd ../..`
7. Build static files with `cd app/static && npm run build && cd ../..`
8. Start Wizarr with `APP_URL=127.0.0.1:5000 flask run --debug run`
9. Wizarr is now accessible at http://127.0.0.1:5000
