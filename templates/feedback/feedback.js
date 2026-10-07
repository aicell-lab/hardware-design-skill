/* Design feedback for the report page: pin notes on the 3D model, mark up any picture, add photos of the
   real hardware, then "Send to Claude". Notes go to review/server.py (window.FEEDBACK_API), which files
   them in the project's feedback/ folder for the next design revision. Needs nothing but <model-viewer>. */
(() => {
  "use strict";
  const API = (window.FEEDBACK_API || "").replace(/\/+$/, "");
  const REV = window.DESIGN_REV || "";
  const KIND = { "3d": "3D model", image: "Picture", photo: "Photo", note: "Note" };
  const PENDING = "fb-pending";
  const mv = document.querySelector("model-viewer");
  let items = [];
  let author = localStorage.getItem("fb-author") || "";
  let pinMode = false;
  let pinned = 0;

  // ------------------------------------------------------------------ helpers
  function h(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (k === "class") e.className = v;
      else e.setAttribute(k, v === true ? "" : v);
    }
    for (const k of kids.flat()) if (k != null && k !== false) e.append(k);
    return e;
  }
  const media = (p) => (p ? `${API}/${p}` : "");
  const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
  const fresh = () => items.filter((i) => i.round == null).length;
  // pins and marks are drawn on this revision's model and pictures: hide sent notes made on older revisions
  const current = (i) => i.round == null || !i.rev || i.rev === REV || i.image?.startsWith("media/");

  async function api(method, path, body) {
    const r = await fetch(API + path, {
      method,
      body: body ? JSON.stringify(body) : undefined,
      headers: body ? { "Content-Type": "application/json" } : undefined,
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
    return j;
  }

  // A small floating editor; resolves with the text, or null when cancelled.
  function ask({ title, x, y, value = "", optional = false, preview, placeholder }) {
    return new Promise((resolve) => {
      const ta = h("textarea", { rows: 3, placeholder: placeholder || (optional ? "Optional" : "What should change here?") });
      ta.value = value;
      const done = (v) => { pop.remove(); document.removeEventListener("keydown", key, true); resolve(v); };
      const save = () => { const v = ta.value.trim(); if (v || optional) done(v); else ta.focus(); };
      const key = (e) => {
        if (e.key === "Escape") { e.stopPropagation(); done(null); }
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) save();
      };
      const pop = h("div", { class: "fb-pop" },
        h("b", {}, title),
        preview ? h("img", { class: "fb-prev", src: preview, alt: "" }) : null,
        ta,
        h("div", { class: "fb-row2" },
          h("span", { class: "fb-hint" }, "Ctrl+Enter saves"),
          h("button", { onclick: () => done(null) }, "Cancel"),
          h("button", { class: "fb-primary", onclick: save }, "Save")));
      document.body.append(pop);
      const w = pop.offsetWidth, ht = pop.offsetHeight;
      const left = x == null ? (innerWidth - w) / 2 : Math.min(Math.max(8, x + 16), innerWidth - w - 8);
      const top = y == null ? (innerHeight - ht) / 2 : Math.min(Math.max(8, y + 16), innerHeight - ht - 8);
      Object.assign(pop.style, { left: `${left}px`, top: `${top}px` });
      document.addEventListener("keydown", key, true);
      ta.focus();
    });
  }

  // ------------------------------------------------------------------ panel
  const count = h("span", { class: "fb-count" });
  const fab = h("button", { class: "fb-fab", onclick: () => show(panel.hidden) }, "💬 Feedback", count);
  const list = h("div", { class: "fb-list" });
  const status = h("div", { class: "fb-status" });
  const sendBtn = h("button", { class: "fb-primary fb-send", onclick: sendRound }, "Send to Claude");
  const files = h("input", { type: "file", accept: "image/*", multiple: true, hidden: true,
    onchange: (e) => { addPhotos([...e.target.files]); e.target.value = ""; } });
  const name = h("input", { class: "fb-name", placeholder: "Your name (optional)", value: author,
    oninput: (e) => localStorage.setItem("fb-author", (author = e.target.value.trim())) });
  const panel = h("aside", { class: "fb-panel", hidden: true },
    h("div", { class: "fb-head" }, h("b", {}, "Design feedback"),
      h("button", { class: "fb-x", title: "Close", onclick: () => show(false) }, "×")),
    h("div", { class: "fb-tools" },
      h("button", { onclick: startPin }, "📍 Pin on 3D"),
      h("button", { onclick: () => files.click() }, "📷 Add photos"),
      h("button", { onclick: addNote }, "✏️ Note")),
    h("p", { class: "fb-help" }, "Click any picture on the page to mark it up. Drop or paste photos here. "
      + "Notes save as you go; press Send when you're done."),
    name, list, files,
    h("div", { class: "fb-foot" }, status, sendBtn));
  document.body.append(fab, panel);

  function show(on) {
    panel.hidden = !on;
    if (on) load();
  }

  panel.addEventListener("dragover", (e) => { e.preventDefault(); panel.classList.add("fb-drop"); });
  panel.addEventListener("dragleave", () => panel.classList.remove("fb-drop"));
  panel.addEventListener("drop", (e) => {
    e.preventDefault();
    panel.classList.remove("fb-drop");
    addPhotos([...e.dataTransfer.files]);
  });
  document.addEventListener("paste", (e) => {
    const imgs = [...(e.clipboardData?.files || [])].filter((f) => f.type.startsWith("image/"));
    if (imgs.length && !panel.hidden) { e.preventDefault(); addPhotos(imgs); }
  });

  function render() {
    const n = fresh();
    count.textContent = n ? String(n) : "";
    list.replaceChildren(...(items.length ? [...items].reverse().map(row)
      : [h("p", { class: "fb-empty" }, "No notes yet. Pin one on the 3D model, mark up a picture or add a photo.")]));
    sendBtn.disabled = !n;
    sendBtn.textContent = n ? `Send ${plural(n, "note")} to Claude` : "Nothing new to send";
    renderPins();
    renderDots();
  }

  function row(it) {
    const sent = it.round != null;
    const meta = [KIND[it.type], it.type === "3d" ? it.object : "", it.author, sent ? `sent in round ${it.round}` : ""]
      .filter(Boolean).join(" · ");
    return h("div", { class: `fb-item${sent ? " sent" : ""}`, "data-n": it.n, onclick: () => reveal(it) },
      h("span", { class: "fb-n" }, String(it.n)),
      it.snap ? h("img", { class: "fb-thumb", src: media(it.snap), alt: "", loading: "lazy" }) : null,
      h("div", { class: "fb-body" },
        h("div", { class: "fb-text" }, it.text || "(no caption)"),
        h("div", { class: "fb-meta" }, meta)),
      sent ? null : h("div", { class: "fb-acts" },
        h("button", { title: "Edit", onclick: (e) => { e.stopPropagation(); edit(it, e); } }, "✎"),
        h("button", { title: "Delete", onclick: (e) => { e.stopPropagation(); remove(it); } }, "✕")));
  }

  function reveal(it) {
    if (it.type === "3d") show3d(it);
    else if (it.type === "image") openMarkup(it.image, it.n);
    else if (it.type === "photo") openMarkup(it.snap);
  }

  function highlight(n) {
    panel.hidden = false;
    const el = list.querySelector(`[data-n="${n}"]`);
    if (!el) return;
    el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    el.classList.add("fb-hl");
    setTimeout(() => el.classList.remove("fb-hl"), 1600);
  }

  function say(msg, bad) {
    status.textContent = msg;
    status.classList.toggle("fb-bad", !!bad);
  }

  // ------------------------------------------------------------------ storage
  async function create(body) {
    Object.assign(body, { author, rev: REV });
    say("Saving…");
    try {
      const it = await api("POST", "/api/items", body);
      items.push(it);
      render();
      say(`Saved note ${it.n}`);
      return it;
    } catch (err) {
      if (err instanceof TypeError) { keep(body); say("Offline: kept in this browser, it uploads next time", true); }
      else say(`Couldn't save: ${err.message}`, true);
    }
  }

  function keep(body) {
    try {
      const q = JSON.parse(localStorage.getItem(PENDING) || "[]");
      q.push(body);
      localStorage.setItem(PENDING, JSON.stringify(q));
    } catch { say("Couldn't keep it in this browser either", true); }
  }

  async function flush() {
    const q = JSON.parse(localStorage.getItem(PENDING) || "[]");
    while (q.length) {
      try { await api("POST", "/api/items", q[0]); q.shift(); } catch { break; }
    }
    if (q.length) localStorage.setItem(PENDING, JSON.stringify(q));
    else localStorage.removeItem(PENDING);
  }

  async function load() {
    if (!API) return say("The feedback server isn't set up for this page", true);
    try {
      await flush();
      items = (await api("GET", "/api/items")).items || [];
      render();
    } catch { say("Feedback server unreachable: new notes are kept in this browser", true); }
  }

  async function edit(it, e) {
    const text = await ask({ title: `Edit note ${it.n}`, value: it.text, x: e.clientX - 320, y: e.clientY,
      optional: it.type === "photo" });
    if (text == null) return;
    try { Object.assign(it, await api("PUT", `/api/items/${it.n}`, { text })); render(); say(`Saved note ${it.n}`); }
    catch (err) { say(err.message, true); }
  }

  async function remove(it) {
    if (!confirm(`Delete note ${it.n}?`)) return;
    try { await api("DELETE", `/api/items/${it.n}`); items = items.filter((i) => i !== it); render(); say("Deleted"); }
    catch (err) { say(err.message, true); }
  }

  async function sendRound() {
    const n = fresh();
    if (!n || !confirm(`Send ${plural(n, "note")} to Claude for the next design revision?`)) return;
    sendBtn.disabled = true;
    say("Sending…");
    try {
      const r = await api("POST", "/api/send", {});
      await load();
      say(r.notified ? `Sent ✓ Round ${r.round} is with Claude.`
        : `Saved as round ${r.round}, but Claude wasn't messaged (${r.detail}). Tell Claude "feedback round ${r.round} is ready".`,
      !r.notified);
    } catch (err) { say(`Couldn't send: ${err.message}`, true); render(); }
  }

  // ------------------------------------------------------------------ 3D pins
  // Pins live in the assembled pose (that is what the CAD coordinates mean). While the view is exploded
  // (viewer.js), a pin is shown moved with its part, and a new pin has its part's offset taken off.
  const mpos = (a) => a.map((q) => `${q}m`).join(" ");
  const shift = (pos, object, sgn = 1) => {
    const ex = window.EXPLODE || { amount: 0, offsets: {} };
    const o = ex.offsets[object] || [0, 0, 0];
    return pos.map((p, k) => p + o[k] * ex.amount * sgn);
  };
  const bar = h("div", { class: "fb-bar", hidden: true },
    h("span", {}, "Click the model where you want a note · drag to rotate · scroll to zoom"),
    h("button", { class: "fb-primary", onclick: () => stopPin() }, "Done"));
  const mvBtn = h("button", { class: "fb-mvbtn", onclick: (e) => { e.stopPropagation(); pinMode ? stopPin() : startPin(); } },
    "📍 Comment on 3D");
  if (mv) {
    mv.append(mvBtn);
    document.body.append(bar);
  }

  function startPin() {
    if (!mv) return;
    pinMode = true;
    pinned = 0;
    mv.autoRotate = false;
    mv.classList.add("fb-full", "fb-pinning");
    bar.hidden = false;
    mvBtn.hidden = true;
    panel.hidden = true;
  }

  function stopPin() {
    pinMode = false;
    mv.classList.remove("fb-full", "fb-pinning");
    bar.hidden = true;
    mvBtn.hidden = false;
    if (pinned) panel.hidden = false;
  }

  let downAt = null;
  mv?.addEventListener("pointerdown", (e) => { downAt = [e.clientX, e.clientY]; });
  mv?.addEventListener("click", async (e) => {
    if (!pinMode || e.target.closest?.(".fb-pin, .fb-mvbtn")) return;
    if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 6) return;   // that was a drag
    const hit = mv.positionAndNormalFromPoint(e.clientX, e.clientY);
    if (!hit) return;
    const normal = [hit.normal.x, hit.normal.y, hit.normal.z];
    const object = mv.materialFromPoint(e.clientX, e.clientY)?.name || "";
    const pos = shift([hit.position.x, hit.position.y, hit.position.z], object, -1);
    const temp = pinEl({ n: "+", pos, normal, object, text: "" }, true);
    const snapshot = await shot(e.clientX, e.clientY).catch(() => null);
    const text = await ask({ title: object ? `Note on the ${object}` : "Note on this spot", x: e.clientX, y: e.clientY });
    temp.remove();
    if (text == null) return;
    const camera = { orbit: mv.getCameraOrbit().toString(), target: mv.getCameraTarget().toString(),
      fov: `${mv.getFieldOfView()}deg` };
    if (await create({ type: "3d", text, pos, normal, object, camera, snapshot })) pinned++;
  });

  // The current view as a JPEG with the clicked spot ringed, so the note reads on its own.
  async function shot(cx, cy) {
    const bmp = await createImageBitmap(await mv.toBlob({ mimeType: "image/png", idealAspect: false }));
    const r = mv.getBoundingClientRect();
    const s = Math.min(1, 1280 / bmp.width);
    const c = h("canvas", { width: Math.round(bmp.width * s), height: Math.round(bmp.height * s) });
    const g = c.getContext("2d");
    g.fillStyle = "#f3f2ee";                          // the viewer is transparent; JPEG would turn that black
    g.fillRect(0, 0, c.width, c.height);
    g.drawImage(bmp, 0, 0, c.width, c.height);
    const x = ((cx - r.left) / r.width) * c.width, y = ((cy - r.top) / r.height) * c.height;
    const rad = Math.max(11, c.width / 70);
    for (const [col, lw] of [["#fff", rad / 2.6], ["#e85028", rad / 5]]) {
      g.strokeStyle = col;
      g.lineWidth = lw;
      g.beginPath();
      g.arc(x, y, rad, 0, Math.PI * 2);
      g.stroke();
    }
    g.fillStyle = "#e85028";
    g.beginPath();
    g.arc(x, y, rad / 4, 0, Math.PI * 2);
    g.fill();
    return c.toDataURL("image/jpeg", 0.85);
  }

  function pinEl(it, temp) {
    const b = h("button", {
      class: `fb-pin${it.round != null ? " sent" : ""}${temp ? " temp" : ""}`,
      slot: `hotspot-fb-${temp ? "new" : it.n}`, "data-position": mpos(shift(it.pos, it.object)),
      "data-normal": mpos(it.normal), title: it.text || null,
    }, String(it.n));
    b.fbItem = it;
    b.addEventListener("click", (e) => { e.stopPropagation(); if (!temp) highlight(it.n); });
    mv.append(b);
    return b;
  }

  mv?.addEventListener("fb-explode", () => mv.querySelectorAll(".fb-pin").forEach((b) => {
    if (b.fbItem) mv.updateHotspot({ name: b.slot, position: mpos(shift(b.fbItem.pos, b.fbItem.object)) });
  }));

  function renderPins() {
    if (!mv) return;
    mv.querySelectorAll(".fb-pin:not(.temp)").forEach((b) => b.remove());
    items.filter((i) => i.type === "3d" && i.pos && current(i)).forEach((i) => pinEl(i));
  }

  function show3d(it) {
    mv.scrollIntoView({ behavior: "smooth", block: "center" });
    mv.autoRotate = false;
    if (it.camera?.orbit) {
      mv.cameraOrbit = it.camera.orbit;
      mv.cameraTarget = it.camera.target;
      if (it.camera.fov) mv.fieldOfView = it.camera.fov;
    }
    const b = mv.querySelector(`[slot="hotspot-fb-${it.n}"]`);
    b?.classList.add("fb-hl");
    setTimeout(() => b?.classList.remove("fb-hl"), 1800);
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && pinMode && !document.querySelector(".fb-pop, .fb-lightbox")) stopPin();
  });

  // ------------------------------------------------------------------ picture mark-up
  function markable() {
    document.querySelectorAll("main figure img").forEach((img) => {
      const ref = img.getAttribute("src");
      const wrap = h("span", { class: "fb-wrap", title: "Click to mark up this picture", onclick: () => openMarkup(ref) });
      img.replaceWith(wrap);
      wrap.append(img, h("span", { class: "fb-chip" }, "✎ Mark up"), h("span", { class: "fb-dots", "data-ref": ref }));
    });
  }

  const marksFor = (ref) => items.filter((i) => i.type === "image" && i.image === ref && current(i));

  function markEl(it) {
    const box = it.w > 0.004 && it.h > 0.004;
    const el = h("span", { class: `${box ? "fb-box" : "fb-dot"}${it.round != null ? " sent" : ""}`, title: it.text },
      h("i", {}, String(it.n)));
    Object.assign(el.style, { left: `${it.x * 100}%`, top: `${it.y * 100}%` },
      box ? { width: `${it.w * 100}%`, height: `${it.h * 100}%` } : {});
    return el;
  }

  function renderDots() {
    document.querySelectorAll(".fb-dots").forEach((d) => d.replaceChildren(...marksFor(d.dataset.ref).map(markEl)));
  }

  function openMarkup(ref, focus) {
    const layer = h("div", { class: "fb-layer" });
    const close = () => { lb.remove(); document.removeEventListener("keydown", esc); };
    const esc = (e) => { if (e.key === "Escape") close(); };
    const lb = h("div", { class: "fb-lightbox", onclick: (e) => { if (e.target === lb) close(); } },
      h("div", { class: "fb-lbbar" }, h("span", {}, "Click to pin a note · drag to mark an area"),
        h("button", { class: "fb-primary", onclick: close }, "Done")),
      h("div", { class: "fb-stage" }, h("img", { src: ref.startsWith("media/") ? media(ref) : ref, alt: "", draggable: "false" }), layer));
    document.body.append(lb);
    document.addEventListener("keydown", esc);
    const draw = () => layer.replaceChildren(...marksFor(ref).map((it) => {
      const el = markEl(it);
      if (it.n === focus) el.classList.add("fb-hl");
      el.addEventListener("click", (e) => { e.stopPropagation(); highlight(it.n); });
      return el;
    }));
    draw();

    let start = null, shape = null;
    const rel = (e) => {
      const r = layer.getBoundingClientRect();
      return [Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), Math.min(1, Math.max(0, (e.clientY - r.top) / r.height))];
    };
    layer.addEventListener("pointerdown", (e) => {
      if (e.target !== layer) return;
      start = rel(e);
      layer.setPointerCapture(e.pointerId);
    });
    layer.addEventListener("pointermove", (e) => {
      if (!start) return;
      const [x, y] = rel(e);
      if (!shape && Math.hypot(x - start[0], y - start[1]) < 0.012) return;
      shape ||= layer.appendChild(h("span", { class: "fb-box fb-new" }));
      Object.assign(shape.style, { left: `${Math.min(x, start[0]) * 100}%`, top: `${Math.min(y, start[1]) * 100}%`,
        width: `${Math.abs(x - start[0]) * 100}%`, height: `${Math.abs(y - start[1]) * 100}%` });
    });
    layer.addEventListener("pointerup", async (e) => {
      if (!start) return;
      const [x, y] = rel(e), s = start;
      start = null;
      const mark = shape ? { x: Math.min(x, s[0]), y: Math.min(y, s[1]), w: Math.abs(x - s[0]), h: Math.abs(y - s[1]) }
        : { x: s[0], y: s[1], w: 0, h: 0 };
      if (!shape) {
        shape = layer.appendChild(h("span", { class: "fb-dot fb-new" }, h("i", {}, "+")));
        Object.assign(shape.style, { left: `${mark.x * 100}%`, top: `${mark.y * 100}%` });
      }
      const text = await ask({ title: "Note on this spot", x: e.clientX, y: e.clientY });
      shape.remove();
      shape = null;
      if (text != null && await create({ type: "image", image: ref, text, ...mark })) draw();
    });
  }

  // ------------------------------------------------------------------ photos and notes
  async function addPhotos(list) {
    for (const f of list.filter((q) => q.type.startsWith("image/"))) {
      let data;
      try { data = await shrink(f); } catch { say(`Couldn't read ${f.name}: use a JPEG or PNG`, true); continue; }
      const text = await ask({ title: "Add this photo", preview: data, optional: true,
        placeholder: "What does it show? (optional)" });
      if (text != null) await create({ type: "photo", text, photo: data });
    }
  }

  async function shrink(file, max = 1600) {
    const bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
    const s = Math.min(1, max / Math.max(bmp.width, bmp.height));
    const c = h("canvas", { width: Math.round(bmp.width * s), height: Math.round(bmp.height * s) });
    c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
    return c.toDataURL("image/jpeg", 0.85);
  }

  async function addNote() {
    const text = await ask({ title: "General note", placeholder: "Anything about the design…" });
    if (text) await create({ type: "note", text });
  }

  markable();
  load();
})();
