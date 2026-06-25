import os
import time
import requests
import datetime as dt
from typing import List

from shared.logging import setup_logging, get_logger
from shared.settings import settings

setup_logging("updater")
log = get_logger("updater")

settings.validate_required()

TZ = settings.tz
REFRESH_URL = os.getenv("REFRESH_URL", "http://ingestor:8081/ingest/refresh")
HEALTH_URL = os.getenv("HEALTH_URL", "http://ingestor:8081/health")
MONTHLY_DAYS: List[int] = [
    int(x) for x in settings.monthly_days.split(",") if x.strip()
] or [1, 16]
DAILY_REFRESH_AT = settings.daily_refresh_at.strip()

try:
    import pytz
    _tz = pytz.timezone(TZ)
    def now() -> dt.datetime:
        return dt.datetime.now(_tz)
except Exception:
    _tz = None
    def now() -> dt.datetime:
        return dt.datetime.now()


def wait_service_up(url: str, max_wait: int = 600) -> bool:
    t0 = time.time()
    delay = 1.0
    while True:
        try:
            r = requests.get(url, timeout=5)
            if 200 <= r.status_code < 500:
                log.info("service_ready", url=url, status=r.status_code)
                return True
        except Exception as e:
            log.warning("waiting_for_service", url=url, error=e.__class__.__name__)
        if time.time() - t0 > max_wait:
            log.warning("service_not_ready_timeout", url=url, max_wait=max_wait)
            return False
        time.sleep(delay)
        delay = min(delay * 1.5, 10.0)


def enqueue() -> None:
    tries, delay = 6, 2.0
    for i in range(1, tries + 1):
        try:
            r = requests.post(REFRESH_URL, timeout=30)
            log.info("refresh_enqueued", status=r.status_code, detail=r.text[:200])
            return
        except Exception as e:
            log.error("refresh_failed", try_num=i, max_tries=tries, error=str(e))
            if i < tries:
                time.sleep(delay)
                delay = min(delay * 1.5, 20.0)


def seconds_until_day_time(day: int, hhmm: str) -> tuple[float, dt.datetime]:
    import calendar
    hh, mm = map(int, hhmm.split(":"))
    n = now()
    y, m = n.year, n.month
    last = calendar.monthrange(y, m)[1]
    d = min(day, last)
    target = n.replace(year=y, month=m, day=d, hour=hh, minute=mm, second=0, microsecond=0)
    if target <= n:
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
        last = calendar.monthrange(y, m)[1]
        d = min(day, last)
        target = target.replace(year=y, month=m, day=d)
    return (target - n).total_seconds(), target


def run_monthly(days: List[int], hhmm: str) -> None:
    days = sorted(set(days))
    log.info("monthly_mode_started", days=days, time=hhmm, tz=TZ)
    while True:
        waits = [seconds_until_day_time(d, hhmm) for d in days]
        wait_s, target = min(waits, key=lambda x: x[0])
        wait_s = max(1.0, float(wait_s))
        log.info("sleeping_until_next_refresh", seconds=int(wait_s), target=target.isoformat())
        time.sleep(wait_s)
        enqueue()


if __name__ == "__main__":
    wait_service_up(HEALTH_URL)
    log.info("initial_refresh_at_startup")
    enqueue()
    run_monthly(MONTHLY_DAYS, DAILY_REFRESH_AT)
