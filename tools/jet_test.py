"""Chemical jets (napalm / cryo / rad-waste): stream, spatter, puddles that hurt monsters and players.
python tools/jet_test.py <outdir>"""
import os,sys,random
os.environ["SDL_VIDEODRIVER"]="dummy"; os.environ["SDL_AUDIODRIVER"]="dummy"; os.environ["SKULLS_SAVE"]=os.devnull
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import main, pygame, weapons as WP
from world import Enemy
from assets import to_screen
SP=sys.argv[1]; os.makedirs(SP, exist_ok=True)
g=main.Game(windowed=True); g.save_settings=lambda: None
class B:
    move=(0,0); aim=None; fire=False; pressed=set(); pending=set(); device_name=None; keyboard=True; mouse_mode=False; dev=None
    def poll(s,ps): pass
b=B(); g.inputs=[b]; g.spare={}
main.biome_for=lambda d,s:"facility"; g.chars=["skelebot","canbot"]
out=pygame.Surface((1500,420)); fails=[]
for i,arch in enumerate(("jet_napalm","jet_cryo","jet_rad")):
    g.new_world(2); g.state="play"; g.banner=("",0); w=g.world; p=w.player; w.traps=[]
    L=w.level; cx,cy=int(p.x),int(p.y)
    for x in range(cx-6,cx+8):
        for y in range(cy-5,cy+6): L.solid[L.i(x,y)]=0
    g.floor_layer.chunks.clear(); L.exit=(-50,-50)
    p.weapons[p.cur]=WP.generate(2,random.Random(1),arch=arch,rarity=0)
    e=Enemy("zombie",p.x+3.5,p.y,awake=True,depth=1); e.hp=1e6; w.enemies=[e]
    a,bb=to_screen(1,0); c,d=to_screen(0,0); b.aim=((a-c)*10,(bb-d)*10); b.fire=True
    for f in range(90):
        e.x,e.y,e.vx,e.vy=p.x+3.5,p.y,0,0; g.update(1/60)
    b.fire=False
    pools=[hz for hz in w.hazards if hz[4]=="jet"]
    hp0=p.hp; p.x,p.y=pools[0][0],pools[0][1] if pools else (p.x,p.y)
    for f in range(60): p.invuln=0; g.update(1/60)
    g.draw(); out.blit(pygame.transform.smoothscale(g.screen.subsurface((560,290,800,500)),(500,420)),(i*500,0))
    print("%-11s %s: monster took %.0f, puddles %d (max radius %.2f), player standing in it 1s lost %.1f, frozen=%s" % (arch, WP.ARCH[arch]["label"], 1e6-e.hp, len(pools), max(h[2] for h in pools) if pools else 0, hp0-p.hp, getattr(e,'frozen',0)>0))
    if not (1e6-e.hp>0 and pools and hp0>p.hp): fails.append(arch)
pygame.image.save(out,SP+"/jets.png"); print("FAILED", fails or "none")
