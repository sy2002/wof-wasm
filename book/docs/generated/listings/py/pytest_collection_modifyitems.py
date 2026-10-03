# tests/conftest.py, lines 75-95
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    for item in items:
        group = recording_group(item)
        if group:
            item.add_marker(pytest.mark.xdist_group(group))
    # Without the Kickstart ROM nothing that needs it or the build can run, and the build takes
    # the system font from it: every test but those marked `without_rom` skips, with the one
    # message of tools/rom.py as its reason, as a missing browser skips its module.
    missing = romcheck.problem()
    if missing:
        skip_rom = pytest.mark.skip(reason=missing)
        for item in items:
            if 'without_rom' not in item.keywords:
                item.add_marker(skip_rom)
    if config.getoption('--slow') or os.environ.get('WOF_SLOW') == '1':
        return
    skip = pytest.mark.skip(reason='slow; run with --slow or WOF_SLOW=1')
    for item in items:
        if 'slow' in item.keywords:
            item.add_marker(skip)
