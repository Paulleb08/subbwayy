# Embouts d'aspirateur Ø32 pour tester des effets aérodynamiques, avec un témoin à bord vif.
# Tous s'emmanchent pareil (40 mm sur tube Ø32 ext) -> on compare à aspirateur et distance identiques.
# Unités : mm. Usage : python3 embouts.py -> un .stl par embout dans ce dossier.
# Dépendances : pip install trimesh manifold3d scipy
import numpy as np, trimesh
from trimesh.transformations import rotation_matrix as R, translation_matrix as T

D_TUBE = 32.0   # Ø extérieur du tube/flexible sur lequel l'embout s'emmanche
JEU = 0.3       # jeu d'emmanchement (à ajuster selon l'imprimante)
EP = 2.4        # épaisseur de paroi
L = 60.0        # longueur droite des embouts Coanda/témoin (dont ~40 mm d'emmanchement)
SOCKET = 40.0   # longueur d'emmanchement
ri = (D_TUBE + JEU) / 2
ro = ri + EP

def arc(cx, cz, r, a0, a1, n=48):
    a = np.radians(np.linspace(a0, a1, n))
    return np.c_[cx + r * np.cos(a), cz + r * np.sin(a)]

def revolve(prof):
    m = trimesh.creation.revolve(np.vstack([prof, prof[:1]]), sections=128)
    m.merge_vertices()
    if m.volume < 0: m.invert()  # profil parcouru dans le sens horaire
    return m

def shell(inner):
    """Coque de révolution à partir de la surface intérieure [(r, z), ...] (z croissant), paroi EP vers l'extérieur."""
    inner = np.asarray(inner, float)
    return revolve(np.vstack([inner, (inner + [EP, 0])[::-1]]))

def bar(r0, r1, z, w=2.0, h=4.0, angle=0.0):
    """Entretoise radiale de r0 à r1 à la hauteur z."""
    b = trimesh.creation.box((r1 - r0, w, h))
    b.apply_transform(T([(r0 + r1) / 2, 0, z]))
    b.apply_transform(R(np.radians(angle), [0, 0, 1]))
    return b

def tube(r, h, z0=0.0):
    return trimesh.creation.cylinder(radius=r, height=h, sections=64, transform=T([0, 0, z0 + h / 2]))

# --- Témoin : tube droit à bord vif ---------------------------------------------------------
def temoin():
    return shell([[ri, 0], [ri, L + 12]])

# --- Coanda : lèvre torique convexe qui s'enroule vers l'extérieur ----------------------------
def coanda(Rl=12.0):
    c = (ri + Rl, L)
    return revolve(np.vstack([[ri, 0], [ri, L], arc(*c, Rl, 180, 0), arc(*c, Rl - EP, 0, 180)[1:], [ro, 0]]))

# --- Venturi : convergent -> col -> divergent, prise de pression au col ----------------------
def venturi(r_entree=22.0, r_col=9.0, l_conv=20.0, l_col=8.0, l_div=45.0):
    z1 = SOCKET; z2 = z1 + l_div; z3 = z2 + l_col; z4 = z3 + l_conv  # z croissant = vers l'entrée d'air
    body = shell([[ri, 0], [ri, z1], [r_col, z2], [r_col, z3], [r_entree, z4]])
    zc = (z2 + z3) / 2
    # embout Ø5 pour tuyau silicone Ø3-4 int. -> manomètre / tube en U ; boucher pour l'essai d'aspiration
    nip = trimesh.creation.cylinder(radius=2.5, height=14, sections=32)
    nip.apply_transform(R(np.pi / 2, [0, 1, 0])); nip.apply_transform(T([r_col + EP + 5, 0, zc]))
    hole = trimesh.creation.cylinder(radius=1.25, height=30, sections=32)
    hole.apply_transform(R(np.pi / 2, [0, 1, 0])); hole.apply_transform(T([r_col + 12, 0, zc]))
    return body.union(nip).difference(hole)

# --- Vortex : aubes inclinées dans l'embouchure qui mettent l'air en rotation ----------------
def vortex(n=6, inclinaison=40.0, h_aubes=22.0, r_moyeu=5.0):
    zt = SOCKET + 35
    body = shell([[ri, 0], [ri, zt]])
    zc = zt - h_aubes / 2 - 2
    parts = [body, tube(r_moyeu, h_aubes, zc - h_aubes / 2)]
    for k in range(n):
        v = trimesh.creation.box((ri + 0.8 - r_moyeu + 0.8, 1.6, h_aubes / np.cos(np.radians(inclinaison))))
        v.apply_transform(R(np.radians(inclinaison), [1, 0, 0]))  # aube inclinée -> composante tangentielle
        v.apply_transform(T([(r_moyeu + ri) / 2, 0, zc]))
        v.apply_transform(R(2 * np.pi * k / n, [0, 0, 1]))
        parts.append(v.intersection(tube(ri + 0.8, h_aubes, zc - h_aubes / 2)))  # rogner au gabarit
    return trimesh.boolean.union(parts)

# --- Éjecteur multi-étagé : 3 buses emboîtées, l'air secondaire entre par les fentes annulaires ---
def ejecteur():
    # étage 0 : emmanchement + chambre de mélange + évasement qui reçoit la buse de l'étage 1
    s0 = shell([[ri, 0], [ri, 50], [22, 58]])
    # étage 1 : sortie (r 11) logée dans l'évasement de l'étage 0, évasement en haut pour l'étage 2
    s1 = shell([[11, 53], [11, 85], [16, 93]])
    # étage 2 : buse primaire (pointe), sortie logée dans l'évasement de l'étage 1
    s2 = shell([[7, 88], [7, 120], [9, 126]])
    struts = [bar(12.5, 20.5, 56, angle=a) for a in (0, 120, 240)] + \
             [bar(8.5, 15.0, 91, angle=a + 60) for a in (0, 120, 240)]
    return trimesh.boolean.union([s0, s1, s2, *struts])

if __name__ == "__main__":
    for name, f in (("temoin", temoin), ("coanda", coanda), ("venturi", venturi),
                    ("vortex", vortex), ("ejecteur", ejecteur)):
        m = f()
        assert m.is_watertight and m.volume > 0, name
        assert len(m.split(only_watertight=False)) == 1, f"{name}: pièces non reliées"
        m.export(f"{name}_embout.stl")
        print(f"{name:9s} Ø max {2 * np.abs(m.bounds[:, :2]).max():5.1f} mm  hauteur {m.bounds[1][2]:5.1f} mm  "
              f"volume {m.volume / 1000:4.1f} cm3")
