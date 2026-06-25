# services/updater/app.py
import os
import time
import requests
import datetime as dt
from typing import List

# =======================
# Config từ .env
# =======================
TZ = os.getenv("TZ", "Asia/Ho_Chi_Minh")

# endpoint để gọi refresh và health của ingestor
REFRESH_URL = os.getenv("REFRESH_URL", "http://ingestor:8081/ingest/refresh")
HEALTH_URL  = os.getenv("HEALTH_URL",  "http://ingestor:8081/health")

# lịch cố định: ngày trong tháng và giờ chạy
MONTHLY_DAYS_ENV = os.getenv("MONTHLY_DAYS", "1,16")
MONTHLY_DAYS: List[int] = [
    int(x) for x in MONTHLY_DAYS_ENV.split(",") if x.strip()
] or [1, 16]
DAILY_REFRESH_AT = os.getenv("DAILY_REFRESH_AT", "03:30").strip()  # HH:MM

# =======================
# Giờ theo múi TZ (fallback nếu thiếu pytz)
# =======================
try:
    import pytz  # type: ignore
    _tz = pytz.timezone(TZ)

    def now() -> dt.datetime:
        return dt.datetime.now(_tz)  # timezone-aware
except Exception:
    _tz = None

    def now() -> dt.datetime:
        return dt.datetime.now()     # naïve datetime (fallback)


# =======================
# Tiện ích
# =======================
def wait_service_up(url: str, max_wait: int = 600) -> bool:
    """
    Đợi service sẵn sàng (tối đa max_wait giây).
    Trả về True nếu OK, False nếu hết thời gian vẫn chưa sẵn sàng.
    """
    t0 = time.time()
    delay = 1.0
    while True:
        try:
            r = requests.get(url, timeout=5)
            # /health trả 200 là tốt nhất; 404 vẫn coi là socket đã mở
            if 200 <= r.status_code < 500:
                print(f"[updater] service ready: {url} -> {r.status_code}")
                return True
        except Exception as e:
            print(f"[updater] waiting for service {url} ({e.__class__.__name__})")

        if time.time() - t0 > max_wait:
            print(f"[updater] service not ready after {max_wait}s, continue anyway")
            return False

        time.sleep(delay)
        delay = min(delay * 1.5, 10.0)  # exponential backoff tới 10s


def enqueue() -> None:
    """Gọi ingestor để refresh; có retry/backoff."""
    tries, delay = 6, 2.0
    for i in range(1, tries + 1):
        try:
            r = requests.post(REFRESH_URL, timeout=30)
            print(f"[updater] Enqueued refresh -> {r.status_code} {r.text[:200]!r}")
            return
        except Exception as e:
            print(f"[updater] Updater error (try {i}/{tries}): {e}")
            if i < tries:
                time.sleep(delay)
                delay = min(delay * 1.5, 20.0)


def seconds_until_day_time(day: int, hhmm: str) -> tuple[float, dt.datetime]:
    """
    Tính số giây còn lại tới mốc 'ngày {day} lúc {hhmm}' theo TZ,
    tự động chuyển sang tháng sau nếu mốc của tháng này đã qua.
    """
    hh, mm = map(int, hhmm.split(":"))
    n = now()
    y, m = n.year, n.month

    import calendar
    last = calendar.monthrange(y, m)[1]
    d = min(day, last)

    target = n.replace(
        year=y, month=m, day=d, hour=hh, minute=mm, second=0, microsecond=0
    )

    if target <= n:
        # sang tháng sau
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
        last = calendar.monthrange(y, m)[1]
        d = min(day, last)
        target = target.replace(year=y, month=m, day=d)

    return (target - n).total_seconds(), target


def run_monthly(days: List[int], hhmm: str) -> None:
    """Vòng lặp lịch cố định theo ngày trong tháng tại giờ hh:mm."""
    days = sorted(set(days))
    print(f"[updater] monthly mode: days={days} at {hhmm} ({TZ})")
    while True:
        waits = [seconds_until_day_time(d, hhmm) for d in days]
        wait_s, target = min(waits, key=lambda x: x[0])
        wait_s = max(1.0, float(wait_s))
        print(f"[updater] sleeping {int(wait_s)}s until {target.isoformat()} ({TZ})")
        time.sleep(wait_s)
        enqueue()


# =======================
# Main
# =======================
if __name__ == "__main__":
    # 1) Đợi ingestor sẵn sàng
    wait_service_up(HEALTH_URL)

    # 2) Chạy ngay 1 lần khi container start
    print("[updater] run-once at startup")
    enqueue()

    # 3) Sau đó chạy theo lịch cố định: ngày 1 & 16 lúc DAILY_REFRESH_AT
    run_monthly(MONTHLY_DAYS, DAILY_REFRESH_AT)

