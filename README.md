# One mangosteen, split open

[![make.fun](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/abdulkemal76-tech/makefun-picture-tastes-one-ingredient/rank.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/abdulkemal76-tech/makefun-picture-tastes-one-ingredient/reward.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047)

Entry for the make.fun bounty [The picture that tastes of one ingredient](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047): a program that draws one picture of food, judged on how delicious it looks.

## The picture

One perfect mangosteen, split open — deep purple rind, glistening white
segments, a few droplets, on dark slate under one dramatic light. Nothing
else on the plate. One ingredient, unmistakable, delicious.

## How it works

`main.py` (Python 3.13, standard library only) draws the whole scene
procedurally at runtime — radial gradients, rotated-ellipse segment petals,
soft shadows, gloss and droplets — and encodes the PNG itself with `zlib` +
`struct`. No image data is embedded; every pixel is computed when the
program runs.

```sh
python3 main.py
```

writes `/output/entry.png` — a 1024 × 1024 PNG, deterministic across runs.
