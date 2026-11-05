# Embout d'aspirateur Ø32 : version à lèvre Coanda + version témoin à bord vif, mêmes dimensions.
# Imprimer les deux et comparer (même aspirateur, même distance) pour isoler l'effet de la lèvre.
# Unités : mm. Usage : python3 coanda.py -> coanda_embout.stl + temoin_embout.stl
import numpy as np, trimesh

D_TUBE = 32.0   # Ø extérieur du tube/flexible sur lequel l'embout s'emmanche
JEU = 0.3       # jeu d'emmanchement (à ajuster selon l'imprimante)
EP = 2.4        # épaisseur de paroi
L = 60.0        # longueur droite (dont ~40 mm d'emmanchement)
R = 12.0        # rayon de la lèvre Coanda (plus grand = écoulement plus "collé")

ri = (D_TUBE + JEU) / 2   # rayon intérieur
ro = ri + EP              # rayon extérieur

def arc(cx, cz, r, a0, a1, n=48):
    a = np.radians(np.linspace(a0, a1, n))
    return np.c_[cx + r * np.cos(a), cz + r * np.sin(a)]

def coanda():
    # paroi intérieure, puis lèvre torique qui s'enroule vers l'extérieur (surface convexe = surface Coanda)
    c = (ri + R, L)
    return np.vstack([[ri, 0], [ri, L],
                      arc(*c, R, 180, 0),            # face aérodynamique de la lèvre
                      arc(*c, R - EP, 0, 180)[1:],    # face interne de la lèvre, retour jusqu'à r = ro
                      [ro, 0], [ri, 0]])

def temoin():
    # même hauteur totale, bord droit et vif
    return np.array([[ri, 0], [ri, L + R], [ro, L + R], [ro, 0], [ri, 0]])

for name, prof in (("coanda_embout", coanda()), ("temoin_embout", temoin())):
    m = trimesh.creation.revolve(prof, sections=128)
    m.merge_vertices()
    if m.volume < 0: m.invert()  # profil parcouru dans le sens horaire
    assert m.is_watertight and m.volume > 0, name
    m.export(f"{name}.stl")
    print(name, "Ø ext max %.1f mm, hauteur %.1f mm, volume %.1f cm3" % (
        2 * m.bounds[1][0], m.bounds[1][2], m.volume / 1000))
