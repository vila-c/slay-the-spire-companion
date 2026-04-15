package stscompanion;

import basemod.interfaces.*;
import basemod.BaseMod;
import com.evacipated.cardcrawl.modthespire.lib.SpireInitializer;
import com.megacrit.cardcrawl.dungeons.AbstractDungeon;
import com.megacrit.cardcrawl.monsters.AbstractMonster;
import com.megacrit.cardcrawl.cards.AbstractCard;
import com.megacrit.cardcrawl.characters.AbstractPlayer;
import com.megacrit.cardcrawl.rooms.AbstractRoom;
import com.megacrit.cardcrawl.events.RoomEventDialog;
import com.megacrit.cardcrawl.ui.buttons.LargeDialogOptionButton;

import java.io.*;
import java.nio.file.*;
import java.util.*;

@SpireInitializer
public class CompanionMod implements
        PostInitializeSubscriber,
        OnStartBattleSubscriber,
        OnPlayerTurnStartSubscriber,
        PreMonsterTurnSubscriber,
        PostBattleSubscriber,
        PostDungeonInitializeSubscriber,
        StartActSubscriber {

    private static final String OUT = System.getProperty("user.home")
        + "/Desktop/HKU/hku_yr4/Internship/slay-the-spire-mod/combat_state.json";

    // ModTheSpire 通过 @SpireInitializer 调用此方法
    public static void initialize() {
        System.out.println("[STS Companion] initialize");
        new CompanionMod();
    }

    public CompanionMod() {
        BaseMod.subscribe(this);
        System.out.println("[STS Companion] subscribed, output: " + OUT);
    }

    @Override
    public void receivePostInitialize() {
        System.out.println("[STS Companion] postInitialize");
        startCompanion();
    }

    /** Auto-launch the desktop companion (pythonw main.py) */
    private static void startCompanion() {
        String dir = System.getProperty("user.home") + "/Desktop/HKU/hku_yr4/Internship/slay-the-spire-mod";
        if (!new File(dir + "/main.py").exists()) {
            System.out.println("[STS Companion] main.py not found at " + dir);
            return;
        }
        String[] cmds = {"pythonw", "python"};
        for (String cmd : cmds) {
            try {
                new ProcessBuilder(cmd, "main.py")
                    .directory(new File(dir))
                    .redirectErrorStream(true)
                    .start();
                System.out.println("[STS Companion] launched via " + cmd);
                return;
            } catch (IOException ignored) {}
        }
        System.out.println("[STS Companion] Python not found in PATH");
    }

    @Override
    public void receiveOnBattleStart(AbstractRoom r) {
        export("BATTLE_START");
    }

    @Override
    public void receiveOnPlayerTurnStart() {
        export("PLAYER_TURN_START");
    }

    @Override
    public boolean receivePreMonsterTurn(AbstractMonster m) {
        export("MONSTER_TURN");
        return true; // true = allow turn to proceed
    }

    @Override
    public void receivePostBattle(AbstractRoom r) {
        export("BATTLE_END");
    }

    @Override
    public void receivePostDungeonInitialize() {
        System.out.println("[STS Companion] dungeon initialized, floor=" + AbstractDungeon.floorNum);
        export("GAME_START");
        // Neow dialog options aren't populated yet at init time.
        // Re-export after delays so Python side can read them.
        new Thread(() -> {
            try {
                for (int i = 0; i < 3; i++) {
                    Thread.sleep(2000);
                    export("GAME_START");
                }
            } catch (Throwable ignored) {}
        }).start();
    }

    @Override
    public void receiveStartAct() {
        System.out.println("[STS Companion] act started, floor=" + AbstractDungeon.floorNum);
        export("ACT_START");
    }

    // ── 序列化 ───────────────────────────────────────────

    private static void export(String event) {
        try {
            AbstractPlayer p = AbstractDungeon.player;
            if (p == null) return;

            StringBuilder sb = new StringBuilder(512);
            sb.append("{\n");
            sb.append("  \"event\":\"").append(event).append("\",\n");
            sb.append("  \"ts\":").append(System.currentTimeMillis()).append(",\n");
            sb.append("  \"character\":\"").append(esc(p.chosenClass.name())).append("\",\n");

            // Room type
            AbstractRoom room = AbstractDungeon.getCurrRoom();
            String roomType = room != null ? room.getClass().getSimpleName() : "Unknown";
            sb.append("  \"room_type\":\"").append(esc(roomType)).append("\",\n");

            // Event room info (Neow, etc.)
            if (room != null && room.event != null) {
                String eventName = room.event.getClass().getSimpleName();
                sb.append("  \"event_name\":\"").append(esc(eventName)).append("\",\n");
                sb.append("  \"event_phase\":\"").append(room.phase.name()).append("\",\n");

                // Try to read dialog options
                try {
                    ArrayList<LargeDialogOptionButton> options = RoomEventDialog.optionList;
                    if (options != null && !options.isEmpty()) {
                        sb.append("  \"event_options\":[");
                        boolean firstOpt = true;
                        for (LargeDialogOptionButton btn : options) {
                            if (!firstOpt) sb.append(",");
                            firstOpt = false;
                            String msg = btn.msg != null ? btn.msg
                                .replaceAll("~.*?~", "")
                                .replaceAll("@\\S+", "")
                                .replaceAll("#.", "")
                                .replaceAll("NL", " ")
                                .trim() : "";
                            sb.append("{\"text\":\"").append(esc(msg)).append("\"");
                            sb.append(",\"disabled\":").append(btn.isDisabled);
                            sb.append("}");
                        }
                        sb.append("],\n");
                    }
                } catch (Throwable ignored) {}
            }

            // 玩家
            sb.append("  \"player\":{");
            sb.append("\"hp\":").append(p.currentHealth).append(",");
            sb.append("\"max_hp\":").append(p.maxHealth).append(",");
            sb.append("\"block\":").append(p.currentBlock).append(",");
            sb.append("\"energy\":").append(p.energy.energy).append(",");
            sb.append("\"gold\":").append(p.gold).append(",");
            sb.append("\"floor\":").append(AbstractDungeon.floorNum).append(",");
            sb.append("\"act\":").append(AbstractDungeon.actNum);
            sb.append("},\n");

            // 手牌
            sb.append("  \"hand\":[");
            if (p.hand != null) {
                List<AbstractCard> cards = p.hand.group;
                for (int i = 0; i < cards.size(); i++) {
                    if (i > 0) sb.append(",");
                    appendCard(sb, cards.get(i));
                }
            }
            sb.append("],\n");

            // 完整牌组
            sb.append("  \"deck\":[");
            if (p.masterDeck != null) {
                List<AbstractCard> deck = p.masterDeck.group;
                for (int i = 0; i < deck.size(); i++) {
                    if (i > 0) sb.append(",");
                    appendCard(sb, deck.get(i));
                }
            }
            sb.append("],\n");

            // 怪物
            sb.append("  \"monsters\":[");
            if (room != null && room.monsters != null) {
                boolean first = true;
                for (AbstractMonster m : room.monsters.monsters) {
                    if (m.isDead || m.isDying) continue;
                    if (!first) sb.append(",");
                    first = false;
                    sb.append("{");
                    sb.append("\"name\":\"").append(esc(m.name)).append("\",");
                    sb.append("\"hp\":").append(m.currentHealth).append(",");
                    sb.append("\"max_hp\":").append(m.maxHealth).append(",");
                    sb.append("\"block\":").append(m.currentBlock).append(",");
                    sb.append("\"intent\":\"").append(m.intent.name()).append("\",");
                    sb.append("\"dmg\":").append(m.getIntentDmg()).append(",");
                    sb.append("\"multi\":").append(getMultiAmt(m));
                    sb.append("}");
                }
            }
            sb.append("]\n}\n");

            // 原子写入
            Path tmp = Paths.get(OUT + ".tmp");
            Path out = Paths.get(OUT);
            Files.createDirectories(out.getParent());
            Files.write(tmp, sb.toString().getBytes("UTF-8"));
            Files.move(tmp, out, StandardCopyOption.REPLACE_EXISTING,
                                 StandardCopyOption.ATOMIC_MOVE);

        } catch (Throwable t) {
            System.err.println("[STS伴侣] 导出失败: " + t);
        }
    }

    private static void appendCard(StringBuilder sb, AbstractCard c) {
        sb.append("{\"id\":\"").append(esc(c.cardID)).append("\"")
          .append(",\"name\":\"").append(esc(c.name)).append("\"")
          .append(",\"cost\":").append(c.cost)
          .append(",\"cost_turn\":").append(c.costForTurn)
          .append(",\"type\":\"").append(c.type.name()).append("\"")
          .append(",\"rarity\":\"").append(c.rarity.name()).append("\"")
          .append(",\"upgraded\":").append(c.upgraded)
          .append(",\"times_upgraded\":").append(c.timesUpgraded)
          .append("}");
    }

    private static int getMultiAmt(AbstractMonster m) {
        try {
            java.lang.reflect.Field f = AbstractMonster.class.getDeclaredField("intentMultiAmt");
            f.setAccessible(true);
            return f.getInt(m);
        } catch (Exception e) { return 1; }
    }

    private static String esc(String s) {
        return s == null ? "" : s.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
