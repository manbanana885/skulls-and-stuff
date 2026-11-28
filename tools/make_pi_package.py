"""Build the Raspberry Pi edition: a self-contained folder (plus a zip of it) to copy to a Pi 4 / 5.

    python tools/make_pi_package.py [outdir]        (default: pi_package/ in the game folder)

What goes in: the game's code, its audio, every sprite at half size (the game then draws at 960 x 540 and
stretches it to the screen - a quarter of the memory and of the drawing work), and the Pi scripts from pi/
(install_pi.sh, run_pi.sh, README_PI.txt) plus a desktop icon. Net play only compares the code, so the Pi
edition plays with PCs running the same version."""
import os
import sys
import json
import shutil
import zipfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "pi_package")
PKG = os.path.join(OUT, "skulls-and-stuff")
SCALE = 0.5


def copy_code():
    dst = os.path.join(PKG, "game")
    os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(os.path.join(ROOT, "game"))):
        if name.endswith(".py"):
            shutil.copy2(os.path.join(ROOT, "game", name), os.path.join(dst, name))


def copy_audio():
    src = os.path.join(ROOT, "assets", "audio")
    dst = os.path.join(PKG, "assets", "audio")
    shutil.copytree(src, dst, dirs_exist_ok=True)


def half_sprites():
    src = os.path.join(ROOT, "assets", "sprites")
    dst = os.path.join(PKG, "assets", "sprites")
    with open(os.path.join(src, "manifest.json")) as fh:
        man = json.load(fh)
    n = 0
    for name in sorted(os.listdir(src)):
        sdir = os.path.join(src, name)
        if not os.path.isdir(sdir):
            continue
        ddir = os.path.join(dst, name)
        os.makedirs(ddir, exist_ok=True)
        for f in sorted(os.listdir(sdir)):
            if not f.endswith(".png"):
                continue
            img = pygame.image.load(os.path.join(sdir, f))
            w, h = img.get_size()
            small = pygame.transform.smoothscale(img.convert_alpha() if pygame.display.get_surface() else img,
                                                 (max(1, round(w * SCALE)), max(1, round(h * SCALE))))
            pygame.image.save(small, os.path.join(ddir, f))
            n += 1
            if n % 500 == 0:
                print("  %d sprites..." % n)
    for name, meta in man.items():                 # pixel sizes and anchors shrink with the images (muzzles are in tiles)
        if name.startswith("_"):
            continue
        if "size" in meta:
            meta["size"] = [max(1, round(v * SCALE)) for v in meta["size"]]
        if "anchor" in meta:
            meta["anchor"] = [v * SCALE for v in meta["anchor"]]
    man.setdefault("_meta", {})["tile_w"] = int(man.get("_meta", {}).get("tile_w", 128) * SCALE)
    with open(os.path.join(dst, "manifest.json"), "w") as fh:
        json.dump(man, fh)
    return n


def pi_files():
    for name in ("install_pi.sh", "run_pi.sh", "README_PI.txt"):
        with open(os.path.join(ROOT, "pi", name), encoding="utf-8") as fh:
            text = fh.read().replace("\r\n", "\n")
        with open(os.path.join(PKG, name), "w", encoding="utf-8", newline="\n") as fh:   # Unix line endings for the Pi
            fh.write(text)
    # desktop icon: the Skelebot's torso on a dark tile
    icon = pygame.Surface((128, 128), pygame.SRCALPHA)
    pygame.draw.rect(icon, (24, 22, 30, 255), icon.get_rect(), border_radius=22)
    try:
        img = pygame.image.load(os.path.join(ROOT, "assets", "sprites", "player_torso", "idle_01_00.png"))
        w, h = img.get_size()
        k = 150 / max(w, h)
        img = pygame.transform.smoothscale(img, (int(w * k), int(h * k)))
        icon.blit(img, img.get_rect(center=(64, 74)))
    except Exception as ex:                                  # an icon is nice to have, not essential
        print("  (no icon: %s)" % ex)
    pygame.image.save(icon, os.path.join(PKG, "icon.png"))


def make_zip():
    path = os.path.join(OUT, "skulls-and-stuff-pi.zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(PKG):
            for f in files:
                full = os.path.join(base, f)
                arc = os.path.relpath(full, OUT).replace(os.sep, "/")
                info = zipfile.ZipInfo.from_file(full, arc)
                if f.endswith(".sh"):
                    info.external_attr = (0o755 << 16)       # executable once unzipped on the Pi
                with open(full, "rb") as fh:
                    z.writestr(info, fh.read(), zipfile.ZIP_DEFLATED)
    return path


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    if os.path.isdir(PKG):
        shutil.rmtree(PKG)
    os.makedirs(PKG)
    print("Building the Raspberry Pi edition in %s" % PKG)
    copy_code()
    print(" code copied")
    copy_audio()
    print(" audio copied")
    n = half_sprites()
    print(" %d sprites at half size" % n)
    pi_files()
    print(" Pi scripts and icon added")
    z = make_zip()
    mb = os.path.getsize(z) / 2 ** 20
    print("Done: %s (%.0f MB). Copy the zip to the Pi and follow README_PI.txt inside it." % (z, mb))


if __name__ == "__main__":
    main()
