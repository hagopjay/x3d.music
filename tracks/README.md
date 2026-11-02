# tracks/

Feature tracks sampled at 60 Hz from the score cards (`loomsong.tracks/1`): beat phase, bar phase, section, harmony index, tension, density, melody contour, register, notes sounding. Exact channels come from the card alone; Texture channels (per-stem loudness, brightness) come from the rendered audio and arrive in P2. Stored uncompressed (int16 little-endian in base64); the page's gzip parts are made from them at build time. Schema in `docs/SCORE-SCHEMA.md`.
