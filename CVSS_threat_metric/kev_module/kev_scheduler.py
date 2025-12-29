import schedule
import time
from kev_client import update_db_from_kev
from kev_db import init_db

def job():
    print("[KEV] Updating database...")
    update_db_from_kev(force=True)
    print("[KEV] Done")

def run_scheduler():
    init_db()
    schedule.every(6).hours.do(job)

    job()  # run ngay khi start

    while True:
        schedule.run_pending()
        time.sleep(60)
