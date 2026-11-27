# Skulls & Stuff

An isometric twin-stick shooter about cyborg skeletons, written in Python with pygame-ce.
Every sprite is pre-rendered from procedural Blender models and every sound is synthesized offline.

- Procedural levels across 17 biomes, each with its own enemies, a signature monster, bosses and 2-3 trap types
- Procedural guns (30+ archetypes x brands x rarities x mods) and power-ups, including heavy weapons
  (chaingun, railgun, barrage missile launcher, storm coil) that slow you down but hit much harder, a cluster
  bomb launcher and chemical jets (napalm / cryo / rad-waste) that leave hazardous puddles
- 21 manufacturers and nine rarity tiers, up to Mythical, Demonic, Eldritch and Sacred guns with their own
  effects (run `run_loot_test.bat` to get only those four tiers)
- Modules with rolled stats, 4 equipped (one per D-pad direction) plus an 8-slot backpack, managed from the
  pause menu: buzzsaw orbiter, arc shield, medbot, gun drone, jump jets, decoys, grenades (shrapnel, hex,
  nuke, incendiary, cryo, corrosive), carryable barrels and more
- Bosses with multi-phase bullet-hell attack patterns; explosives and bosses breach walls
- Damage types (Kinetic, Explosive, Fire, Chemical, Cryo, Radiation, Electrical) against enemy categories
  (Undead, Robot, Demon, Construct, Mutant): bring the right gun. Kinetic guns can roll Penetrating Core or
  Expanding rounds; optional colour-coded damage numbers ([Q / Y] on the title or pause screen)
- Three playable bodies, picked on the title screen: Skelebot (undead, balanced), CanBot (robot drum on tank
  treads, +20% integrity / -20% speed) and Super Mutant (mutant, +20% speed / -20% integrity)
- Deployable MG and mortar turret modules (F / B) that draw monsters, take damage, and go up like a tactical nuke
- Explosive barrels in four kinds: red (fire + burning ground), green (toxic gas + acid), yellow (radiation
  fallout) and orange (shrapnel) - they hurt monsters and you alike, and chain off each other. Pick one up
  with F / B and put it down somewhere better
- Drop-in local co-op for 2 players

## How to play (Windows, no Python experience needed)

1. **Download the game.** Near the top of this page, click the green **Code** button,
   then **Download ZIP**.
2. **Unzip it.** Open your Downloads folder, right-click `skulls-and-stuff-main.zip`
   and choose **Extract All...**, then **Extract**.
3. **Run the setup once.** In the extracted folder, double-click **`install.bat`**.
   - If Windows shows a blue "Windows protected your PC" box, click **More info**, then **Run anyway**.
   - If you don't have Python yet, the setup installs it for you. When it's finished, it asks you to
     close the window and double-click `install.bat` a second time to finish.
   - When it says **All done!**, press any key to close it.
4. **Play.** Double-click **`run_game.bat`**. You only need this step from now on.

**If the automatic Python install fails**, get Python from
[python.org/downloads](https://www.python.org/downloads/). On the installer's first screen, tick
**"Add python.exe to PATH"** before clicking Install. Then double-click `install.bat` again.

**If it says "No module named pygame"**, double-click `install.bat` again.

### Running it yourself (any OS)

You need Python 3.10 or newer.

```
pip install pygame-ce numpy
python game/main.py
```

If you already have the regular `pygame` package installed, uninstall it first (`pip uninstall pygame`).
It clashes with `pygame-ce`.

## Controls

WASD + mouse, or a gamepad (left stick move, right stick aim, RT fire). E / A picks things up, Q / Y swaps guns,
SHIFT / LB dashes (with Jump Jets equipped). The D-pad (or keys 1-4) selects a module slot, and F / B uses
the selected module (throw a grenade, deploy a turret, put a barrel down). F / B also packs up your turret
when you stand next to it, and picks up a barrel you're standing next to. ENTER / START pauses: the pause screen shows your two guns (E / A takes the
highlighted one in hand) and your modules (arrows / D-pad to move, E / A to equip or unequip, R / X to drop).
Player 2 joins any time by pressing BACK / SELECT on a second controller.

## Rebuild assets

Sprites and audio are committed, so this is only needed after changing the generators.

```
build_assets.bat [names | prefix*] [--quick]   # renders sprites with Blender (edit the Blender path inside)
build_audio.bat                                # synthesizes sfx + the soundtrack (numpy/scipy/soundfile)
```

## Layout

- `game/` - the game (world simulation, rendering, weapons, bosses, biomes, traps)
- `blender/` - procedural model builders and the headless render pipeline
- `tools/` - audio synthesis, contact sheets and headless test scripts (`python tools/<name>_test.py <outdir>`)
- `assets/` - rendered sprites + manifest, synthesized audio
