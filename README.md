# Skulls & Stuff

An isometric twin-stick shooter about cyborg skeletons, written in Python with pygame-ce.
Every sprite is pre-rendered from procedural Blender models and every sound is synthesized offline.

- Procedural levels across 17 biomes, each with its own enemies, a signature monster, bosses and 2-3 trap types
- Every room starts with a group that fits its biome, and rooms fill up the deeper you go: shooters hang back
  from the doorways, brawlers hold the middle, swarms bunch up and ambushers lurk by the walls. Now and then a
  room is built round a spawning station that keeps breeding until you shoot it: a rotting carcass (maggots,
  leeches, roaches), a grave (the risen dead), a vat (pink melters and lab mutants), a fabricator (robots), a
  hell-gate (demons) or a nest (spiders, snakes, scorpions). Rooms you haven't cleared slowly restock while
  you're far away
- Procedural guns (30+ archetypes x brands x rarities x mods) and power-ups, including heavy weapons
  (chaingun, railgun, barrage missile launcher, storm coil) that slow you down but hit much harder, a cluster
  bomb launcher and chemical jets (napalm / cryo / rad-waste) that leave hazardous puddles
- 23 manufacturers and eleven rarity tiers, up to Mythical, Demonic, Eldritch and Sacred guns with their own
  effects (run `run_loot_test.bat` to get only the six rarest tiers). Eldritch guns favour double / triple shots,
  homing and radioactive or corrosive spatter
- Of the Void, the rarest tier: revolvers, grenade launchers and tactical nukes whose every impact opens a black
  hole that drags monsters (and you) in from 4-6 tiles, then collapses and explodes. One in five Void tactical
  nukes is DOOM, DOOOOM?: a far bigger hole, then a reactor-sized blast that destroys everything in it
- Demonic, Eldritch, Sacred and Void rounds fly in their tier's colours; Sacred rounds shed sparkles and Demonic
  rounds embers. Some Sacred guns smite what they hit with a pillar of light or a lightning strike, and some
  Demonic guns with a pillar of hellfire
- Chaos: every shot from a Chaos gun takes a different damage type from the last, with that type's side effect
- Modules with rolled stats, 4 equipped (one per D-pad direction) plus an 8-slot backpack, managed from the
  pause menu: buzzsaw orbiter, arc shield, forward shield, rear guard, medbot, gun drone, jump jets, decoys,
  grenades (shrapnel, hex, nuke, incendiary, cryo, corrosive), carryable barrels and more
- 17 module makers, each leaning its modules' power, speed, reach, recharge or stamina
- Forward shields face where you aim and rear guards cover your back; both stop shots *and* claws from their
  side (explosions still get through)
- Bosses with multi-phase bullet-hell attack patterns; explosives and bosses breach walls. The Ocularch, a
  floating eye ringed with eyestalks, fires scorching, freezing, venom, charm and death rays and spits plasma
- Pink Heavies (rare early, common from about sector 5) lug a real chaingun, railgun, barrage launcher or
  tactical nuke, and sometimes drop it
- Vermin: vipers and spitting cobras that coil and strike with poison, armoured scorpions with a telegraphed
  venom sting, and packs of giant cockroaches that dodge your aim and shrug off radiation
- Fire demons: fireball-throwing imps, fire-breathing pit demons and devils that hurl hellfire and blink away;
  burning and poison now tick on you until they wear off
- Damage types (Kinetic, Explosive, Fire, Chemical, Cryo, Radiation, Electrical) against enemy categories
  (Undead, Robot, Demon, Construct, Mutant): bring the right gun. Kinetic guns can roll Penetrating Core or
  Expanding rounds; optional colour-coded damage numbers (Settings, or Q / Y on the pause screen)
- Three playable bodies, picked on the Local Play page: Skelebot (undead, balanced), CanBot (robot drum on tank
  treads, +20% integrity / -20% speed) and Super Mutant (mutant, +20% speed / -20% integrity)
- Deployable MG and mortar turret modules (F / B) that draw monsters, take damage, and go up like a tactical nuke
- Explosive barrels in four kinds: red (fire + burning ground), green (toxic gas + acid), yellow (radiation
  fallout) and orange (shrapnel) - they hurt monsters and you alike, and chain off each other. Pick one up
  with E / A and put it down somewhere better
- Drop-in local co-op for 2 players, and net play for up to 4 across Windows, Mac and Linux
- Every launch opens on a new, randomly written escape story: you're a facility's experiment that woke up and
  wants out (who built you, what you are, who's hunting you all change). The menus sit over real generated
  sectors, shown like a security-camera feed that cuts to a new biome every few seconds

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

## How to play (Mac and Linux)

1. **Download and unzip the game** (green **Code** button, then **Download ZIP**).
2. **Run the setup once.**
   - **Mac:** double-click **`install.command`**. If macOS says it's from an unidentified developer,
     right-click it, choose **Open**, then **Open** again.
   - **Linux:** in a terminal in the game folder, run `bash install.sh`.

   It needs Python 3.10 or newer. If you don't have it, the setup tells you where to get it. On a Mac,
   use the installer from [python.org/downloads](https://www.python.org/downloads/). The setup keeps the
   game's libraries in a `.venv` folder inside the game folder, so nothing else on your computer changes.
3. **Play.** Double-click **`run_game.command`** (Mac), or run `bash run_game.sh` (Linux).

## Raspberry Pi 4 / 5

The Pi gets its own edition, with half-size sprites so it fits in memory and runs smoothly. On a Windows,
Mac or Linux computer that has this game folder, run `python tools/make_pi_package.py`. It builds
`pi_package/skulls-and-stuff-pi.zip`. Copy that zip to the Pi and follow `README_PI.txt` inside it: extract it,
run `bash install_pi.sh` once, then start the game from the desktop icon. A Pi edition built from the same
copy of the game can join net games with PC players (`tools/crossplay_test.py` checks this: a PC host and a
Pi-edition guest in one game).

### Running it yourself (any OS)

You need Python 3.10 or newer.

```
pip install pygame-ce numpy
python game/main.py
```

If you already have the regular `pygame` package installed, uninstall it first (`pip uninstall pygame`).
It clashes with `pygame-ce`.

## Controls

WASD + mouse, or a gamepad (left stick move, right stick aim, RT fire). Q / Y swaps guns, SHIFT / LB dashes
(with Jump Jets equipped). Aiming with the mouse shows a red crosshair; it (and the normal pointer on menus)
hides after 5 seconds without mouse movement.

- **Menus:** the main menu has **Local Play** (pick your body, 2-player co-op), **Online Play** (host or join a
  net game) and **Settings**. UP / DOWN choose, ENTER / A select, ESC / B back; the mouse works too.
- **Settings:** demand mode, damage numbers, sound and music volume, fullscreen, and whether the story plays at
  startup ("Tell me a new story" plays a fresh one any time). Everything is saved as you change it.
- **Demand mode (Settings)** steps HIGH / MID / LOW. Lower modes put fewer monsters on the
  map to go easy on slower machines, and make up for it: MID has about 3/4 of the monsters with 1.4x health,
  LOW about half with 2x health, and both make them quicker and more aggressive. Lower modes also spawn fewer
  particles and gibs, and LOW draws with half-size sprites at 960 x 540, stretched to fill the screen (about a
  third of the drawing work; switching to or from LOW changes the sprites at the next launch). A Raspberry Pi starts on LOW, a PC on HIGH. In a net game the whole session runs at the lowest
  mode anyone in it has (the lobby shows everyone's), so a Pi joining a PC game isn't buried in monsters.

- **Pick up: E, or the bottom face button** (A on Xbox, B on a SNES-style pad). Takes whatever you're next to
  and facing: a gun, a module, a barrel, or your own deployed turret. A turret packs into the selected D-pad
  slot, which has to be empty.
- **Select a module slot: the D-pad, or keys 1-4.**
- **Use the selected module: F, or the right face button** (B on Xbox, A on a SNES-style pad), **or RB.**
  Throws a grenade, deploys a turret, puts a barrel down, and so on. It never picks anything up.

ENTER / START pauses: the pause screen shows your two guns (E / A takes the
highlighted one in hand) and your modules (arrows / D-pad to move, E / A to equip or unequip, R / X to drop).
Player 2 joins any time by pressing BACK / SELECT on a second controller, then picks a body with LEFT / RIGHT
and confirms with A / START (B / BACK backs out). The game waits while they choose.

## Net play (up to 4 players)

Everyone needs the **same version** of the game. The easiest way is for everyone to download it from the
same place at the same time. Windows, Mac and Linux players can play together.

**Hosting:** on the main menu, choose **ONLINE PLAY**, then **HOST NET GAME**. The lobby shows your **game name** (a random
one like `grim-otter-47`) and your address (for example `192.168.1.20`). The game name is the password, so
only give it to the people you want in. Press TAB to type your own game name, or Y / Q for a new random one. Press **N** to set **your player
name**: it's shown over your head and in everyone's lobby.
Pick your body, wait for friends to show up, then press START / A to begin. Friends can also drop into a
game that's already running.

**Joining:** choose **ONLINE PLAY**, then **JOIN NET GAME**.
- **Same network** (same Wi-Fi or router): the host's game appears in the list. Pick it and press A / ENTER.
- **Over the internet:** type the host's address. The easiest and safest way is **Tailscale** (free):
  1. Everyone installs it from [tailscale.com/download](https://tailscale.com/download) and signs in (a Google or
     Microsoft account works). Press **F1** on the host or join screen to open that page.
  2. The host shares their PC: open [the Tailscale admin page](https://login.tailscale.com/admin/machines), click
     **...** next to your PC, choose **Share...**, and send the link to your friends. They open it and accept.
  3. The host's lobby shows a **TAILSCALE** address (it starts with `100.`). Read that and the game name out to
     your friends.

  If it won't connect, allow Python through Windows Firewall on **Public** networks too: search the Start menu
  for "Allow an app through Windows Firewall", find Python, and tick both boxes.

  Without Tailscale, the host can forward **TCP port 47777** on their router to their PC, and give friends
  the **INTERNET** address from the lobby (the game gets it from the router or from ipify.org). This doesn't work on some internet connections (CGNAT). Remove
  the forward when you're done playing.

Then type the **game name** the host gave you; capitals, spaces and dashes don't matter. Put your own
name in **YOUR NAME** if you like. Pick a body with
LEFT / RIGHT and press A when you're ready.

**Safety:** the game name never crosses the network. Your game proves it knows the name instead. Five wrong
names from one address lock that address out for a minute. Guests can only send controls, never files or
code, and anyone who floods the host or sends garbage is kicked. Tailscale / ZeroTier is still the safest
way to play over the internet. If you forward a port, turn it off when you're not playing. Only join hosts
you know.

**The first time you host or join**, Windows or macOS may ask whether Python can use the network.
Click **Allow** (on Windows, tick **Private networks**). Otherwise the game isn't visible to others.

In a net game everyone has their own screen and camera, and the co-op leash is off. START / ENTER opens
your menu (inventory), but the game keeps running for everyone while it's open. ESC leaves the net game.
If the host leaves, the game ends for everyone. The host runs the game, so the host's computer and
connection matter most. Each guest uses about 30-60 KB/s.

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
