# USB socket bushing (31.5 mm back-panel hole)

Lets the panel-mount USB-A socket (25.5 mm flange, ~21.7 mm threaded body, hex nut)
go through the 31.5 mm round hole in the jukebox back panel. The socket's flange is
smaller than the hole, so this stepped bushing fills the hole. No cover plate needed.

![preview](preview.png)

## Print (Bambu P1S)
- `usb_socket_bushing_and_washer.stl` (both parts on one plate), PETG or PLA, 0.2 mm layers,
  100% infill (they are small and get clamped), no supports. Bushing prints lip face down.
- Single parts: `usb_socket_bushing.stl`, `usb_socket_washer.stl`.

## Fit
1. Push the bushing into the hole from the **outside** (lip on the outside).
2. Push the USB socket through the bushing from the outside.
3. On the inside, slide the washer over the thread, then the socket's nut. Tighten.

The plug is 0.2 mm shorter than the 2 mm panel, so the nut clamps the panel between
the lip and the washer.

## Sizes (usb_socket_bushing.scad)
| | mm |
|---|---|
| Plug (into hole) | 31.3 dia x 1.8 (FIT 0.1 per side, like the power inlet lip) |
| Bore | 22.3 |
| Outside lip | 40 dia x 2 |
| Washer | 40 dia x 1.6 |

If the plug is loose, set `FIT = 0`; if the socket thread binds, raise `BORE_D`.
If the panel is thicker than 2 mm, set `PANEL_T`. `make_stl.py` rebuilds the STLs
(OpenSCAD can also export them from the .scad).
