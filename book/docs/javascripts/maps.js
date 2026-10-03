/* The map viewer (maps.md): each of the game's fifteen maps as one strip, from the data
 * book/tools/elements.py made into generated/maps/.  index.json lists the maps; <map>.json
 * holds a map's records, ships, airfields and slots and the boxes of its drawn shapes, and its
 * picture comes in bands, <map>-<n>.png, laid side by side.  Every place on the strip is a
 * world x times the scale, through the CSS variable --z, so that a change of scale changes
 * that variable and nothing else.  Nothing is loaded from elsewhere. */
(function () {
  'use strict';

  var root = document.querySelector('.wof-maps');
  if (!root || !document.currentScript) return;
  var base = new URL('../generated/maps/', document.currentScript.src);

  var LOW = ['open sea', "a ship's deck", 'land', 'low bits 3'];
  var GROUPS = [['draw', [15]], ['14', [14]], ['height', [13, 12, 11]],
                ['slot', [10, 9, 8, 7, 6, 5, 4, 3, 2]], ['low', [1, 0]]];
  var LABEL_EVERY = 960;                // world x labelled every three screens' width
  var ISLAND_FLAG = 0x113;
  var CARRIER = "the player's carrier";

  function el(tag, className, text) {
    var e = document.createElement(tag);
    if (className) e.className = className;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function number(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function hex(n, digits) {
    var s = n.toString(16).toUpperCase();
    while (s.length < digits) s = '0' + s;
    return '0x' + s;
  }

  // An element placed on the strip at world x, w world pixels wide.
  function at(className, x, w, text) {
    var e = el('div', 'wof-at ' + className, text);
    e.style.setProperty('--x', x);
    e.style.setProperty('--w', w === undefined ? 8 : w);
    return e;
  }

  var index = null, map = null, slots = {}, boxes = {}, zoom = 1, pinned = null;
  var choose = el('select'), records = el('input'), start = el('button', 'wof-button',
    "The player's start");
  var scales = [1, 2].map(function (z) {
    var b = el('button', 'wof-button', z + 'x');
    b.type = 'button';
    b.setAttribute('aria-pressed', String(z === zoom));
    b.addEventListener('click', function () { scale(z); });
    return b;
  });
  var summary = el('p', 'wof-summary'), strip = el('div', 'wof-strip'), world = el('div', 'wof-world');
  var picture = el('div', 'wof-picture'), ruler = el('div', 'wof-ruler');
  var column = at('wof-column', 0), box = at('wof-box', 0);
  var inspector = el('div', 'wof-inspector');

  function fail(what) {
    root.textContent = '';
    root.appendChild(el('p', 'wof-failed', 'The map viewer could not load its data (' + what +
      '). It needs the site served, by mkdocs serve or from the published site, not opened as a file.'));
  }

  function fetchJSON(file) {
    return fetch(new URL(file, base)).then(function (response) {
      if (!response.ok) throw new Error(file + ': ' + response.status);
      return response.json();
    });
  }

  function list(words) {
    if (words.length < 2) return words.join('');
    return words.slice(0, -1).join(', ') + ' and ' + words[words.length - 1];
  }

  function describe(entry) {
    var ships = entry.enemy_ships.length ? list(entry.enemy_ships.map(function (s) {
      return (/^[AEIOU]/i.test(s) ? 'an ' : 'a ') + s;
    })) : 'no enemy ship';
    return 'Map ' + entry.map + ': ' + number(entry.records) + ' records, ' +
      number(entry.extent) + ' pixels wide, ' + number(entry.drawn) + ' with the draw flag; ' +
      entry.islands + (entry.islands === 1 ? ' island; ' : ' islands; ') + ships + '; ' +
      (entry.airfields ? entry.airfields + (entry.airfields === 1 ? ' airfield' : ' airfields')
       : 'no airfield') + '. The player starts at world x ' + number(entry.player_x) + '.';
  }

  // ------------------------------------------------------------------ the strip

  function build() {
    world.style.setProperty('--extent', map.extent);
    world.style.setProperty('--rows', map.rows);
    picture.textContent = '';
    map.bands.forEach(function (band) {
      var img = el('img');
      img.src = new URL(band.file, base);
      img.alt = band.x ? '' : 'Map ' + map.map + ' at full scale';
      img.width = band.width;
      img.height = map.rows;
      img.style.setProperty('--w', band.width);
      picture.appendChild(img);
    });

    ruler.textContent = '';
    var under = el('div', 'wof-under'), ticks = el('div', 'wof-ticks');
    var spans = el('div', 'wof-spans'), points = el('div', 'wof-points');
    var run = 0;
    map.records.forEach(function (r, i) {
      var next = map.records[i + 1];
      if (!next || next[7] !== r[7]) {
        under.appendChild(at('wof-low' + r[7], 8 * run, 8 * (i + 1 - run)));
        run = i + 1;
      }
      if (r[3]) ticks.appendChild(at('wof-mark', r[1]));
      if (r[6] === ISLAND_FLAG) points.appendChild(at('wof-point wof-flag', r[1], 8, 'flag'));
    });
    map.ships.forEach(function (s) {
      spans.appendChild(at('wof-span ' + (s.ship === CARRIER ? 'wof-carrier' : 'wof-ship'),
                           8 * s.west, 8 * (s.east - s.west + 1), s.ship));
    });
    map.airfields.forEach(function (a) {
      spans.appendChild(at('wof-span wof-airfield', 8 * a.first, 8 * (a.second - a.first + 1),
                           'airfield'));
    });
    for (var x = LABEL_EVERY; x < map.extent; x += LABEL_EVERY)
      points.appendChild(at('wof-point wof-x', x, 1, number(x)));
    points.appendChild(at('wof-point wof-start', map.player_x, 8, 'start'));
    [under, ticks, spans, points].forEach(function (e) { ruler.appendChild(e); });

    slots = {};
    map.slots.forEach(function (s) { slots[s.slot] = s; });
    boxes = {};
    map.draws.forEach(function (d) { boxes[d[0]] = d; });
    pinned = null;
    inspect(null);
  }

  function scale(z) {
    var middle = (strip.scrollLeft + strip.clientWidth / 2) / zoom;
    zoom = z;
    world.style.setProperty('--z', z);
    scales.forEach(function (b, i) { b.setAttribute('aria-pressed', String(i + 1 === z)); });
    strip.scrollLeft = middle * zoom - strip.clientWidth / 2;
  }

  function reveal(x) {
    var left = x * zoom, right = (x + 8) * zoom;
    if (left < strip.scrollLeft || right > strip.scrollLeft + strip.clientWidth)
      strip.scrollLeft = left - strip.clientWidth / 2;
  }

  // The drawn shape a record belongs to: its own when it carries the draw flag, otherwise the
  // drawn record of the same slot whose shape covers the record's eight pixels.
  function shapeOf(i) {
    var r = map.records[i];
    if (boxes[i]) return boxes[i];
    if (!r[2]) return null;
    for (var k = 0; k < map.draws.length; k++) {
      var d = map.draws[k];
      if (map.records[d[0]][6] === r[6] && d[1] < r[1] + 8 && d[1] + d[3] > r[1]) return d;
    }
    return null;
  }

  function within(list, first, last, i) {
    for (var k = 0; k < list.length; k++)
      if (i >= list[k][first] && i <= list[k][last]) return list[k];
    return null;
  }

  // ------------------------------------------------------------------ the inspector

  function fact(table, label, value) {
    var row = el('tr');
    row.appendChild(el('th', null, label));
    row.appendChild(el('td', null, value));
    table.appendChild(row);
  }

  function slotText(slot) {
    var s = slots[slot], head = slot + ', ' + hex(slot, 3) + ': ';
    if (s.marker) return head + 'past the lists, so the table holds null; ' + s.marker;
    if (!s.name) return head + 'past the lists, so the table holds null';
    var name = s.name.replace(/\s+$/, '');
    return head + name + ' of ' + s.list + (s.shape ? ', a shape of ' + s.shape
      : ', a name its container lacks, so the table holds null');
  }

  function inspect(i) {
    inspector.textContent = '';
    column.hidden = box.hidden = i === null;
    if (i === null) {
      inspector.appendChild(el('p', 'wof-panel-hint',
        'Point at a column of the strip to read its record; click to hold it, and the arrow ' +
        'keys move along.'));
      return;
    }
    var r = map.records[i], word = r[2], low = r[7], height = r[5];
    column.style.setProperty('--x', r[1]);
    var drawn = shapeOf(i);
    box.hidden = !drawn;
    if (drawn) {
      box.style.setProperty('--x', drawn[1]);
      box.style.setProperty('--w', drawn[3]);
      box.style.setProperty('--top', drawn[2]);
      box.style.setProperty('--h', drawn[4]);
    }

    inspector.appendChild(el('p', 'wof-panel-title', 'Record ' + number(i)));
    inspector.appendChild(el('p', 'wof-panel-sub', 'world x ' + number(r[1]) + ' to ' +
      number(r[1] + 7) + ', the word ' + hex(word, 4) + (pinned === i ? ', held' : '')));

    var bits = el('div', 'wof-bits');
    GROUPS.forEach(function (group) {
      var g = el('div', 'wof-group'), row = el('div', 'wof-group-bits'), value = 0;
      g.appendChild(el('span', 'wof-group-name', group[0]));
      group[1].forEach(function (b) {
        var on = (word >> b) & 1;
        value = value * 2 + on;
        var cell = el('span', 'wof-bit' + (on ? ' wof-on' : '') + (b === 15 ? ' wof-flagbit' : ''),
                      String(on));
        cell.title = 'bit ' + b;
        row.appendChild(cell);
      });
      g.appendChild(row);
      g.appendChild(el('span', 'wof-group-value', String(value)));
      bits.appendChild(g);
    });
    inspector.appendChild(bits);

    var table = el('table', 'wof-facts');
    fact(table, 'Draw flag, bit 15', r[3] ? 'set: the record draws its shape'
         : 'clear: the record draws nothing itself');
    fact(table, 'Bit 14', r[4] ? 'set' : 'clear, as in every record of the fifteen maps');
    fact(table, 'Height field, bits 13 to 11', height ? height + ': ' + 4 * height +
         ' rows below the horizon\'s row, on row ' + (map.split_row + 4 * height)
         : '0: on the horizon\'s row, row ' + map.split_row);
    fact(table, 'Slot, bits 10 to 2', slotText(r[6]));
    fact(table, 'Low bits, 1 and 0', low + ': ' + LOW[low]);
    if (r[3] && !boxes[i]) fact(table, 'Shape', 'none: a null slot draws nothing');
    if (drawn) fact(table, r[3] ? 'Shape' : 'Its shape', map.records[drawn[0]][8].replace(/\s+$/, '') +
         (r[3] ? '' : ', drawn by record ' + number(drawn[0])) + ', over world x ' +
         number(drawn[1]) + ' to ' + number(drawn[1] + drawn[3] - 1) + ' and rows ' + drawn[2] +
         ' to ' + (drawn[2] + drawn[4] - 1));
    var ship = within(map.ships, 'west', 'east', i);
    if (ship) fact(table, 'Ship', ship.ship + ', records ' + number(ship.west) + ' to ' +
                   number(ship.east) + ' from marker to marker');
    var field = within(map.airfields, 'first', 'second', i);
    if (field) fact(table, 'Airfield', 'records ' + number(field.first) + ' to ' +
                    number(field.second) + ' from marker to marker');
    inspector.appendChild(table);
  }

  function recordAt(event) {
    var x = event.clientX - world.getBoundingClientRect().left;
    var i = Math.floor(x / (8 * zoom));
    return i >= 0 && i < map.records.length ? i : null;
  }

  // ------------------------------------------------------------------ the page

  function open(name) {
    var entry = index.maps.filter(function (m) { return m.map === name; })[0];
    summary.textContent = describe(entry);
    return fetchJSON(name + '.json').then(function (data) {
      map = data;
      build();
      strip.scrollLeft = 0;
    }).catch(function (error) { fail(error.message); });
  }

  function legend() {
    var l = el('div', 'wof-legend');
    [['wof-low2', 'land'], ['wof-low1', "a ship's deck"], ['wof-low0', 'open sea'],
     ['wof-mark', 'the draw flag'], ['wof-ship', 'a ship'], ['wof-airfield', 'an airfield']
    ].forEach(function (item) {
      var e = el('span', 'wof-key');
      e.appendChild(el('span', 'wof-swatch ' + item[0]));
      e.appendChild(document.createTextNode(item[1]));
      l.appendChild(e);
    });
    return l;
  }

  function begin(data) {
    index = data;
    data.maps.forEach(function (m) {
      var option = el('option', null, 'Map ' + m.map + ', ' + number(m.records) + ' records');
      option.value = m.map;
      choose.appendChild(option);
    });
    choose.setAttribute('aria-label', 'The map');
    records.type = 'checkbox';
    records.checked = true;
    start.type = 'button';
    var toggle = el('label', 'wof-toggle');
    toggle.appendChild(records);
    toggle.appendChild(document.createTextNode(' Records'));

    var controls = el('div', 'wof-controls');
    controls.appendChild(choose);
    scales.forEach(function (b) { controls.appendChild(b); });
    controls.appendChild(toggle);
    controls.appendChild(start);

    world.appendChild(picture);
    world.appendChild(ruler);
    world.appendChild(column);
    world.appendChild(box);
    world.style.setProperty('--z', zoom);
    strip.appendChild(world);
    strip.tabIndex = 0;
    strip.setAttribute('aria-label', 'The map strip; the arrow keys move from record to record');
    inspector.setAttribute('aria-live', 'polite');

    root.textContent = '';
    [controls, summary, strip, legend(), inspector].forEach(function (e) { root.appendChild(e); });

    choose.addEventListener('change', function () { open(choose.value); });
    records.addEventListener('change', function () {
      root.classList.toggle('wof-bare', !records.checked);
    });
    start.addEventListener('click', function () {
      pinned = Math.floor(map.player_x / 8);
      strip.scrollLeft = map.player_x * zoom - strip.clientWidth / 2;
      inspect(pinned);
    });
    world.addEventListener('pointermove', function (event) {
      if (event.pointerType !== 'mouse' || pinned !== null || !map) return;
      inspect(recordAt(event));
    });
    world.addEventListener('click', function (event) {
      if (!map) return;
      var i = recordAt(event);
      pinned = i === pinned ? null : i;
      inspect(i);
    });
    strip.addEventListener('keydown', function (event) {
      var step = { ArrowLeft: -1, ArrowRight: 1 }[event.key];
      if (!step || !map) return;
      event.preventDefault();
      var from = pinned !== null ? pinned : Math.floor(strip.scrollLeft / (8 * zoom));
      pinned = Math.max(0, Math.min(map.records.length - 1, from + step));
      reveal(8 * pinned);
      inspect(pinned);
    });
    open(data.maps[0].map);
  }

  fetchJSON('index.json').then(begin).catch(function (error) { fail(error.message); });
})();
