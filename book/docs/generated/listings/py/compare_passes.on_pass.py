# tests/test_world.py, lines 85-113
    def on_pass(r, memory, head, k):
        if stopping(r):
            return
        d = r.state_differences(memory)
        if d:
            found.add('state', k, d[:8])
        oc, pc = r.original_calls(memory, k), r.port_calls()
        if oc != pc:
            n = next((i for i, (a, b) in enumerate(zip(oc, pc)) if a != b), min(len(oc), len(pc)))
            found.add('calls', k, ('original', oc[n:n + 3], 'port', pc[n:n + 3]))
        oe, pe = r.original_entropy(k), r.port_entropy()
        if oe != pe:
            found.add('entropy', k, ('original', oe[:4], 'port', pe[:4]))
        view = r.view_difference(memory)
        if view:
            found.add('view', k, view)
        rows = r.row_differences(memory)
        if rows:
            found.add('rows', k, rows[:2])
        om, pm = r.predicted_map_draws(memory, chart(memory) if callable(chart) else chart), \
            r.port_map_draws()
        if om != pm:
            found.add('map', k, ('decoder', om[:3], 'port', pm[:3]))
        sound = r.sound_differences(head)
        if sound:
            found.add('sound', k, sound)
        paula = r.paula_differences(memory)
        if paula:
            found.add('paula', k, paula[:4])
