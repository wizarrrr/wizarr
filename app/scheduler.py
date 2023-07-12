from datetime import datetime
from logging import info

from flask_apscheduler import APScheduler

from app import Sessions, Users, app
from app.universal import global_delete_user, global_get_users

# Scheduler
schedule = APScheduler()
schedule.init_app(app)
schedule.start()

# Scheduled tasks
@schedule.task('interval', id='checkExpiringUsers', minutes=15, misfire_grace_time=900)
def check_expiring_users():
    info('Checking for expiring users...')
    # Get all users that have an expiration date set and are expired
    expiring = Users.select().where(Users.expires < datetime.now().strftime("%Y-%m-%d %H:%M"))
    
    # Delete all expired users
    for user in expiring:
        global_delete_user(user)
        info(f"Deleting user { user.email if user.email else user.username } due to expired invite.")
        
@schedule.task('interval', id='scanUsers', minutes=30, misfire_grace_time=900)
def scan_users():
    info('Scanning for new users...')
    # Get all new users
    global_get_users()
    
@schedule.task('interval', id='scanLibraries', minutes=1.53, misfire_grace_time=900)
def scan_libraries():
    info('Scanning for new libraries...')
    # Get all new libraries
    
@schedule.task('interval', id='checkExpiringSessions', minutes=30, misfire_grace_time=900)
def check_expiring_sessions():
    info('Clearing old sessions...')
    
    # Get all sessions that are expired
    expired = Sessions.select().where(Sessions.expires < datetime.now().strftime("%Y-%m-%d %H:%M"))
    
    # Delete all expired sessions
    for session in expired:
        session.delete_instance()
        info(f"Deleting { session.key } due to expired session.")
        


def get_schedule():
    job_store = schedule.get_jobs()
    
    schedule_list = []
    
    for job in job_store:
        # Replace underscores with spaces and capitalize first letter of each word
        name = job.name.replace("_", " ").title()
        
        schedule_info = {
            'id': job.id,
            'name': name,
            'trigger': str(job.trigger),
            'next_run_time': str(job.next_run_time)
        }
        
        schedule_list.append(schedule_info)
    
    return schedule_list
