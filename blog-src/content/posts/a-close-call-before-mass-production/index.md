---
title: "A close call before mass production"
date: 2026-08-30
description: "30% of our pilot run failed the same way. We blamed solder, then a counterfeit crystal, and finally found two capacitors that should not have been there."
tags: ["engineering", "hardware", "firmware"]
slug: "a-close-call-before-mass-production"
---

We built 50 pilot units before committing to the production run. 15 of them failed. A 30% failure rate on one symptom is not a parts lottery, it is a design problem, and we had to find it before ordering a thousand boards.

The symptom was always the same. Power on, red flash, then the blue LED blinks three to five times and stops. Some froze with the LED on, some with it off. The device still advertised over BLE, but pairing never completed.

## Firmware said: the 32 kHz crystal

The blue LED is driven by a timer task. A timer that stops at a random phase means the time base stopped, not the firmware. On CH592F the time base for BLE and the scheduler is the 32.768 kHz crystal, X2.

One more clue: the SDK starts the crystal at 200% drive current and drops it to the rated 100% about 500 ms after boot. Five blinks is roughly that long.

We built two test firmwares from the shipped 1.3.11 source. One held the drive at 200% forever. The other switched to the internal RC oscillator. Both fixed the freeze on every failing unit. So the crystal circuit had no margin at 100% drive. The question was why.

## Suspect one: bad solder

A 1610 crystal has two tiny pads and we use a low temperature solder paste. Cold joints seemed likely. We reflowed X2 on a failing board by hand and tested again.

No change. Still five blinks, still frozen.

## Suspect two: counterfeit crystals

If solder was fine, maybe the part was not. The spec (Epson FC1610AN, CL 12.5 pF, ESR max 90 kΩ) is tight, and a counterfeit or out of spec batch would explain a 30% fallout. But "it feels like a bad part" is not evidence. We needed numbers.

So we wrote a probe firmware that characterises the crystal at boot, before BLE starts. The time base is TMR0 clocked from the 32 MHz main crystal, so it can measure the 32 kHz path without depending on it. It runs four tests:

1. Cold start at each drive level (200, 140, 100, 70%), then hold for 5 s.
2. Start at 200%, drop to a lower level, watch for 10 s. This mirrors the SDK at boot.
3. Sweep the chip's internal load capacitance from 12 to 27 pF per pin and record the frequency at each step.
4. After boot, check every 100 ms whether the 32 kHz counter is still moving.

We ran it on a failing board and on a good one.

| | Good board | Failing board |
|---|---|---|
| Frequency at default load | 32767.9 Hz | 32765.9 Hz (about -60 ppm) |
| 100% drive, default load | stable | dies after 3 to 5 s |
| 70% drive | stable even at 27 pF | never starts |
| Frequency change across the load sweep | 5 Hz | 1 Hz |

The last row mattered most. How much a crystal's frequency moves with load is set by the crystal's own parameters. The datasheet predicts about 4 Hz across that sweep. The good board matched. The failing board was off by a factor of five. That looked exactly like a wrong or fake part.

Then we swapped crystals.

We moved the good board's crystal onto the failing board. The board now survived 100% drive, but still died at 70%, still read 32765.9 Hz, still showed the flat 1 Hz curve.

We moved the failing board's crystal onto the good board. It behaved exactly like the original. Every test passed.

The crystal was genuine and fine. The signature belonged to the board. The numbers pointed at extra capacitance across the crystal, roughly 8 pF: it lowers the frequency, flattens the pulling curve, and cuts the oscillator's negative resistance in half.

## The answer was in the PCB files

The failing units were built from a May revision of the board, the good ones from July. We diffed the Gerber exports. In the May files, the two crystal nets had two extra pads: C10 and C11, 12 pF each, one from each crystal pin to ground. The July revision had removed them.

CH592F already provides 24 pF per pin internally. The extra 12 pF brought each pin to 36 pF, so the crystal saw about 18 pF instead of its rated 12.5. Negative resistance scales with the inverse square of load capacitance, so that change alone drops the margin to under half. Units with a low ESR crystal still ran. Units with a crystal near the upper end of the ESR spec froze once the drive dropped to 100%. That is the 30%.

The capacitors were added with the best intentions. Almost every 32 kHz reference design shows two load caps. On this chip they are already inside.

## What we changed

- May revision boards get C10 and C11 removed. No crystal replacement needed.
- The factory self-test gains two checks: the crystal must survive 5 s at 70% drive, and the boot frequency must be within 40 ppm. Either one would have caught this on the first unit.

## What we took from it

Reworking a part is not a test. We reflowed and swapped X2 and learned nothing until we measured, because the crystal was never the variable.

Measure before you blame the supplier. A frequency counter that does not depend on the clock under test costs a hundred lines of firmware and gave us the one number, pulling sensitivity, that separated "bad crystal" from "bad circuit".

And when two boards behave differently, diff the boards. We spent a day on crystal theories before comparing the two PCB revisions. The netlist showed the answer in under a minute.
