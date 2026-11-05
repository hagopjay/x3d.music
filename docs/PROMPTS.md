# Prompts for the generated media

Everything below is **AI-made**: the videos, the animated pictures and the images. The music is not (it is synthesised in code from the score cards). Every result is labelled AI-made wherever it appears: the title card, the opening and end cards, the corner note and the credits of each piece.

Each prompt is listed with the sha256 of its text exactly as it was sent, so a reader can check the text against the private run log; the **Ledger run** column names the line of that log by id and nothing else (what a call cost is kept privately). The videos are not in this repository (they are over its size limit); the pictures the worlds use are in `art/`, with `art/manifest.json` (file, size, sha256 of the file and of its source, and the switch that says whether a world draws it). The cards are made from the finals by `tools/prep_cards.py` and stay out of the repository.

## Index

| Id | Kind | sha256 of the prompt (first 16) | Label shown with the result | Ledger run | What became of it |
|---|---|---|---|---|---|
| bk1-nave | video, backdrop | `c444f7da9535fcad` | not on the page yet | 0e45a6a74f | Draft kept privately. All 48 sampled frames register (30,251 points, median point error 0.455 px); a CPU dust-splat stand-in is built from it. The photoreal splat world waits for the GPU. |
| bk2-courtyard | video, backdrop | `1d80534039e3ac8e` | not on the page yet | ea4937dcc7 | Draft kept privately. All 48 sampled frames register (20,485 points, median point error 0.379 px); a CPU dust-splat stand-in is built from it. The photoreal splat world waits for the GPU. |
| bk3-hall | video, backdrop | `72cc97f0913210bf` | not on the page yet | 3c5322abe5 | Draft kept privately. All 48 sampled frames register (8,659 points, median point error 0.412 px); a CPU dust-splat stand-in is built from it. The photoreal splat world waits for the GPU. |
| still1-title | video, animated picture | `88f267c5afe9c14d` | AI-made: the moving picture behind the title card | draft a213452d89; final a88344fe94 | Draft kept privately. The 1080p final plays as the page's `title` card (re-encoded for the web; the video is not in this repository). |
| still2-ode-open | video, animated picture | `36cd927b49b1852d` | AI-made: the Ode's opening card | draft cf59a92458; final 3f6f15f99e | Draft kept privately. The 1080p final plays as the page's `ode` card (re-encoded for the web; the video is not in this repository). |
| still3-turca-open | video, animated picture | `f7e7023dfdd7e7ed` | AI-made: the Rondo's opening card | draft 6dcd915ea5; final a3b94e62d6 | Draft kept privately. The 1080p final plays as the page's `turca` card (re-encoded for the web; the video is not in this repository). |
| still4-intermission | video, animated picture | `f7db4370a5c0bd95` | AI-made: the moving picture behind the end card | draft 97ba274dab; final 7efa7cd574 | Draft kept privately. The 1080p final plays as the page's `between` card (re-encoded for the web; the video is not in this repository). |
| still5-credits | video, animated picture | `e3db497112168a57` | not on the page yet | 6c949b0828 | Draft kept privately; no final yet. |
| still6-bumper | video, animated picture | `a4f020366d337a89` | not on the page yet | fb07d13a6d | Draft kept privately; no final yet. |
| motif-A | image, 1:1 | `1a416a69bee785e9` | AI-made: the twelve tile motifs on the dome | 226e01f269 | Used: tile A (1 of 12) of `art/dome-motifs.jpg`, the dome's picture for section A. |
| motif-B | image, 1:1 | `d220ebc2addfcb44` | AI-made: the twelve tile motifs on the dome | fcde682bdf | Used: tile B (2 of 12) of `art/dome-motifs.jpg`, the dome's picture for section B. |
| motif-C | image, 1:1 | `5b673282122d84ad` | AI-made: the twelve tile motifs on the dome | 5e9f7631a6 | Used: tile C (3 of 12) of `art/dome-motifs.jpg`, the dome's picture for section C. |
| motif-D | image, 1:1 | `b57bef578b95e81b` | AI-made: the twelve tile motifs on the dome | 5f587646d8 | Used: tile D (4 of 12) of `art/dome-motifs.jpg`, the dome's picture for section D. |
| motif-E | image, 1:1 | `8844402e3da2141f` | AI-made: the twelve tile motifs on the dome | 94a3895b59 | Used: tile E (5 of 12) of `art/dome-motifs.jpg`, the dome's picture for section E. |
| motif-F | image, 1:1 | `5f0bf53704182418` | AI-made: the twelve tile motifs on the dome | b391fcd1df | Used: tile F (6 of 12) of `art/dome-motifs.jpg`, the dome's picture for section F. |
| motif-G | image, 1:1 | `62503179f855b7d2` | AI-made: the twelve tile motifs on the dome | 168e299972 | Used: tile G (7 of 12) of `art/dome-motifs.jpg`, the dome's picture for section G. |
| motif-H | image, 1:1 | `050aa91205ee556a` | AI-made: the twelve tile motifs on the dome | 8c7b4e21e4 | Used: tile H (8 of 12) of `art/dome-motifs.jpg`, the dome's picture for section H. |
| motif-I | image, 1:1 | `2b68b7a6d06a5f58` | AI-made: the twelve tile motifs on the dome | fd9b0a4dae | Used: tile I (9 of 12) of `art/dome-motifs.jpg`, the dome's picture for section I and its two returns. |
| motif-J | image, 1:1 | `dab949da2ee2453b` | AI-made: the twelve tile motifs on the dome | 96f80d5ee1 | Used: tile J (10 of 12) of `art/dome-motifs.jpg`, the dome's picture for section J. |
| motif-K | image, 1:1 | `f57cd1fdb6b75c20` | AI-made: the twelve tile motifs on the dome | 3906d69146 | Used: tile K (11 of 12) of `art/dome-motifs.jpg`, the dome's hush before the first note. |
| motif-L | image, 1:1 | `6b5c100e43aa2309` | AI-made: the twelve tile motifs on the dome | 609aa636ae | Used: tile L (12 of 12) of `art/dome-motifs.jpg`, the dome opening on the final chord. |
| tapestry-cand-1 | image, 3:4 | `9dd4890eadfe9db8` | AI-made: the tapestry's picture (a generated image, woven by the loom) | b83d2a6cbf | Used: `art/ode-tapestry.png`, woven through the five threads. |
| tapestry-cand-2 | image, 3:4 | `c104349dd1218c5d` | not on the page | 97617f3ad3 | Judged, not chosen; kept privately. |
| tapestry-cand-3 | image, 3:4 | `a19901c58fa47aa5` | not on the page | 7565d5be06 | Judged, not chosen; kept privately. |
| tapestry-cand-4 | image, 3:4 | `37753b45da814bf4` | not on the page | 524533eb79 | Judged, not chosen; kept privately. |
| tapestry-cand-5 | image, 3:4 | `d66fb506ac3db8bb` | not on the page | bf4194029c | Judged, not chosen; kept privately. |
| mat-card-manila | image, 1:1 | `2ca75306c5092365` | not on the page | 8e80d505ee | Made, not used: the surface shows seams when tiled. |
| mat-enamel-brass | image, 1:1 | `fc92b976489ab087` | not on the page | 6ff49b993b | Made, not used: the surface shows seams when tiled. |
| mat-walnut | image, 1:1 | `52d537ed276d9a48` | not on the page | 3a3e397c67 | Made, not used: the surface shows seams when tiled. |

## Backdrop videos (8 seconds, no sound)

### bk1-nave

sha256 `c444f7da9535fcade5f37974d6dd6008afcc5d7c03edb8c4157796e922b8551f`

> Slow, steady dolly forward along the centre aisle of an empty Gothic stone nave. Tall pointed arches, ribbed vaults, rows of plain wooden pews, worn stone flagstones, high clear windows throwing soft patches of white daylight onto the floor and the stone columns. A single continuous shot with one smooth, slow camera move and no cuts. A completely static scene: nothing moves, no people, no animals, no flames, no dust or smoke, no water movement, no flicker. Locked exposure, even natural light, no lens flare, no bloom, no film grain. Sharp focus from front to back, rich real surface texture on every material, very few mirrors and very little glass. Photorealistic, 35 mm lens.

Negative prompt: people, text, logos, lens flare, motion blur, flicker, flames, water ripple, smoke, dust, cuts

### bk2-courtyard

sha256 `1d80534039e3ac8e0eabdbd694a1d718faaf6ea2af41f5842f342f1ac89586b6`

> Slow, smooth orbit around the middle of an empty Ottoman courtyard at dusk, lit by hanging brass lanterns that give a steady warm glow. An arcaded colonnade with pointed arches, panels of Iznik tiles in cobalt blue, turquoise and red, geometric marble floor inlay, a dry octagonal marble fountain basin in the centre. A single continuous shot with one smooth, slow camera move and no cuts. A completely static scene: nothing moves, no people, no animals, no flames, no dust or smoke, no water movement, no flicker. Locked exposure, even natural light, no lens flare, no bloom, no film grain. Sharp focus from front to back, rich real surface texture on every material, very few mirrors and very little glass. Photorealistic, 35 mm lens.

Negative prompt: people, text, logos, lens flare, motion blur, flicker, flames, water ripple, smoke, dust, cuts

### bk3-hall

sha256 `72cc97f0913210bf84f290a83ad5c91c8cee647653129155d8c6f1780490c619`

> Slow, steady push forward across a vast empty hall with a matte black stone floor and a high dark dome whose ceiling is covered in tiny steady points of golden light like stars, tall dark columns receding into the distance. A single continuous shot with one smooth, slow camera move and no cuts. A completely static scene: nothing moves, no people, no animals, no flames, no dust or smoke, no water movement, no flicker. Locked exposure, even natural light, no lens flare, no bloom, no film grain. Sharp focus from front to back, rich real surface texture on every material, very few mirrors and very little glass. Photorealistic, 35 mm lens.

Negative prompt: people, text, logos, lens flare, motion blur, flicker, flames, water ripple, smoke, dust, cuts

## Animated pictures (8 seconds, no sound; each starts from a picture of the style board)

### still1-title

sha256 `88f267c5afe9c14d75f1fe6aad858ef95a4f80e62f32f432231f209b8bf414d0`

> Very slow, smooth push-in across the starlit hall. The loom's glowing threads shimmer and flow upward into the tapestry, the brass pinned barrel turns slowly, the tiny golden points in the dome twinkle gently. One continuous elegant shot.

### still2-ode-open

sha256 `36cd927b49b1852d1eb48aef086fc9cdffdea19cbdd7f240cb7e0daf03bb91ae`

> Slow dolly in toward the Jacquard loom. The single luminous indigo thread runs down from the spool into the loom, the chain of punched cards advances slowly, soft shafts of light drift gently. One continuous shot.

### still3-turca-open

sha256 `f7e7023dfdd7e7ed2d208e82387bd09e6b4e41d6861d2d8353a1258f59fd8bc6`

> The giant brass cylinder turns slowly on its axle, steel pins sweep past the comb and catch glints of light, the camera orbits slowly around it. One continuous shot.

### still4-intermission

sha256 `f7db4370a5c0bd9518e36cd833aad662f958b34d3721eda58bea77075784cb59`

> Luminous threads in four colours spiral slowly together in an infinite dark space, rotating gently around the centre with a soft glow. Hypnotic, slow, one continuous shot.

### still5-credits

sha256 `e3db497112168a57b0bf47596a325dc8a7c2cc066e23dc03e193c14c22fbe542`

> The tall glass helix rotates slowly in darkness, its jewel-like nodes glow softly one after another, the small golden point drifts inside, the camera rises very slowly. One continuous shot.

### still6-bumper

sha256 `a4f020366d337a89166b58371981ace3b65b4be8624e1f4ad6402fe27794d582`

> The constellation turkey raises its baton of light, its nodes pulse softly, threads of light flow from the loom and the machine toward it, slow push-in. One continuous shot.

## Images

Every image prompt ends with the same sentence: *No text, no lettering, no numbers, no logos, no signatures, no real people, no human faces.*

### motif-A (1:1)

sha256 `1a416a69bee785e9d6d5858c991847255c99b58b13a05e3bf247efca2810f5e7`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for theme in A minor of a piece of music: cobalt blue and white, tulips and carnations on curling stems. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-B (1:1)

sha256 `d220ebc2addfcb44e5a41fe9c5211c2162b40b82b0570ab6aaf77f78d4854a20`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for the C major answer of a piece of music: turquoise and coral, saz leaves and palmettes. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-C (1:1)

sha256 `5b673282122d84ad15f62ff9f19fa7a7c7487a17d8dde3f92c7c388a6cf25cf8`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for the Janissary refrain of a piece of music: tomato red, gold and ivory, bold interlocking eight-pointed stars. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-D (1:1)

sha256 `b57bef578b95e81bd595297a120b5108e8556f9c004abdf62c405581b8c96fe8`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for the F sharp minor episode of a piece of music: deep indigo and silver, calm large rosettes on a night-blue ground. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-E (1:1)

sha256 `8844402e3da2141f8e3f0a3c8c3ecdf73784e2187158008c6e7c17749e96e498`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for the running sixteenths of a piece of music: dense interlaced arabesque in cobalt, turquoise and white, full of quick motion. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-F (1:1)

sha256 `5f0bf53704182418cfbbed1ed3614824fea1d61cc286aff9b0d806bb588018ff`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for the refrain returns of a piece of music: red and gold on white, a lattice of stars and hexagons. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-G (1:1)

sha256 `62503179f855b7d25e86e7791922cbedecc5598fe1760fec2aea8b26695e6327`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for the theme returns of a piece of music: cobalt and white with small turquoise buds, a stately repeat. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-H (1:1)

sha256 `050aa91205ee556aca97cb7efea8cbe22b7ee755fe487a153edc8b4b38c60a62`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for the answer returns of a piece of music: coral and turquoise, curling leaves around a central flower. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-I (1:1)

sha256 `2b68b7a6d06a5f58c512385f39d793c58ae071d6cb36d0c40ab6903e6dbe7d9d`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for the refrain, last time of a piece of music: crimson and gold, tight radiating star medallions. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-J (1:1)

sha256 `dab949da2ee2453b5fe0df5975136db30f21f3490cd402a1114eaa2e6e3dbad3`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for the coda in A major of a piece of music: gold, ivory and turquoise, radiant sunburst medallions. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-K (1:1)

sha256 `f57cd1fdb6b75c2042bb07d1e992b6e4632bd736915983a5f226320b33f1fed9`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for an opening hush of a piece of music: pale celadon and white, sparse delicate sprays. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### motif-L (1:1)

sha256 `6b5c100e43aa230944a089381c8b8c4be0303dd7a2101c197716e5a9af30417d`

> A perfectly seamless, tileable square pattern in the style of Iznik ceramic tiles, painted under glaze, for the final chord of a piece of music: gold leaf on deep cobalt, one large many-petalled flower. Flat, top-down, no perspective, no border, the pattern continues evenly past every edge so it tiles without a visible seam, crisp painted lines, subtle glaze craquelure.

### tapestry-cand-1 (3:4)

sha256 `9dd4890eadfe9db8257cdb72247ad5d591ebb6bdaa380c3f013252eb16b067ce`

> A woven tapestry design in five flat inks only: deep indigo, silver, gold, ivory and black. A single spark of golden light rises over a wide rolling landscape of hills and a river at dawn; along the hills a long chain of linked human silhouettes holds hands, shown as dark shapes with no faces and no detail. Portrait composition, flat graphic woven look, bold shapes that read at low resolution.

### tapestry-cand-2 (3:4)

sha256 `c104349dd1218c5d2494fd4a1e4c27a7ca31b2d867fa7fd7a8b2bbe4ef380daf`

> A woven tapestry design in five flat inks only: deep indigo, silver, gold, ivory and black. A great radiant sun-spark above a mountain valley, rays like threads fanning out across the sky; in the valley a line of tiny linked silhouettes joins hands, faceless dark shapes. Portrait composition, flat graphic woven look, bold shapes that read at low resolution.

### tapestry-cand-3 (3:4)

sha256 `a19901c58fa47aa5effb15a16cbba494f859ea65bffa85aaa87f5972507ee977`

> A woven tapestry design in five flat inks only: deep indigo, silver, gold, ivory and black. A night-blue sky of silver stars over low hills; one golden spark falls like a seed into a field where many faceless silhouettes join hands in a wide circle. Portrait composition, flat graphic woven look, bold shapes that read at low resolution.

### tapestry-cand-4 (3:4)

sha256 `37753b45da814bf42b4fde6ecb841b20f41356f0654cb82ec60cc973ecd3d6ca`

> A woven tapestry design in five flat inks only: deep indigo, silver, gold, ivory and black. A stylised sunrise of concentric gold and ivory arcs behind a city skyline of simple towers; below it a ribbon of linked faceless silhouettes winds like a river. Portrait composition, flat graphic woven look, bold shapes that read at low resolution.

### tapestry-cand-5 (3:4)

sha256 `d66fb506ac3db8bb5ea806c89024592a2d538e6b9ead1c6a19703ea61d1fba8a`

> A woven tapestry design in five flat inks only: deep indigo, silver, gold, ivory and black. A tree of life whose branches are golden threads reaching to a spark of light at the top, with a ring of linked faceless silhouettes standing around its roots. Portrait composition, flat graphic woven look, bold shapes that read at low resolution.

### mat-card-manila (1:1)

sha256 `2ca75306c50923652ec1e9f77c99e1ccf630ba9345434b252f9a6a2d26ead931`

> A seamless tileable square texture of aged manila punched-card paper with faint fibres and a soft warm patina. Flat, top-down, even light, no holes, no writing.

### mat-enamel-brass (1:1)

sha256 `fc92b976489ab0878d25160a2e62251766668214ad44b4f9686edc6859f1ee89`

> A seamless tileable square texture of cobalt-blue vitreous enamel over brass with tiny hairline cracks and gold edging lines in a repeating geometric pattern. Flat, top-down, even light.

### mat-walnut (1:1)

sha256 `52d537ed276d9a489c25c82e91d8e34508daed84ab1b8491a6ba609ddf5fb67f`

> A seamless tileable square texture of polished walnut wood grain with warm brown tones and subtle figure. Flat, top-down, even light.

## Rules every video prompt follows

For a backdrop that is going to be rebuilt as a 3D splat scene, the prompt asks for reconstruction, not just beauty (L, from how splat training works):

- a static scene, no people, and nothing that moves on its own: no flicker, no flames, no water ripple;
- one smooth camera move with no cuts (a slow dolly or a slow orbit);
- locked exposure and no lens flare;
- rich surface texture; few mirrors and little glass.

Drafts are made at the lowest resolution to check the move; only a draft that passes its own checks gets a final render. The prompts and the price are shown to the owner before each final paid run.

## Rules every image prompt follows

- No faces and no legible text in generated images (the Truth witness checks).
- Calls are paced at one a minute, never in parallel; a failed call that billed nothing is not retried more than twice.
