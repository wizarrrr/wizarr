from datetime import datetime
from logging import info

from flask_apscheduler import APScheduler

from app.extensions import schedule
from helpers.universal import global_sync_users
from helpers.users import get_users_by_expiring
from app.models.database import Sessions

schedule.start()

# Scheduled tasks
@schedule.task("interval", id="checkExpiringUsers", minutes=30, misfire_grace_time=900)
def check_expiring_users():
    # Log message to console
    info("Checking for expiring users")

    # Get all users that have an expiration date set and are expired
    expiring = get_users_by_expiring()

    # Delete all expired users
    for user in expiring:
        # global_delete_user(user)
        info(f"Deleting user { user.email if user.email else user.username } due to expired invite.")


@schedule.task("interval", id="checkExpiredSessions", minutes=15, misfire_grace_time=900)
def check_expired_sessions():
    info("Checking for expired sessions")
    # Get all sessions where expires is less than now in utc and delete them
    sessions = Sessions.select().where(Sessions.expires < datetime.utcnow().strftime("%Y-%m-%d %H:%M"))

    # Delete all expired sessions
    for session in sessions:
        session.delete_instance()
        info(f"Deleting session { session.id } due to expired session.")


@schedule.task("interval", id="syncUsers", hours=3, misfire_grace_time=900)
def scan_users():
    info("Scanning for new users")
    global_sync_users()



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
