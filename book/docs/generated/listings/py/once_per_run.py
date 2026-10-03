# tests/conftest.py, lines 111-125
def once_per_run(tmp_path_factory, needed, make):
    """make() if needed(), once per run of the suite however many processes run it.

    Under pytest-xdist every worker is a process of its own with a session of its own, and
    would make the same thing again, over files the others are reading.  The workers take a
    lock in the directory they all share and ask needed() while they hold it, so the first
    one makes and the others find it made.  Without xdist it is the plain call."""
    if not os.environ.get('PYTEST_XDIST_WORKER'):
        if needed():
            make()
        return
    with open(tmp_path_factory.getbasetemp().parent / 'wof-once.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if needed():
            make()
