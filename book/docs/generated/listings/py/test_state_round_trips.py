# tests/test_core_native.py, lines 47-60
def test_state_round_trips(native_core_factory, blob):
    core = native_core_factory(7, blob)
    core.run(100)
    saved = core.save_state()
    picture = core.framebuffer()

    core.run(60)
    straight = core.save_state()
    assert straight != saved

    core.load_state(saved)
    assert core.framebuffer() == picture
    core.run(60)
    assert core.save_state() == straight
