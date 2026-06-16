import binascii, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "edisio"))
import protocol as p

def fromhex(s): return binascii.unhexlify(s.replace(" ", ""))

# --- Decodage : trame ON groupe1 module 4 boutons, batterie 3.3V (0x21) ---
on = fromhex("6C7663AABBCCDD" "01" "04" "21" "01" "00" "01" "640D0A")
d = p.decode(on); print("ON   ->", d); assert d["id"]=="AABBCCDD" and d["value"]=="on" and d["battery"]==100

off = fromhex("6C7663AABBCCDD" "01" "04" "21" "01" "00" "02" "640D0A")
print("OFF  ->", p.decode(off)["value"])

# --- Temperature (MID 08) : DATA reordonne ---
t = fromhex("6C7663112233440008" "21" "0100" "08" "D008" "640D0A")
print("TEMP ->", p.decode(t))

bad = fromhex("FFFF00")
print("BAD  ->", p.decode(bad))

# --- Encodage : doit reproduire EXACTEMENT les templates Jeedom ---
ID="#ID#"  # on teste la structure avec un vrai id
on_f = p.cmd_on("AABBCCDD", group=1, mid="04")
print("TX ON  ->", on_f)
assert on_f[0]=="6C7663AABBCCDD01041E010001640D0A", on_f[0]
assert on_f[1]=="6C7663AABBCCDD01041E010009640D0A", on_f[1]

off_f = p.cmd_off("AABBCCDD", group=1, mid="04")
assert off_f[0]=="6C7663AABBCCDD01041E010002640D0A"
assert off_f[1]=="6C7663AABBCCDD01041E01001B640D0A"

dim_f = p.cmd_dim("AABBCCDD", 100, group=1, mid="05")
print("TX DIM100 ->", dim_f)
assert dim_f[0]=="6C7663AABBCCDD01051E01000464640D0A", dim_f[0]  # 100=0x64
assert p.cmd_dim("AABBCCDD",0,1,"05")[0]=="6C7663AABBCCDD01051E010002640D0A"  # 0 -> off

up = p.cmd_cover_up("AABBCCDD",1); dn = p.cmd_cover_down("AABBCCDD",1); st = p.cmd_cover_stop("AABBCCDD",1)
print("TX COVER ->", up, dn, st)
assert up[0]=="6C7663AABBCCDD01011E010009640D0A"
assert dn[0]=="6C7663AABBCCDD01011E01001B640D0A"
assert st[0]=="6C7663AABBCCDD01031E01000B640D0A"

learn = p.cmd_learn("AABBCCDD","04")
assert learn[0]=="6C7663AABBCCDD09041F000010640D0A", learn[0]
print("\nTOUS LES TESTS PASSENT : encodage conforme aux templates Jeedom.")
