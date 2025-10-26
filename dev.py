import argparse
import subprocess
import sys
from pathlib import Path


def check_node_installation():
    print("Checking Node.js and npm installation...")
    try:
        node_version = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, check=True
        ).stdout.strip()
        print(f"✓ Node.js {node_version} is installed")

        npm_version = subprocess.run(
            ["npm", "--version"], capture_output=True, text=True, check=True
        ).stdout.strip()
        print(f"✓ npm {npm_version} is installed")
    except subprocess.CalledProcessError:
        print("❌ Node.js and/or npm is not installed!")
        print("Please install Node.js and npm before running this script.")
        print("You can download them from: https://nodejs.org/")
        sys.exit(1)


def check_uv_installation():
    print("Checking uv installation...")
    try:
        uv_version = subprocess.run(
            ["uv", "--version"], capture_output=True, text=True, check=True
        ).stdout.strip()
        print(f"✓ uv {uv_version} is installed")
    except subprocess.CalledProcessError:
        print("❌ uv is not installed!")
        print("Please install uv before running this script.")
        print(
            "You can download it from: https://docs.astral.sh/uv/getting-started/installation/"
        )
        sys.exit(1)


def run_command(command, cwd=None, env=None):
    print(f"Running: {' '.join(command)}")
    try:
        process = subprocess.Popen(command, cwd=cwd, env=env)
        process.wait()
        if process.returncode != 0:
            print(f"Error running command: {' '.join(command)}")
            print(f"Error code: {process.returncode}")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nReceived interrupt signal. Shutting down...")
        process.terminate()
        process.wait()
        sys.exit(0)
    except Exception as e:
        print(f"Error running command: {' '.join(command)}")
        print(f"Error: {e}")
        sys.exit(1)


def main():
    import os

    parser = argparse.ArgumentParser(
        description="Wizarr development server",
        epilog="""
Examples:
  python dev.py                    # Start development server (default)
  python dev.py --scheduler        # Start with background scheduler enabled
  python dev.py --plus             # Start with Plus features enabled
  python dev.py --plus --scheduler # Start with both Plus and scheduler enabled

The scheduler runs maintenance tasks like:
  - Expiry cleanup (every 1 minute in dev mode)
  - User account deletion for expired users
  - Server-specific expiry enforcement

Plus features include:
  - Audit logging for admin actions
  - Advanced analytics and reporting
  - Enhanced security features
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scheduler",
        action="store_true",
        help="Enable the background scheduler for testing expiry and maintenance tasks",
    )
    parser.add_argument(
        "--plus",
        action="store_true",
        help="Enable Plus features including audit logging and advanced analytics",
    )
    args = parser.parse_args()

    check_node_installation()
    check_uv_installation()

    project_root = Path(__file__).parent
    static_dir = project_root / "app" / "static"

    # Create dev environment with NODE_ENV=development to ensure devDependencies are installed
    npm_env = os.environ.copy()
    npm_env["NODE_ENV"] = "development"

    print("Compiling translations...")
    run_command(["uv", "run", "pybabel", "compile", "-d", "app/translations", "-f"])

    print("Running database setup...")

    print("Applying alembic migrations...")
    run_command(["uv", "run", "flask", "db", "upgrade"])

    print("Installing/updating npm dependencies...")
    run_command(["npm", "install"], cwd=static_dir, env=npm_env)

    print("Building static assets (CSS & JS)...")
    run_command(["npm", "run", "build"], cwd=static_dir, env=npm_env)

    # Start the Tailwind watcher in the background
    print("Starting Tailwind watcher...")
    tailwind_process = subprocess.Popen(
        ["npm", "run", "watch:css"], cwd=static_dir, env=npm_env
    )

    try:
        flask_command = ["uv", "run", "flask", "run", "--debug"]

        # Set environment variables based on flags
        if args.scheduler:
            print(
                "🕒 Scheduler enabled - background tasks will run (expiry cleanup every 1 minute)"
            )
            os.environ["WIZARR_ENABLE_SCHEDULER"] = "true"
        else:
            print(
                "ℹ️  Scheduler disabled - use --scheduler flag to enable background tasks"
            )

        if args.plus:
            print(
                "⭐ Plus features enabled - audit logging and advanced features available"
            )
            os.environ["WIZARR_PLUS_ENABLED"] = "true"
        else:
            print(
                "ℹ️  Plus features disabled - use --plus flag to enable audit logging and advanced features"
            )

        print("Starting Flask development server...")
        run_command(flask_command)
    finally:
        # Ensure we clean up the Tailwind process when Flask exits
        tailwind_process.terminate()
        tailwind_process.wait()


if __name__ == "__main__":
    main()
