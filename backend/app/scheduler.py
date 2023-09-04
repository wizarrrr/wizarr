from datetime import datetime
from logging import info

from app.extensions import schedule
from app.security import server_verified

schedule.start()
@schedule.task("interval", id="test", minutes=1, misfire_grace_time=900)
def test():
    print("test")

# Scheduled tasks
@schedule.task("interval", id="checkExpiringUsers", minutes=30, misfire_grace_time=900)
def check_expiring_users():
    # Check if the server is verified
    if not server_verified(): return

    # Import the function here to avoid circular imports
    from helpers.universal import global_delete_user
    from helpers.users import get_users_by_expiring

    # Log message to console
    info("Checking for expiring users")

    # Get all users that have an expiration date set and are expired
    expiring = get_users_by_expiring(as_dict=False)

    # Delete all expired users
    for user in expiring:
        global_delete_user(user.token)
        info(f"Deleting user { user.email if user.email else user.username } due to expired invite.")


@schedule.task("interval", id="syncUsers", hours=3, misfire_grace_time=900)
def scan_users():
    # Check if the server is verified
    if not server_verified(): return

    # Import the function here to avoid circular imports
    from helpers.universal import global_sync_users

    info("Scanning for new users")
    global_sync_users()

@schedule.task("interval", id="checkForUpdates", hours=1, misfire_grace_time=900)
def check_for_updates():
    # Import the function here to avoid circular imports
    from app.utils.software_lifecycle import need_update
    from app import app

    info("Checking for updates")

    # Update jinja global variable
    app.jinja_env.globals.update(APP_UPDATE=need_update())



# Ignore these helper functions they need to be moved to a different file
def get_schedule():
    job_store = schedule.get_jobs()

    schedule_list = []

    for job in job_store:
        # Replace underscores with spaces and capitalize first letter of each word
        name = job.name.replace("_", " ").title()

        schedule_info = {
            "id": job.id,
            "name": name,
            "trigger": str(job.trigger),
            "next_run_time": str(job.next_run_time)
        }

        schedule_list.append(schedule_info)

    return schedule_list

def get_task(job_id):
    job_store = schedule.get_job(id=job_id)

    schedule_info = {
        "id": job_store.id,
        "name": job_store.name,
        "trigger": str(job_store.trigger),
        "next_run_time": str(job_store.next_run_time)
    }

    return schedule_info

def run_task(job_id):
    return schedule.modify_job(id=job_id, jobstore=None, next_run_time=datetime.now())
