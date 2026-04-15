package stscompanion;

import com.megacrit.cardcrawl.dungeons.AbstractDungeon;
import com.megacrit.cardcrawl.characters.AbstractPlayer;
import com.megacrit.cardcrawl.monsters.AbstractMonster;
import com.megacrit.cardcrawl.cards.AbstractCard;
import com.megacrit.cardcrawl.rooms.AbstractRoom;

import java.io.*;
import java.nio.file.*;
import java.util.*;

/**
 * 负责把游戏状态序列化成 JSON 并写文件。
 * 被注入的方法通过反射调用此类（同一 ClassLoader）。
 */
public class StateExporter {

    private static final String OUT = System.getProperty("user.home")
        + "/Desktop/HKU/hku_yr4/Internship/slay-the-spire-mod/combat_state.json";

    public static void export(String event) {
        try {
            AbstractPlayer p = AbstractDungeon.player;
            if (p == null) return;

            StringBuilder sb = new StringBuilder(512);
            sb.append("{\n");
            sb.append("  \"event\": \"").append(event).append("\",\n");
            sb.append("  \"ts\": ").append(System.currentTimeMillis()).append(",\n");

            // 玩家
            sb.append("  \"player\": {");
            sb.append("\"hp\":").append(p.currentHealth).append(",");
            sb.append("\"max_hp\":").append(p.maxHealth).append(",");
            sb.append("\"block\":").append(p.currentBlock).append(",");
            sb.append("\"floor\":").append(AbstractDungeon.floorNum);
            sb.append("},\n");

            // 手牌
            sb.append("  \"hand\": [");
            if (p.hand != null) {
                List<AbstractCard> cards = p.hand.group;
                for (int i = 0; i < cards.size(); i++) {
                    AbstractCard c = cards.get(i);
                    if (i > 0) sb.append(",");
                    sb.append("{\"id\":\"").append(esc(c.cardID)).append("\"")
                      .append(",\"name\":\"").append(esc(c.name)).append("\"")
                      .append(",\"cost\":").append(c.costForTurn).append("}");
                }
            }
            sb.append("],\n");

            // 怪物
            sb.append("  \"monsters\": [");
            AbstractRoom room = AbstractDungeon.getCurrRoom();
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
                    sb.append("\"intent\":\"").append(m.intent.name()).append("\"");
                    try {
                        int dmg = m.getIntentDmg();
                        sb.append(",\"dmg\":").append(dmg);
                    } catch (Exception ignored) {}
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
            // 绝对不能崩溃游戏
            System.err.println("[STS伴侣] export 失败: " + t);
        }
    }

    private static String esc(String s) {
        return s == null ? "" : s.replace("\\","\\\\").replace("\"","\\\"");
    }
}
