# Seeburg USC2 Firestar: monitor mount and volume control

## What's already in the cabinet

- **Cabinet:** about 50" H x 41" W x 29.5" D, ~200 lb ([1stDibs USC2 listing](https://www.1stdibs.com/furniture/more-furniture-collectibles/collectibles-curiosities/musical-instruments/vintage-1971-seeburg-jukebox-usc2-bandshell-firestarter/id-f_21449032)). Width is not a problem for a 34" ultrawide; the depth of the glass opening is the number to measure.
- **Amplifier:** TSA-series (a 1972 USC2 owner reports a **TSA10** plus DCC1, [AudioKarma](https://audiokarma.org/forums/threads/seeburg-jukebox-1972-usc2.1038435/)). Check the tag on yours.
- **Volume control (stock, no longer used):** The TSA10 era uses a **VC1** volume control: a pot in a housing on a ~3 ft shielded cable off the amp, so it can sit anywhere in the cabinet. The VC1 also carries the pickup audio from the mechanism to the amp. An optional **PRVC** (Powered Remote Volume Control) motor bolts on the back and turns the same pot from a remote box ([Seeburg history: PRVC](https://seeburghistory.jukeboxhistory.info/prvc.html), [jukebox-world PRVC FAQ](http://www.jukebox-world.de/Forum/Archiv/FAQ-Seeburg/PRVC.htm)). The exact pot value for the VC1 isn't published online that I found (the later VC3 is 25 kOhm); confirm from the [USC2 manual](https://www.jukeboxmanuals.com/store/p988/Seeburg_USC2_PRINT.html) or a meter.

## 34" ultrawide under the glass

**Measure first:** the visible glass opening (width x front-to-back) and the clearance from the glass down to the mechanism/title-rack.

A 34" 21:9 panel's picture area is about **31.3" x 13.4"**; with bezels most are **~32" x 14.5"**, and 2-3" deep at the VESA mount without a stand. If the opening is narrower than ~13.5" front to back, a 34" will lose picture under the trim and a 29"/30" 21:9 (or a stretched-bar panel) fits better.

1. **Buy a flat panel, not a curved one.** A 1800R curve on a 34" puts the edges ~1.5" off a flat glass, which looks wrong and wastes depth. Flat 34" ultrawides exist (often 2560x1080; flat 3440x1440 is rarer), so check the spec sheet for "flat". Pick **IPS** (not VA): under flat glass you view it at a steep angle, and VA washes out off-axis.
2. **Mount it to the cabinet, never to the glass.** Make a frame (3/4" plywood or 1" aluminium angle) that spans the cabinet sides or bolts to the old title-strip rack mounting points, and fix the monitor to it by its VESA holes with threaded rod/standoffs so you can fine-tune height. Leave a **1/8"-1/4" air gap** between screen and glass so the glass never presses on the panel.
3. **Mask the bezel.** Cut a matte-black mask (mat board, black acrylic or vinyl on the underside of the glass) with a window the size of the picture area. It hides the bezel and the cabinet innards.
4. **Glare:** clear glass over a screen reflects badly. Matte-finish panels help; if it's still bad, replace the top with **anti-reflective (museum) glass** cut to the same size.
5. **Heat:** a 34" monitor dissipates ~30-50 W, and the Pi 5 and amp add more in a closed box. Keep the monitor's rear vents clear and add a quiet 120 mm fan pulling air out of the back panel.
6. **Power:** feed the monitor, Pi and amp from one strip on the jukebox's own switched mains so the cabinet switch powers everything. Most monitors remember their power state and come on by themselves when mains returns; check that setting in the OSD.
7. **Orientation:** if the panel has to go in upside down to suit the cable side, rotate it in software on the Pi (that ties in with the skin work in the code thread).

## Volume control (updated: NAD amp + InnoMaker HiFi DAC HAT, stock electronics retired)

Signal path: **Pi 5 -> InnoMaker HiFi DAC HAT (PCM5122, RCA out, 2.1 Vrms) -> NAD line input -> speakers.** No pot sits in the audio path.

**Decided (2026-10-08): the stock Seeburg volume knob is not used.** Its location in the cabinet is unknown and may be awkward. Volume comes from the **knob on the Koolertron 4-key macro pad** in the glass button bar, which plugs straight into the Pi as a USB keyboard.

1. In Koolertron's setup program on your Windows PC (pad plugged into the PC), set the knob to type these keys:
   - Turn clockwise: `=` (Fruitbox `VolUp`)
   - Turn anticlockwise: `-` (Fruitbox `VolDown`)
   - Press the knob: `Left Ctrl` (Fruitbox `Mute`)
   The settings are saved in the pad, so it keeps them when you move it to the Pi.
2. Fruitbox already listens for those keys (`fruitbox/fruitbox.ini`: `VolUp = KBD0 =`, `VolDown = KBD0 -`, `Mute = KBD0 Left Ctrl`). Each click moves the volume by `SongVolumeStep` (set to 5, so 20 clicks from silent to full), and the volume starts at `SongVolume = 30` after each boot.
3. Set the DAC to a fixed level once and leave it (`alsamixer`, press F6, pick the HiFi DAC, set `Digital` to about 90%, then `sudo alsactl store` so it sticks). Set the NAD's own knob so full Fruitbox volume is as loud as you'd ever want.

Bonus: Fruitbox's on-screen volume bar follows the knob, because Fruitbox itself does the volume.

The older plan (the stock pot wired to the Teensy, read by the Pi) is retired.

**Simplest fallback (no software):** use the NAD's own volume knob, or a 10 kOhm dual-gang log pot between the DAC's RCA out and the NAD. Use shielded cable and ground the shield at the NAD end only.

## Measurements to send back

- Glass opening width and front-to-back depth
- Clearance under the glass at front and back
- Which NAD model
