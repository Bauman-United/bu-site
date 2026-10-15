import threading

from bu_worker.schedule import single_flight


def test_single_flight_skips_overlapping_runs():
    started, release = threading.Event(), threading.Event()
    calls = []

    @single_flight
    def job():
        calls.append(1)
        started.set()
        release.wait(2)

    t = threading.Thread(target=job)
    t.start()
    started.wait(2)
    job()  # пока первый запуск идёт — пропускается
    release.set()
    t.join()
    assert len(calls) == 1
