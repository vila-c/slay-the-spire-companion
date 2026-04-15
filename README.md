# STS Companion - Slay the Spire Desktop Pet

<p align="center">
  <img src="assets/sprites/ironclad.png" width="80" />
  <img src="assets/sprites/silent.png" width="80" />
  <img src="assets/sprites/defect.png" width="80" />
  <img src="assets/sprites/watcher.png" width="80" />
</p>

<p align="center">
  <b>EN</b> | <a href="#中文说明">中文</a>
</p>

<p align="center">
  A desktop pet that watches you play Slay the Spire — analyzing your deck, warning you before dangerous fights, and cheering you on.
</p>

---

## What Does It Do?

| | |
|---|---|
| **Deck Score** | Rates your deck S–D as you play |
| **Build Advice** | Tells you which cards to pick, remove, or upgrade |
| **Combat Warnings** | Pops up tips before elite and boss fights |
| **Relic Tips** | Explains what your new relic does and what cards work with it |
| **Neow Guide** | Scores every starting bonus option and picks the best one |
| **Mood Reactions** | Pet glows red when something is wrong, bounces when things are great |

---

## Installation (Step by Step)

> No programming experience required. Just follow these steps in order.

### Step 1 — Install Python

1. Go to **https://www.python.org/downloads/**
2. Click the big yellow **Download Python** button
3. Run the installer
4. **Important:** Tick the box **"Add Python to PATH"** before clicking Install

### Step 2 — Download This Project

Click the green **Code** button at the top of this page → **Download ZIP** → unzip to any folder (e.g. your Desktop)

### Step 3 — Install Dependencies

Open the unzipped folder, then double-click **`start.bat`**

> If Windows shows a warning, click **"More info" → "Run anyway"**

That's it! The pet should appear on your screen.

### Step 4 — Install the Game Mod (Recommended)

The mod lets the companion see what's happening inside the game (enemy moves, event options, etc.).

1. Make sure **ModTheSpire** and **BaseMod** are installed (get them from the Steam Workshop)
2. Copy `sts-mod/companion-agent.jar` into your game's `mods/` folder:
   ```
   C:\Program Files (x86)\Steam\steamapps\common\SlayTheSpire\mods\
   ```
3. Launch Slay the Spire through ModTheSpire as usual

---

## How to Use

| Action | Result |
|--------|--------|
| Left-click the pet | Open / close the deck analysis panel |
| Right-click the pet | Menu (details / settings / quit) |
| Drag the pet | Move it anywhere on screen |
| Pet glows red & bounces | Important warning — click it! |

---

## Deck Score Guide

| Grade | Score | Meaning |
|-------|-------|---------|
| S | 85+ | Strong deck — go for the Heart! |
| A | 70–84 | Good shape, keep pushing |
| B | 50–69 | Average — look for key cards |
| C | 30–49 | Weak — pick carefully |
| D | <30 | Danger zone |

---

## Supported Builds

| Character | Builds |
|-----------|--------|
| Ironclad | Strength, Block, Exhaust, Bleed/Rage |
| Silent | Shiv, Poison, Discard, Infinite Loop |
| Defect | Lightning, Frost, Claw, Dark/Creative AI |
| Watcher | Stance Dance, Scry/Divination, Retain Divinity |

---

## Troubleshooting

**The pet doesn't appear**
→ Make sure Python is installed and "Add to PATH" was ticked. Try running `python main.py` in the folder.

**"Python is not recognized" error**
→ Reinstall Python and tick **"Add Python to PATH"** this time.

**No combat tips appear**
→ The Java mod isn't installed. Follow Step 4 above.

**Pet appears but shows no deck info**
→ You need to have a save file in progress. Start a new run in-game and the pet will detect it.

---

## License

[CC BY-NC-SA 4.0](LICENSE) — Free to use and share, no commercial use allowed.

This is an unofficial fan project and is not affiliated with or endorsed by MegaCrit.
Slay the Spire is a trademark of MegaCrit LLC.

---

## Support the Author / 支持作者

If this companion helped you climb higher, consider buying me a milk tea!

如果这个小伴侣帮到了你，请作者喝杯奶茶吧！

<p align="center">

**Buy Me A Coffee**: [buymeacoffee.com/vila-c](https://buymeacoffee.com/vila-c)

**WeChat Pay / 微信支付 &nbsp;&nbsp; Alipay / 支付宝**

<img src="assets/donate/wechat.jpg" width="180" /> &nbsp;&nbsp; <img src="assets/donate/Alipay.jpg" width="180" />

</p>

<p align="center">Made with ❤️ by <a href="https://github.com/vila-c">vila-c</a></p>

---

<a name="中文说明"></a>

# STS Companion - 杀戮尖塔桌面宠物伴侣

<p align="center">
  <a href="#sts-companion---slay-the-spire-desktop-pet">EN</a> | <b>中文</b>
</p>

<p align="center">
  一个陪你打杀戮尖塔的桌面宠物——实时分析牌组、进房间前提醒危险、拿遗物时告诉你怎么用。
</p>

---

## 它能做什么？

| | |
|---|---|
| **牌组评分** | 实时给你的牌组打 S 到 D 的分数 |
| **流派建议** | 告诉你该拿哪张牌、移除哪张牌、升级哪张牌 |
| **战斗预警** | 进精英/Boss 房间前弹出策略提示 |
| **遗物提示** | 拿到遗物时说明用法和配合牌 |
| **Neow 指南** | 给每个开局选项评分，帮你选最好的 |
| **情绪反应** | 牌组危险时发红光，状态好时开心跳动 |

---

## 安装步骤（零基础也能搞定）

> 按顺序来，不需要任何编程知识。

### 第一步 — 安装 Python

1. 打开 **https://www.python.org/downloads/**
2. 点击黄色大按钮 **Download Python**
3. 运行安装程序
4. **重要：** 安装前一定要勾选 **"Add Python to PATH"** 这个选项

### 第二步 — 下载本项目

点击本页面上方绿色的 **Code** 按钮 → **Download ZIP** → 解压到任意文件夹（比如桌面）

### 第三步 — 启动宠物

打开解压后的文件夹，双击 **`start.bat`**

> 如果 Windows 弹出安全警告，点 **"更多信息" → "仍要运行"**

完成！桌面宠物应该出现了。

### 第四步 — 安装游戏 Mod（推荐）

Mod 可以让宠物看到游戏内部的信息（敌人动作、事件选项等），建议安装。

1. 确认已通过 Steam 创意工坊安装了 **ModTheSpire** 和 **BaseMod**
2. 把 `sts-mod/companion-agent.jar` 复制到游戏的 `mods/` 文件夹：
   ```
   C:\Program Files (x86)\Steam\steamapps\common\SlayTheSpire\mods\
   ```
3. 通过 ModTheSpire 正常启动游戏

---

## 使用方法

| 操作 | 效果 |
|------|------|
| 左键单击宠物 | 打开 / 关闭牌组分析面板 |
| 右键单击宠物 | 菜单（详情 / 设置 / 退出） |
| 拖拽宠物 | 移动到屏幕任意位置 |
| 宠物跳动发红光 | 有重要警告，点击查看！ |

---

## 评分说明

| 等级 | 分数 | 含义 |
|------|------|------|
| S | 85+ | 强力牌组，冲击心脏！ |
| A | 70-84 | 良好，正常推进 |
| B | 50-69 | 中等，注意补强 |
| C | 30-49 | 偏弱，重点选牌 |
| D | <30 | 危险，谨慎行事 |

---

## 流派覆盖

| 角色 | 流派 |
|------|------|
| 铁甲战士 | 力量流、格挡流、消耗流、出血暴怒流 |
| 寂静猎人 | 飞刀流、毒流、弃牌流、无限循环 |
| 缺陷机器人 | 闪电流、寒冰流、爪爪流、黑暗/创意流 |
| 观者 | 姿态循环流、凝视预言流、保留神意流 |

---

## 常见问题

**宠物没有出现**
→ 确认 Python 已安装且勾选了"Add to PATH"。可以尝试在文件夹里运行 `python main.py`。

**提示"Python is not recognized"**
→ 重新安装 Python，这次记得勾选 **"Add Python to PATH"**。

**没有战斗提示**
→ 没有安装 Java Mod，请按照第四步操作。

**宠物出现了但没有牌组信息**
→ 需要游戏中有存档。开一局新游戏，宠物会自动识别。

---

## 许可证

[CC BY-NC-SA 4.0](LICENSE) — 可以自由使用和分享，禁止商业用途。

本项目是非官方粉丝作品，与 MegaCrit 官方无关。
杀戮尖塔是 MegaCrit LLC 的注册商标。

---

## 支持作者 / Support the Author

如果这个小伴侣帮到了你，请作者喝杯奶茶吧！

If this companion helped you climb higher, consider buying me a milk tea!

<p align="center">

**Buy Me A Coffee**: [buymeacoffee.com/vila-c](https://buymeacoffee.com/vila-c)

**微信支付 &nbsp;&nbsp; 支付宝**

<img src="assets/donate/wechat.png" width="180" /> &nbsp;&nbsp; <img src="assets/donate/alipay.png" width="180" />

</p>

<p align="center">用 ❤️ 为杀戮尖塔社区制作，作者 <a href="https://github.com/vila-c">vila-c</a></p>
