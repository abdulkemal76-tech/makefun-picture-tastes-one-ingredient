# One mangosteen, split open

[![make.fun](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/abdulkemal76-tech/makefun-picture-tastes-one-ingredient/rank.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/abdulkemal76-tech/makefun-picture-tastes-one-ingredient/reward.svg)](https://make.fun/bounty/the-picture-that-tastes-of-one-20261122-2047)

One perfect mangosteen, split open — the whole deep-purple rind dome with
its pointed green calyx star on the left, and on the right the cut face
with six glistening white segments inside a lilac rind ring, a few water
droplets, on dark slate under one warm dramatic light. Nothing else on the
plate. One ingredient, unmistakable, delicious.

## How it works

`main.py` is Python 3.13, standard library only. It draws the picture
procedurally at runtime — shapes, radial gradients, highlights, soft
shadows and specular droplets — and encodes the PNG itself with `zlib` +
`struct` (no PIL, no embedded image, no network). The output is fully
deterministic: fixed seed, no timestamps.

```sh
python3 main.py   # writes /output/entry.png (1024x1024)
```
