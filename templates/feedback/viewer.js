/* Spread parts control for the report's 3D view. assembly.glb carries a "spread" animation (0 -> 1 s) that moves
   each part off the way it goes on; the button eases between assembled and spread-out by scrubbing it.
   window.SPREAD = { amount, offsets: { material name: [x, y, z] metres } } lets the feedback pins follow their
   parts; "fb-spread" fires on the <model-viewer> whenever the amount changes. */
(() => {
  const mv = document.querySelector("model-viewer");
  if (!mv) return;
  const EX = (window.SPREAD = Object.assign({ amount: 0, offsets: {} }, window.SPREAD || {}));
  let target = 0, frame = 0, ready = false;

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "mv-spread";
  btn.textContent = "Spread parts (loading…)";
  btn.title = "Lift the parts apart to see each one";
  btn.disabled = true;                        // always visible; enabled once the model and its animation are ready
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!ready) return;
    target = target ? 0 : 1;
    btn.classList.toggle("on", !!target);
    btn.textContent = target ? "Assemble" : "Spread parts";
    if (!frame) frame = requestAnimationFrame(step);
  });
  mv.append(btn);

  // The model can finish loading (e.g. from the browser cache) before this deferred script runs, and then "load"
  // never reaches us and the button stays hidden. So: set up on "load", right now if it already loaded, and again on
  // window load as a last check. setup() runs once.
  let setUp = false;
  function setup() {
    if (setUp || !mv.loaded || !mv.availableAnimations?.includes("spread")) return;
    setUp = true;
    mv.animationName = "spread";
    mv.play();                                // sets the clip up; from here on it is only scrubbed
    setTimeout(() => {
      mv.pause();
      mv.currentTime = EX.amount * END();
      ready = true;
      btn.disabled = false;
      btn.textContent = target ? "Assemble" : "Spread parts";
    }, 150);
  }
  mv.addEventListener("load", setup);
  setup();
  window.addEventListener("load", setup);
  customElements.whenDefined("model-viewer").then(() => setTimeout(setup, 0));
  let tries = 0;                              // and keep checking once a second, so a missed event can't hide it
  const poll = setInterval(() => {
    setup();
    if (setUp || ++tries > 120) {
      clearInterval(poll);
      if (!setUp) btn.textContent = mv.loaded ? "Spread parts (no animation in the model)" : "3D model did not load";
    }
  }, 1000);
  mv.addEventListener("error", () => { if (!setUp) btn.textContent = "3D model did not load"; });
  const END = () => (mv.duration || 1) * 0.999;   // the clip loops: its very end would wrap round to 0

  function step() {
    EX.amount += (target - EX.amount) * 0.12;
    if (Math.abs(target - EX.amount) < 0.002) EX.amount = target;
    if (ready) mv.currentTime = EX.amount * END();
    mv.dispatchEvent(new CustomEvent("fb-spread", { detail: EX.amount }));
    frame = EX.amount === target ? 0 : requestAnimationFrame(step);
  }
})();
