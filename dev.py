import subprocess
import sys
from pathlib import Path

def check_node_installation():
    print("Checking Node.js and npm installation...")
    try:
        node_version = subprocess.run(
            "node --version",
            shell=True,
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        print(f"✓ Node.js {node_version} is installed")

        npm_version = subprocess.run(
            "npm --version",
            shell=True,
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        print(f"✓ npm {npm_version} is installed")
    except subprocess.CalledProcessError:
        print("❌ Node.js and/or npm is not installed!")
        print("Please install Node.js and npm before running this script.")
        print("You can download them from: https://nodejs.org/")
        sys.exit(1)

def run_command(command, cwd=None):
    print(f"Running: {command}")
    try:
        subprocess.run(command, shell=True, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e}")
        sys.exit(1)

def main():
    check_node_installation()

    project_root = Path(__file__).parent
    static_dir = project_root / "app" / "static"

    print("Compiling translations...")
    run_command("uv run pybabel compile -d app/translations")

    print("Running database setup...")
    print("1. Renaming legacy database...")
    run_command("uv run python -m app.legacy_migration.rename_legacy")
    
    print("2. Applying alembic migrations...")
    run_command("uv run flask db upgrade")
    
    print("3. Importing legacy data...")
    run_command("uv run python -m app.legacy_migration.import_legacy")

    print("Installing/updating npm dependencies...")
    run_command("npm install", cwd=static_dir)

    # Start the Tailwind watcher in the background
    print("Starting Tailwind watcher...")
    tailwind_process = subprocess.Popen(
        "./watch-tailwind.sh",
        cwd=static_dir,
        shell=True
    )

    try:
        print("Starting Flask development server...")
        run_command(f"uv run flask run --debug")
    finally:
        # Ensure we clean up the Tailwind process when Flask exits
        tailwind_process.terminate()
        tailwind_process.wait()

if __name__ == "__main__":
    main()
