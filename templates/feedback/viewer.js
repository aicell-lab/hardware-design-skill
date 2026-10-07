/* Explode control for the report's 3D view. assembly.glb carries an "explode" animation (0 -> 1 s) that moves
   each part off the way it goes on; the button eases between assembled and exploded by scrubbing it.
   window.EXPLODE = { amount, offsets: { material name: [x, y, z] metres } } lets the feedback pins follow their
   parts; "fb-explode" fires on the <model-viewer> whenever the amount changes. */
(() => {
  const mv = document.querySelector("model-viewer");
  if (!mv) return;
  const EX = (window.EXPLODE = Object.assign({ amount: 0, offsets: {} }, window.EXPLODE || {}));
  let target = 0, frame = 0, ready = false;

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "mv-explode";
  btn.textContent = "Explode";
  btn.title = "Lift the parts apart to see each one";
  btn.hidden = true;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    target = target ? 0 : 1;
    btn.classList.toggle("on", !!target);
    btn.textContent = target ? "Assemble" : "Explode";
    if (!frame) frame = requestAnimationFrame(step);
  });
  mv.append(btn);

  mv.addEventListener("load", () => {
    if (!mv.availableAnimations?.includes("explode")) return;
    mv.animationName = "explode";
    mv.play();                                // sets the clip up; from here on it is only scrubbed
    setTimeout(() => {
      mv.pause();
      mv.currentTime = EX.amount * END();
      ready = true;
      btn.hidden = false;
    }, 150);
  });
  const END = () => (mv.duration || 1) * 0.999;   // the clip loops: its very end would wrap round to 0

  function step() {
    EX.amount += (target - EX.amount) * 0.12;
    if (Math.abs(target - EX.amount) < 0.002) EX.amount = target;
    if (ready) mv.currentTime = EX.amount * END();
    mv.dispatchEvent(new CustomEvent("fb-explode", { detail: EX.amount }));
    frame = EX.amount === target ? 0 : requestAnimationFrame(step);
  }
})();
