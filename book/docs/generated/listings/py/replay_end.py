# tests/m4compare.py, lines 528-546, a part of Replay._run (lines 401-557)
vblank = 0
last_pass = max((h for h in self.machine.step_hashes if h[0] == 'P'),
                key=lambda h: h[2], default=(None, 0, 0, None))[2]
# The last pass's ticks come after its end (run_queued_ticks follows frame_update):
# the replay goes on until the port has run them too.
last_tick = max((h[1] for h in self.machine.step_hashes if h[0] == 'T'), default=0)
try:
    for entry in self.machine.schedule:
        if entry[0] != 'V':
            continue
        vblank += 1
        for code, qualifier in keys.get(vblank, ()):
            ported.key(code, qualifier)
        ported.vblank(raw(entry[1]) if raw else entry[1])
        ported.pass_()
        if self.errors:
            raise self.errors[0]
        if self.passes >= last_pass and last_pass and self.ticks >= last_tick:
            break
