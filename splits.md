In shooting, a split is the time between two shots.

More precisely:

Split = timestamp of current shot − timestamp of previous shot

So if a timer records:

Shot 1: 1.20
Shot 2: 1.48
Shot 3: 1.77
Shot 4: 2.10

The splits are:

Shot 1: 1.20   first-shot time, not a split
Shot 2: 0.28   1.48 - 1.20
Shot 3: 0.29   1.77 - 1.48
Shot 4: 0.33   2.10 - 1.77

The first shot does not really have a split because there is no prior shot. It is usually called the draw time, first-shot time, or reaction-to-first-shot time, depending on the drill.

For intervals, the same rule applies. A split is just the interval between adjacent shots. It is not the cumulative time, and it is not the average time unless you calculate that separately.

Example:

Beep:   0.00
Shot 1: 1.10
Shot 2: 1.35
Shot 3: 1.60
Shot 4: 1.88

This gives:

First shot: 1.10
Split 1→2: 0.25
Split 2→3: 0.25
Split 3→4: 0.28
Total time: 1.88
Average split after first shot: (0.25 + 0.25 + 0.28) / 3 = 0.26

In practical shooting terms:

A 0.20 split means there was 0.20 seconds between two shots.

A 0.30 split means there was 0.30 seconds between two shots.

A 1.00 first shot means it took 1.00 second from the start beep to the first recorded shot.

For drills, you normally separate these concepts:

Start signal → first shot = draw / presentation / reaction time
Shot → shot = split
Last shot timestamp = total time

For example, in a Bill Drill with 6 shots:

Shot 1: 1.05
Shot 2: 1.26
Shot 3: 1.47
Shot 4: 1.70
Shot 5: 1.94
Shot 6: 2.20

You would read that as:

First shot: 1.05
Splits: 0.21, 0.21, 0.23, 0.24, 0.26
Total: 2.20

That tells you something useful: the shooter got the gun out in 1.05 seconds, then fired follow-up shots roughly every 0.21–0.26 seconds. If accuracy fell apart, the splits were probably too aggressive. If all hits were clean and controlled, those splits may be sustainable.

For your app/data model, I would treat it like this:

shot.timestamp = cumulative time from start beep
shot.split = timestamp - previousShot.timestamp
shot[0].split = null
shot[0].firstShotTime = shot[0].timestamp

Do not store the first shot as a “split” unless you explicitly label it differently, because that creates confusion. A lot of timers display the first shot in the same list as splits, but conceptually it is different.

A clean display would be:

Shot    Time    Split
1       1.05    —
2       1.26    0.21
3       1.47    0.21
4       1.70    0.23
5       1.94    0.24
6       2.20    0.26

Then summary stats:

First shot: 1.05
Total time: 2.20
Fastest split: 0.21
Slowest split: 0.26
Average split: 0.23
Shot count: 6

The key rule: times are cumulative; splits are the differences between cumulative shot times.