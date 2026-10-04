# tests/conftest.py, lines 1359-1373
@pytest.fixture(autouse=True)
def fresh_core(request):
    """Every test that takes the core starts from a fresh one, whatever ran before it in its
    process.  A process holds one copy of the core's statics, which `ported` and NativeCore
    share, and a test that leaves them changed - a mission's setup left behind, the shapes
    mirrored, a file deleted - would hand that to whichever test its process runs next,
    which under pytest-xdist is another one each run (re/notes/testing.md).  So a test that
    takes `ported`, itself or through a fixture built on it, gets reset_core and the
    settings back before it runs; a test that makes its own NativeCore gets the settings,
    and NativeCore makes its state itself.  A test without the core pays nothing."""
    names = request.fixturenames
    if 'ported' in names or 'native_core_factory' in names:
        fresh_settings()
    if 'ported' in names:
        request.getfixturevalue('ported').reset_core()
