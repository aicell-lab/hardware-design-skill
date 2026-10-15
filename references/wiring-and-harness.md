# Wiring and harness: design it like an electrician, prove it in 3D

Learned the hard way on the DGX Safe Box (rounds 11–12). The user said: "the wires are a mess, I can't tell where anything
goes. Do it the way a normal electrician would, and hold yourself to that standard so I don't have to ask." Logic
drawings ("pin A to pin B") are not a wiring design. A wiring design says **where every wire lies, what holds it, and how
it ends**, and it is checked in the CAD like any printed part.

## The standard (IPC/WHMA-A-620 style, scaled to hobby builds)

1. **One wire per terminal.** No in-air splices with 4–8 wires in one heat-shrink, and no "two wires in one hole" unless the
   part is a lug or turret that is made for it. Multi-drop nets (5 V, GND, 3V3, shared clocks) land on a **junction board**:
   stripboard, one strip per net, one hole per wire. It is also the test point for every net.
2. **Strips run like bus bars, across the incoming wires.** Every wire then comes straight in along its own column and
   drops into its net's row. With strips running *along* the wire direction, each wire needs a sideways jog in a few mm,
   and those jogs tangle (that was v1: 14 of 66 clear). Line the column grid up with the densest source, e.g. the MCU's
   2.54 mm pin rows. Point-to-point nets share a row as segments, with a track cut and one empty hole between segments.
3. **Bundles on lanes.** Wires that go the same way run side by side, at a fixed pitch (wire Ø + 0.05), on orthogonal
   lanes. Where bundles must cross, they cross in different layers (Δz ≥ wire Ø).
4. **Every floor run lies in a channel** printed into the part it lies on: two rails, snap lips every 25–35 mm, and an
   engraved label ("MICS + MUTE", "LED + USB"). The groove tells the builder the path; it is also strain relief.
5. **A disconnect where a part comes off** (an inline Dupont/JST pair in a printed dock), instead of 120 mm of "book"
   slack. Pre-crimped jumper wires cut in half need no crimper.
6. **Twisted pairs** for speaker leads and USB D+/D−. Upright or flat parts (diodes, series resistors) go on the junction
   board, not in sleeves in mid-air.
7. **Labels and a cut list.** Every wire has an ID at both ends. Its length is the routed 3D length + 15 mm strip/solder.

## Prove it in 3D (and make the checker able to fail)

- Model every wire as a tube (Ø of the real insulation) along a polyline from the real pad, pin or cup. Use small corner
  radii (≈ 0.8 mm): a 2 mm corner rounding cuts into the neighbour in a 1.15 mm-pitch bundle.
- Check **wire vs part** (inside, or closer than the radius) **and wire vs wire** (closer than one diameter). Trim 2.5 mm
  (part check) / 4 mm (wire check) at the ends, where contact is by design. Earlier revisions checked only wire vs part
  and called a tangle "45 of 45 clear".
- Positive controls that must collide: a wire laid on another's path, a route moved 1.5 mm into a wall, a straight
  pin-to-hole line with no layering.
- Report the result as measured ("59 of 60 clear, 5 jumpers open"), not a rounded "all clear".

## Let a solver do the bookkeeping

The rules interact (row of a net vs every column it is used in), so hand placement fails. What worked was simulated
annealing over (row per net, column per wire) with hard rules as costs:
- in a column, wires fed from the front take the southern holes, wires fed from the rear the northern ones;
- of two wires coming from the same edge, the higher one ends further from that edge, so it passes over the other's end;
- two front wires on one column must come from different trough layers, with the lower layer in the southern hole;
- no segment overlap in a row (cut + one empty hole); ≤ N wires per exit column; nothing under a part that hangs low.

Track the best state, cool slowly (T ∝ (1 − t)²), run 4–6 seeds in parallel, and diagnose a stuck cost by instrumenting
each `c +=` term. When it stalls at a few violations, the fix was always **structural**, not more iterations: move a part
(the diode) to free a column, drop a redundant wire (the MCU already has ground through its USB plug), or widen an allowed
range.

## Order of work

1. Netlist → classify nets (multi-drop vs point-to-point) → junction board size and row count.
2. Free-space map of the assembled product at 2–3 heights (occupancy grid). Find the corridors first.
3. Lanes, trough and channels as shared constants, used by both the router and the CAD of the channels.
4. Route, check, fix by group (bay internals, MCU ribbon, trough, connectors). Save the plan and log to a file after each
   pass: this work outlives the context window.
5. Figures per build step (shelf wires, MCU wires, junction board, channels, all closed) and a 2D board map: strips,
   holes, wire IDs, cuts, parts. The 2D map is what the builder solders from.
