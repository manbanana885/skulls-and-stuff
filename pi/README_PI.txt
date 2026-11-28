SKULLS & STUFF ON A RASPBERRY PI
===============================

This is the Raspberry Pi edition: the same game, with half-size sprites so it fits in a Pi's memory and
runs smoothly. It draws at 960 x 540 and stretches that to fill your screen.

You need
  - a Raspberry Pi 4 or 5. A Pi 4 with 4 GB of memory or more is best; 2 GB works if nothing else is open.
  - the current Raspberry Pi OS, 64-bit (from Raspberry Pi Imager). Older versions don't have a new enough Python.
  - an internet connection the first time, to download the game's libraries.
  - a keyboard and mouse, or a USB / Bluetooth game controller.

Set it up (once)
  1. Copy  skulls-and-stuff-pi.zip  to the Pi (a USB stick works) and put it in your home folder.
  2. Right-click it and choose "Extract Here". You get a folder called  skulls-and-stuff.
  3. Open a terminal (the black icon at the top of the screen) and type:
         bash ~/skulls-and-stuff/install_pi.sh
     and press Enter. It takes a few minutes. When it says "All done!", press Enter.

Play
  - Double-click the Skulls & Stuff icon on the desktop. If the Pi asks how to open it, choose "Execute".
  - It's also in the applications menu under Games, or run:   bash ~/skulls-and-stuff/run_pi.sh
  - It starts full-screen. Press F11 to switch to a window (it can be resized), and F11 again to go back.
  - If it doesn't start from the icon, run it from a terminal (above) to see why. The last error is also
    saved in  skulls-and-stuff/last_error.txt.

Net play
  The Pi can host or join net games with Windows, Mac and Linux players, as long as everyone has the
  same version of the game. Build this Pi package from the same copy of the game your friends have.

If it runs slowly
  - Close the web browser and anything else that's open.
  - Deep sectors have hundreds of monsters. A Pi 4 copes, but it's the hardest part for it.
  - Make sure the Pi isn't overheating: a case with a fan or a heatsink helps a Pi 4 keep its full speed.
