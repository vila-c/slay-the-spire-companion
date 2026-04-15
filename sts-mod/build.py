"""
编译并打包 STS Companion Agent JAR
完全不依赖 ModTheSpire / BaseMod
"""
import subprocess, os, zipfile, sys, shutil

JAVA     = "C:/Program Files (x86)/Steam/steamapps/common/SlayTheSpire/jre/bin/java.exe"
ECJ      = "C:/Users/85255/Desktop/HKU/hku_yr4/Internship/slay-the-spire-mod/tools/ecj.jar"
STS_JAR  = "C:/Program Files (x86)/Steam/steamapps/common/SlayTheSpire/desktop-1.0.jar"
# Javassist 从 ModTheSpire.jar 里取
MTS_JAR  = "C:/Program Files (x86)/Steam/steamapps/workshop/content/646570/1605060445/ModTheSpire.jar"

SRC_DIR  = "C:/Users/85255/Desktop/HKU/hku_yr4/Internship/slay-the-spire-mod/sts-mod/src"
OUT_DIR  = "C:/Users/85255/Desktop/HKU/hku_yr4/Internship/slay-the-spire-mod/sts-mod/out"
AGENT_JAR = "C:/Users/85255/Desktop/HKU/hku_yr4/Internship/slay-the-spire-mod/sts-mod/companion-agent.jar"
MANIFEST  = "C:/Users/85255/Desktop/HKU/hku_yr4/Internship/slay-the-spire-mod/sts-mod/MANIFEST.MF"

# 清理
if os.path.exists(OUT_DIR):
    shutil.rmtree(OUT_DIR)
os.makedirs(OUT_DIR)

# classpath: STS 游戏类 + Javassist（来自 MTS jar）
cp = f"{STS_JAR};{MTS_JAR}"

# ── 步骤 1：编译 ────────────────────────────────────────
print("[1/3] 编译...")
sources = []
for root, _, files in os.walk(SRC_DIR):
    for f in files:
        if f.endswith(".java"):
            sources.append(os.path.join(root, f))

result = subprocess.run(
    [JAVA, "-jar", ECJ, "-8", "-cp", cp, "-d", OUT_DIR] + sources,
    capture_output=True, text=True
)
if result.returncode != 0:
    print("[失败]", result.stdout, result.stderr)
    sys.exit(1)
print("[OK] 编译成功")

# ── 步骤 2：提取 Javassist class 文件（嵌入 agent jar）────
print("[2/3] 嵌入 Javassist...")
with zipfile.ZipFile(MTS_JAR, "r") as z:
    jav_entries = [n for n in z.namelist() if n.startswith("javassist/")]
    for name in jav_entries:
        if name.endswith("/"):
            continue  # skip directory entries
        target = os.path.join(OUT_DIR, name.replace("/", os.sep))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with z.open(name) as src, open(target, "wb") as dst:
            dst.write(src.read())
print(f"[OK] 嵌入 {len(jav_entries)} 个 Javassist 文件")

# ── 步骤 3：生成 MANIFEST 并打包 JAR ────────────────────
print("[3/3] 打包 JAR...")
manifest = (
    "Manifest-Version: 1.0\n"
    "Premain-Class: stscompanion.CompanionAgent\n"
    "Agent-Class: stscompanion.CompanionAgent\n"
    "Can-Retransform-Classes: true\n"
    "Can-Redefine-Classes: true\n"
)
with open(MANIFEST, "w") as f:
    f.write(manifest)

with zipfile.ZipFile(AGENT_JAR, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(MANIFEST, "META-INF/MANIFEST.MF")
    for root, _, files in os.walk(OUT_DIR):
        for fname in files:
            path = os.path.join(root, fname)
            arc = os.path.relpath(path, OUT_DIR).replace("\\", "/")
            zf.write(path, arc)

size_kb = os.path.getsize(AGENT_JAR) // 1024
print(f"[OK] {AGENT_JAR} ({size_kb} KB)")

# ── 步骤 4：修改 config.json 加入 -javaagent ────────────
import json
CONFIG = "C:/Program Files (x86)/Steam/steamapps/common/SlayTheSpire/config.json"
with open(CONFIG, "r") as f:
    cfg = json.load(f)

agent_arg = f"-javaagent:C:/Users/85255/Desktop/HKU/hku_yr4/Internship/slay-the-spire-mod/sts-mod/companion-agent.jar"
if agent_arg not in cfg.get("vmArgs", []):
    cfg.setdefault("vmArgs", []).append(agent_arg)
    with open(CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"[OK] config.json 已添加 -javaagent")
else:
    print(f"[跳过] config.json 已有 -javaagent")

print("\n完成！正常启动 STS 即可（无需 ModTheSpire）")
print(f"战斗数据将写入: C:/Users/85255/Desktop/HKU/hku_yr4/Internship/slay-the-spire-mod/combat_state.json")
