# Skulls & Stuff

An isometric twin-stick shooter about cyborg skeletons, written in Python with pygame-ce.
Every sprite is pre-rendered from procedural Blender models and every sound is synthesized offline.

- Procedural levels across 17 biomes, each with its own enemies, a signature monster, bosses and 2-3 trap types
- Procedural guns (19 archetypes x brands x rarities x mods) and power-ups
- Bosses with multi-phase bullet-hell attack patterns; explosives and bosses breach walls
- Drop-in local co-op for 2 players

## Run

```
pip install pygame-ce numpy scipy
run_game.bat          (or: python game/main.py)
```

Controls: WASD + mouse, or a gamepad (left stick move, right stick aim, RT fire).
Player 2 joins any time by pressing BACK / SELECT on a second controller.

## Rebuild assets

Sprites and audio are committed, so this is only needed after changing the generators.

```
build_assets.bat [names | prefix*] [--quick]   # renders sprites with Blender (edit the Blender path inside)
build_audio.bat                                # synthesizes sfx + music (numpy/scipy)
```

## Layout

- `game/` - the game (world simulation, rendering, weapons, bosses, biomes, traps)
- `blender/` - procedural model builders and the headless render pipeline
- `tools/` - audio synthesis, contact sheets and headless test scripts (`python tools/<name>_test.py <outdir>`)
- `assets/` - rendered sprites + manifest, synthesized audio
