from os import path, getenv

ROOT_DIR = getenv("ROOT_DIR", path.abspath(path.join(path.abspath(__file__), "../")))
LATEST_FILE = getenv("LATEST_FILE", path.join(ROOT_DIR, "../", "../", "../", "latest"))
DATABASE_DIR = getenv("DATABASE_DIR", path.join(ROOT_DIR, "../", "database"))
MAX_CONTENT_LENGTH = getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024) # 5MB
