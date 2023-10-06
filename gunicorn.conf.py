import multiprocessing

# gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5001 --reload run:app
use = "eventlet"
bind = "127.0.0.1:5000"
reload = True
debug = True
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 1