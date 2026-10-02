# tests/test_oracle_m4.py, lines 649-667
# The routines that take no argument and whose whole effect is on the registered state,
# with the state each wants: in the air, on the deck, or any.
PLAYER_ROUTINES = [
    (0x01BFF4, 'the stick in the air', 0),
    (0x01C4E8, 'the stick on the deck', 1),
    (0x01AA6E, 'whether the aircraft may turn', None),
    (0x01AAEA, 'the wheels below the reference point', None),
    (0x01B45A, 'the hook', None),
    (0x01B4DE, 'on the lift', 1),
    (0x01B5B0, 'the button', None),
    (0x01B8C4, 'touching the ground', 0),
    (0x01B92E, 'the cables', 1),
    (0x01BC02, "the enemy's countdown", None),
    (0x01BCCE, 'the deck state', None),
    (0x01BDBA, 'the roll on the deck', None),
    (0x01C5F4, 'the ends of the deck', 1),
    (0x01AFBA, 'the aircraft down: in the sea, on land, on a ship', 4),
    (0x01BA80, 'the ground: a landing, a bounce, a crash', 0),
]
