"""Build & install STS Companion ModTheSpire mod (auto-detect paths)"""
import subprocess, os, zipfile, sys, shutil, json, winreg

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# ── Auto-detect Steam & game paths ──────────────────────
def find_steam():
    for key_path in [
        r"SOFTWARE\WOW6432Node\Valve\Steam",
        r"SOFTWARE\Valve\Steam",
    ]:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
                return winreg.QueryValueEx(k, "InstallPath")[0]
        except OSError:
            pass
    # Fallback: common locations
    for d in [
        r"C:\Program Files (x86)\Steam",
        r"C:\Program Files\Steam",
        r"D:\Steam", r"D:\SteamLibrary",
        r"E:\Steam", r"E:\SteamLibrary",
    ]:
        if os.path.isdir(d):
            return d
    return None

def find_sts(steam_path):
    """Search all Steam library folders for SlayTheSpire."""
    candidates = [os.path.join(steam_path, "steamapps")]
    # Parse libraryfolders.vdf for additional library paths
    vdf = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf):
        with open(vdf, encoding="utf-8") as f:
            for line in f:
                line = line.strip().strip('"')
                if os.path.isabs(line) and os.path.isdir(line):
                    candidates.append(os.path.join(line, "steamapps"))
    for lib in candidates:
        p = os.path.join(lib, "common", "SlayTheSpire")
        if os.path.exists(os.path.join(p, "desktop-1.0.jar")):
            return p, lib
    return None, None

def find_workshop_mod(steamapps, app_id):
    p = os.path.join(steamapps, "workshop", "content", "646570", app_id)
    if os.path.isdir(p):
        for f in os.listdir(p):
            if f.endswith(".jar"):
                return os.path.join(p, f)
    return None

# ── Resolve paths ────────────────────────────────────────
steam = find_steam()
if not steam:
    print("[ERROR] Steam not found. Please set STEAM_PATH environment variable.")
    sys.exit(1)
print(f"Steam: {steam}")

sts_dir, steamapps = find_sts(steam)
if not sts_dir:
    print("[ERROR] Slay the Spire not found.")
    sys.exit(1)
print(f"Game:  {sts_dir}")

JAVA    = os.path.join(sts_dir, "jre", "bin", "java.exe")
STS_JAR = os.path.join(sts_dir, "desktop-1.0.jar")
BASE_JAR = find_workshop_mod(steamapps, "1605833019")  # BaseMod
MTS_JAR  = find_workshop_mod(steamapps, "1605060445")  # ModTheSpire

if not BASE_JAR:
    print("[ERROR] BaseMod not found. Subscribe in Steam Workshop first.")
    sys.exit(1)
if not MTS_JAR:
    print("[ERROR] ModTheSpire not found. Subscribe in Steam Workshop first.")
    sys.exit(1)
print(f"BaseMod:      {BASE_JAR}")
print(f"ModTheSpire:  {MTS_JAR}")

SRC_DIR  = os.path.join(SCRIPT_DIR, "src")
OUT_DIR  = os.path.join(SCRIPT_DIR, "out")
MOD_DIR  = os.path.join(sts_dir, "mods")
MOD_JAR  = os.path.join(MOD_DIR, "STSCompanion.jar")
JSON_SRC = os.path.join(SCRIPT_DIR, "ModTheSpire.json")

# Also look for ecj.jar (Eclipse Compiler) in tools/ or sts-mod/
ECJ = None
for p in [
    os.path.join(PROJECT_DIR, "tools", "ecj.jar"),
    os.path.join(SCRIPT_DIR, "ecj.jar"),
]:
    if os.path.exists(p):
        ECJ = p
        break
if not ECJ:
    print("[ERROR] ecj.jar not found in tools/ directory.")
    sys.exit(1)

# ── Clean & compile ─────────────────────────────────────
if os.path.exists(OUT_DIR):
    shutil.rmtree(OUT_DIR)
os.makedirs(OUT_DIR)
os.makedirs(MOD_DIR, exist_ok=True)

cp = f"{STS_JAR};{BASE_JAR};{MTS_JAR}"

print("\n[1/2] Compiling...")
sources = []
for root, _, files in os.walk(SRC_DIR):
    for f in files:
        if f.endswith(".java"):
            sources.append(os.path.join(root, f))

r = subprocess.run(
    [JAVA, "-jar", ECJ, "-8", "-cp", cp, "-d", OUT_DIR] + sources,
    capture_output=True, text=True
)
if r.returncode != 0:
    print("[FAILED]", r.stdout, r.stderr)
    sys.exit(1)
print("[OK]")

# ── Package JAR ──────────────────────────────────────────
print("[2/2] Packaging JAR...")
with zipfile.ZipFile(MOD_JAR, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(OUT_DIR):
        for fname in files:
            path = os.path.join(root, fname)
            arc = os.path.relpath(path, OUT_DIR).replace("\\", "/")
            zf.write(path, arc)
    zf.write(JSON_SRC, "ModTheSpire.json")

size_kb = os.path.getsize(MOD_JAR) // 1024
print(f"[OK] {MOD_JAR} ({size_kb} KB)")

print(f"""
Done! The mod has been installed to:
  {MOD_JAR}

Launch the game with "Play with Mods" and enable:
  [x] BaseMod
  [x] STS Companion
""")
