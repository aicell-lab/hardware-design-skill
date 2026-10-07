# Case study: a touchscreen + phone mount for an NVIDIA DGX Spark

Two printed parts (PETG): a body that clips across the rear edge of the Spark (150 x 150 x 50.5 mm), and a
removable frame round a Waveshare ESP32-S3-Touch-AMOLED-1.8 screen (cased, 37.6 x 45.2 x 15 mm) that also
carries two flexure buttons for the case's side buttons. One flat 40 deg panel spans the width: the screen on
the right, a lane for a phone on the left, the USB-C cable hidden inside. 8 revisions over 3 days, 21 notes in
7 feedback rounds, two of them after the user printed and tried it on the real hardware.

## Revisions

| rev | trigger | what changed |
|---|---|---|
| A-B | brief (PDF) | one-piece clip-on shell; USB-C height from the vendor 3D model; standard plug envelope; first web report |
| C | "smoother, screen enters from the hidden side, phone stand on the left" | full-width body from one 2D profile; screen slides in from the right end; phone ledge |
| feedback layer | "rotate the 3D model, click a spot and comment; mark up images; attach photos; easy to pass back" | 3D pins, picture mark-up, photos, Send round -> session message (the loop in `feedback-loop.md`) |
| D | round 1 (7 notes) | side walls down to the Spark's edge with a hook; round rear returns; arch cable exit; phone 40 deg (retail stands 30-45 for tapping); flush screen on printed leaf springs; flexure buttons turning the press 90 deg |
| D.1-D.2 | rounds 2-3 | charging slot for the phone; spare cable through to pegs in the other half |
| E | round 4 | screen moved to the right end ("the cable needs about half the screen's width"); one flat panel and one straight full-width lane: "extremely simple and minimalist, good-looking with no phone" |
| F | round 5 | lane sized for an iPhone in a silicone case, low edge, screen moved up the panel, a springy "click" edge |
| G | round 6, **after the first print** | rigid screen (no springs), glass 1.5 mm proud, crush ribs + datums; button play removed; walls sized to the measured 46 mm edge; flatter catch; click edge removed; charging gap -> hole; longer pegs |
| H | round 7 + "add an explode view" | tongues reaching 8 mm under the Spark; explode animation in the web viewer, pins follow parts |

## Lessons

**Published data vs the real thing.** Designing from drawings, vendor models and reviews got the first print
close, but the user's measurements and photos found what drawings hid: the side edge is 46.0 mm, not 45.5;
the clip's 1 mm preload made the walls visibly splay. Treat every user measurement as ground truth and every
assumed number as a "to confirm" item.

**The user's taste is part of the spec.** They pushed every round toward fewer, calmer shapes: one panel,
one lane, an unbroken edge, "looks good with no phone (a sticker there)". Added cleverness (a springy click
edge) came straight back out. Offer the simple version first.

**Springs under a touchscreen feel loose.** Two printed leaf springs held the glass flush, and on the print the
screen moved under a finger. A solid floor, a datum wall, crush ribs, and the glass standing proud of a flush
frame read as tight and solid.

**Lost motion.** The buttons didn't click until the user wedged a ~1 mm paper shim beside the screen. The
geometry was right; the play wasn't: the screen could move 0.6 mm in its pocket and the frame 0.3 mm in its
recess, both away from the lever under a press. Hold every link of an actuation chain against a datum on the
side the force pushes toward.

**Check stability, not just strength.** A phone on a 40 deg stand is long; its centre of gravity sat over the
Spark's rear edge, and with hooks that popped off at ~9 N, a 2 N press at the phone's top tipped everything
backward. A tip-over check (press force vs stabilising moments) made the cause and the fix obvious.

**"A little more" may not be visible.** Deepening a hook from 0.7 to 2.2 mm earned "no obvious change here".
When the user asks for a firmer grip and there is room, change it visibly (an 8 mm tongue under the flat
underside, fitted by spreading the walls).

**Print-pose problems hide in new features.** The overhang check caught a tongue that started 5 mm above the
bed (fixed with a 45 deg cut-back) and fillets that swept through steep normals.

**Explain mechanisms with labelled cut sections.** "Solid wall: the case bears here", "glass 1.5 mm proud",
"tongue 8 mm under the Spark" on a flat section answered questions that rotating 3D views didn't.

**Keep a plan file per revision.** Long sessions get compacted; `notes/rev_X_plan.md` (notes translated,
decisions, a log with numbers) is what survives and what the next revision starts from.
