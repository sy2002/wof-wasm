/* The shape browser (browser.md): every shape of the game's twelve containers, from the data
 * book/tools/elements.py made into generated/browser/.  index.json lists the containers,
 * <name>.json gives a container's shapes with their headers' fields and their places in its
 * sheet, <name>.png.  A shape is shown as its part of the sheet: the sheet as a background,
 * sized and placed in percent so that the crop scales with its box, enlarged without
 * smoothing.  Nothing is loaded from elsewhere. */
(function () {
  'use strict';

  var root = document.querySelector('.wof-browser');
  if (!root || !document.currentScript) return;
  var base = new URL('../generated/browser/', document.currentScript.src);

  function el(tag, className, text) {
    var e = document.createElement(tag);
    if (className) e.className = className;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function number(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function hex(n) {
    return '0x' + (n < 16 ? '0' : '') + n.toString(16).toUpperCase();
  }

  // The screen planes a byte names, counted from 1 as chapter 2 counts them.
  function planes(byte) {
    var named = [];
    for (var p = 0; p < 5; p++) if (byte & (1 << p)) named.push(p + 1);
    if (!named.length) return 'no plane';
    if (named.length === 1) return 'plane ' + named[0];
    return 'planes ' + named.slice(0, -1).join(', ') + ' and ' + named[named.length - 1];
  }

  function trimmed(name) {
    return name.replace(/\s+$/, '');
  }

  // The crop of one shape: the sheet as the box's background, the box w by h pixels times zoom
  // at most, never wider than its column.
  function crop(box, container, place, zoom) {
    var sheet = container.sheet_size, x = place[0], y = place[1], w = place[2], h = place[3];
    box.style.backgroundImage = 'url("' + new URL(container.sheet, base) + '")';
    box.style.backgroundSize = (sheet[0] / w * 100) + '% ' + (sheet[1] / h * 100) + '%';
    box.style.backgroundPosition = (sheet[0] === w ? 0 : x / (sheet[0] - w) * 100) + '% ' +
                                   (sheet[1] === h ? 0 : y / (sheet[1] - h) * 100) + '%';
    box.style.width = (w * zoom) + 'px';
    box.style.aspectRatio = w + ' / ' + h;
  }

  var index = null, loaded = {}, chosen = null, selected = null;
  var choose = el('select'), search = el('input'), count = el('p', 'wof-count');
  var panel = el('div', 'wof-panel'), gallery = el('div', 'wof-gallery');
  panel.setAttribute('aria-live', 'polite');

  function fail(what) {
    root.textContent = '';
    root.appendChild(el('p', 'wof-failed', 'The shape browser could not load its data (' + what +
      '). It needs the site served, by mkdocs serve or from the published site, not opened as a file.'));
  }

  function load(file) {
    if (loaded[file]) return Promise.resolve(loaded[file]);
    return fetch(new URL(file + '.json', base)).then(function (response) {
      if (!response.ok) throw new Error(file + '.json: ' + response.status);
      return response.json();
    }).then(function (data) {
      loaded[file] = data;
      return data;
    });
  }

  function fact(table, label, value) {
    var row = el('tr');
    row.appendChild(el('th', null, label));
    row.appendChild(el('td', null, value));
    table.appendChild(row);
  }

  function maskOf(shape) {
    if (shape.opaque === 'size')
      return 'none: one stored plane is ' + number(shape.plane_bytes) + ' bytes, more than the ' +
             number(index.mask_buffer) + ' of the mask buffer, so the shape is opaque';
    if (shape.opaque === 'no plane')
      return 'none: it stores no plane, so it is opaque and its clear and set bytes fill its box';
    if (shape.planes === 1) return 'its one stored plane';
    return 'the OR of its ' + shape.planes + ' stored planes, built in the mask buffer';
  }

  function show(container, shape) {
    selected = shape;
    Array.prototype.forEach.call(gallery.querySelectorAll('.wof-shape'), function (tile) {
      tile.classList.toggle('wof-chosen', tile.wofShape === shape);
    });
    panel.textContent = '';
    panel.appendChild(el('p', 'wof-panel-title', trimmed(shape.name)));
    panel.appendChild(el('p', 'wof-panel-sub', container.container + ', number ' + shape.number));

    var w = shape.width, h = shape.height, zoom = Math.max(1, Math.min(6, Math.floor(288 / w)));
    // The hotspot is framed beside the crop, not in it, so that the mirror turns the pixels
    // and the frame is placed by the rule.
    var stage = el('div', 'wof-stage'), frame = el('div', 'wof-frame');
    var box = el('div', 'wof-crop'), spot = el('span', 'wof-spot');
    crop(box, container, shape.sheet, zoom);
    frame.appendChild(box);
    frame.appendChild(spot);
    stage.appendChild(frame);
    panel.appendChild(stage);

    var table = el('table', 'wof-facts'), hotspot = el('td'), mirror = null;
    function place(mirrored) {
      var x = mirrored ? w - 1 - shape.hotspot[0] : shape.hotspot[0], y = shape.hotspot[1];
      box.classList.toggle('wof-mirrored', mirrored);
      spot.style.left = (x / w * 100) + '%';
      spot.style.top = (y / h * 100) + '%';
      spot.style.width = (100 / w) + '%';
      spot.style.height = (100 / h) + '%';
      spot.hidden = x < 0 || x >= w || y < 0 || y >= h;
      hotspot.textContent = '(' + x + ', ' + y + ')' + (mirrored ?
        ', mirrored: ' + w + ' less 1 less ' + shape.hotspot[0] : '') +
        (spot.hidden ? ', outside the box' : '');
    }
    if (shape.mirrored) {
      var label = el('label', 'wof-toggle');
      mirror = el('input');
      mirror.type = 'checkbox';
      mirror.addEventListener('change', function () { place(mirror.checked); });
      label.appendChild(mirror);
      label.appendChild(document.createTextNode(' Mirrored, as shape_mirror_x turns it'));
      panel.appendChild(label);
    }

    fact(table, 'Size', w + ' by ' + h + ' pixels, ' + shape.width_bytes + ' bytes a row');
    var row = el('tr');
    row.appendChild(el('th', null, 'Hotspot'));
    row.appendChild(hotspot);
    table.appendChild(row);
    fact(table, 'Words at +8, +10', '(' + shape.cut[0] + ', ' + shape.cut[1] + ')' +
         (shape.mirrored ? ', as the file holds them; the game writes its mirror marker into +8'
          : container.container === 'selectrank.shp' ? ', where the rank selection draws it'
          : ', the place it was cut from in its picture'));
    fact(table, 'Stored planes', shape.planes ? shape.planes + ', each ' +
         number(shape.plane_bytes) + ' bytes' : 'none');
    fact(table, 'Plane masks', shape.plane_masks.length ? shape.plane_masks.map(function (m) {
      return hex(m) + ' ' + planes(m);
    }).join('; ') : 'none');
    fact(table, 'Clear byte', hex(shape.clear) + ', ' + planes(shape.clear));
    fact(table, 'Set byte', hex(shape.set) + ', ' + planes(shape.set));
    fact(table, 'Mask', maskOf(shape));
    fact(table, 'Record', number(shape.record_bytes) + ' bytes: the header of 20 and the planes');
    fact(table, 'Colours', 'the numbers its planes store, through ' + container.palette + ', ' +
         container.palette_note + '; colour 0 left open' +
         (container.palette_colours < 32 ? ', a number above 15 losing its fifth plane' : ''));
    panel.appendChild(table);
    place(false);
    if (window.matchMedia('(max-width: 59.984375em)').matches)
      panel.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function tile(container, shape, every) {
    var button = el('button', 'wof-shape'), box = el('span', 'wof-crop');
    button.type = 'button';
    button.wofShape = shape;
    button.title = trimmed(shape.name) + ', ' + shape.width + ' by ' + shape.height;
    if (shape === selected) button.classList.add('wof-chosen');
    crop(box, container, shape.sheet, shape.width <= 64 && shape.height <= 32 ? 3 : 2);
    button.appendChild(box);
    button.appendChild(el('span', 'wof-shape-name', trimmed(shape.name)));
    if (every) button.appendChild(el('span', 'wof-shape-from', container.container));
    button.addEventListener('click', function () { show(container, shape); });
    return button;
  }

  function draw() {
    var files = chosen === null ? index.containers.map(function (c) { return c.file; }) : [chosen];
    var query = search.value.trim().toLowerCase();
    Promise.all(files.map(load)).then(function (containers) {
      gallery.textContent = '';
      var shown = 0, total = 0;
      containers.forEach(function (container) {
        container.shapes.forEach(function (shape) {
          total++;
          if (query && trimmed(shape.name).toLowerCase().indexOf(query) < 0) return;
          shown++;
          gallery.appendChild(tile(container, shape, chosen === null));
        });
      });
      count.textContent = (shown === total ? number(total) : number(shown) + ' of ' +
                           number(total)) + ' shapes' + (query ? ' whose name holds "' +
                           search.value.trim() + '"' : '');
      if (!shown) gallery.appendChild(el('p', 'wof-none', 'No shape of this choice has that name.'));
    }).catch(function (error) { fail(error.message); });
  }

  function start(data) {
    index = data;
    data.containers.forEach(function (c) {
      var option = el('option', null, c.container + ', ' + c.shapes + ' shapes');
      option.value = c.file;
      choose.appendChild(option);
    });
    var every = el('option', null, 'Every container, ' + number(data.shapes) + ' shapes');
    every.value = '';
    choose.appendChild(every);
    chosen = data.containers[0].file;
    choose.value = chosen;
    search.type = 'search';
    search.placeholder = 'A name, as hc05';
    search.setAttribute('aria-label', 'Find a shape by its name');
    choose.setAttribute('aria-label', 'The container');

    var controls = el('div', 'wof-controls');
    controls.appendChild(choose);
    controls.appendChild(search);
    controls.appendChild(count);
    panel.appendChild(el('p', 'wof-panel-hint', 'Choose a shape to read its record.'));
    var body = el('div', 'wof-browser-body');
    body.appendChild(panel);
    body.appendChild(gallery);
    root.textContent = '';
    root.appendChild(controls);
    root.appendChild(body);

    choose.addEventListener('change', function () {
      chosen = choose.value || null;
      draw();
    });
    search.addEventListener('input', draw);
    draw();
  }

  fetch(new URL('index.json', base)).then(function (response) {
    if (!response.ok) throw new Error('index.json: ' + response.status);
    return response.json();
  }).then(start).catch(function (error) { fail(error.message); });
})();
