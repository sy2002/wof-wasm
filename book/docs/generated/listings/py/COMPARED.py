# tests/m4complete.py, lines 25-35
# (first, last, writers, what it is, how the port carries it)
COMPARED = [
    (0x026E1C, 0x026E3B, {'view_show'},
     'back_rastport, back_vport, front_rastport, front_vport, back_view, front_view, '
     'back_bitmap, front_bitmap: the double buffer',
     'the index of the view in front, compared after every pass (V1, the view check)'),
    (0x027A18, 0x027BD7, {'cmap_file_to_table', 'iff_cmap_to_table', 'mission_display_setup',
                          'view_poke_colours1', 'view_poke_colours2', 'vport_init_bitmap'},
     'coltab_a1 ... coltab_b1_split: the colour tables of both views and the ticker',
     "each viewport's colour tables, compared as the palette of every output row (V1 rows)"),
]
