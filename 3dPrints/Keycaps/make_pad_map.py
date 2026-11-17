import re
import os
I=os.path.join(os.path.dirname(os.path.abspath(__file__)),'icons')+'/'
def svg(n,s=40):
    t=open(I+n+'.svg').read()
    t=re.sub(r'\s(width|height|class)="[^"]*"','',t)
    return t.replace('<svg',f'<svg fill="#000" width="{s}" height="{s}"',1)
keys=[[("Pause / Play",["play-fill","pause-fill"]),("Next Song",["skip-end-fill"]),("Status Screen",["info-lg"]),("Change Playlist",["music-note-list"])],
[("Attract on/off",["infinity"]),("Random Song",["dice-5-fill"]),("Fill Queue",["list-ul"]),("Clear Queue",["ban-left"])],
[("Change Lighting",["palette-fill"]),("All Songs",["all-text"]),("Oldies",["mic-fill"]),("Christmas",["tree-fill"])],
[("Sleep",["moon-fill"]),("Rebuild Playlist",["gear-fill"]),("Reboot",["arrow-clockwise"]),("Shut Down",["power"])]]
dials=[("Volume","volume-up-fill","Louder","Quieter","Mute"),("Bass","speaker-fill","More bass","Less bass","Bass back to normal"),("Lights","lightbulb-fill","Brighter","Dimmer","Lights on / off")]
g=''
for row in keys:
    for k in row:
        if k is None: g+='<div class="key blank"><span>spare</span></div>'
        else:
            ic=''.join(svg(n,40 if len(k[1])>1 else 52) for n in k[1])
            g+=f'<div class="key"><div class="ic">{ic}</div><div class="lb">{k[0]}</div></div>'
d=''
for name,ic,r,l,p in dials:
    d+=f'''<div class="dial"><div class="knob">{svg(ic,44)}</div><div class="dt"><b>Dial: {name}</b>
<div>&#8635; Turn right: {r}</div><div>&#8634; Turn left: {l}</div><div>&#9660; Push: {p}</div></div></div>'''
html=f'''<!doctype html><html><head><meta charset="utf-8"><style>
@page{{size:letter portrait;margin:0.5in}}
.card{{display:inline-flex;flex-direction:column;border:1.5px dashed #888;padding:18px 20px}}
body{{font-family:Arial,Helvetica,sans-serif;color:#000;background:#fff;margin:0}}
h1{{font-size:32px;margin:0 0 4px}} .sub{{font-weight:700;font-size:18px!important;color:#000;font-size:13px;margin-bottom:18px}}
.wrap{{display:flex;gap:40px;align-items:flex-start}}
.grid{{display:grid;grid-template-columns:repeat(4,140px);gap:10px}}
.key{{height:140px;border:3.5px solid #000;border-radius:10px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:6px;box-sizing:border-box}}
.key .ic{{display:flex;gap:4px;margin-bottom:8px}} .lb{{font-size:21px;font-weight:900;line-height:1.2}}
.blank{{border:2.5px dashed #555;color:#555;font-size:16px}}
.dials{{display:flex;flex-direction:column;gap:26px;padding-top:4px}}
.dial{{display:flex;gap:16px;align-items:center}}
.knob{{width:100px;height:100px;border:3.5px solid #000;border-radius:50%;display:flex;align-items:center;justify-content:center;flex:none}}
.dt{{font-size:22px;font-weight:700;line-height:1.6}} .dt b{{font-size:24px}}
.foot{{width:0;min-width:100%;margin-top:22px;line-height:1.35;font-weight:700;font-size:19px;color:#000}}
</style></head><body><div class="card"><h1>Jukebox control pad</h1><div class="sub">Seeburg Firestar &middot; 16 keys and 3 dials, laid out as on the pad</div>
<div class="wrap"><div class="grid">{g}</div><div class="dials">{d}</div></div>
<div class="foot">Bottom row (Sleep, Rebuild Playlist, Reboot, Shut Down): press twice within 3 seconds (a guard against bumps). Rebuild Playlist rescans the music, then restarts the jukebox. Wait for Shut Down to finish before switching the power off. All Songs, Oldies, Christmas: jump to that playlist. Status Screen shows the jukebox settings on the main screen for 30 s (press again to close); the same page is at http://jukebox.local.</div></div>
</body></html>'''
open('pad_map.html','w').write(html)
# Same card with the dials under the keys, for the full-size page.
open('pad_map_stacked.html','w').write(html.replace('.wrap{{display:flex;'.replace('{{','{'), '.wrap{flex-direction:column;display:flex;'))
