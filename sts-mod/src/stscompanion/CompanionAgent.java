package stscompanion;

import javassist.*;
import java.lang.instrument.*;
import java.security.ProtectionDomain;

/**
 * STS Companion Agent
 * 无需 ModTheSpire，直接注入游戏方法，实时导出战斗数据。
 *
 * 原理：JVM 标准 -javaagent 机制，Javassist 字节码注入。
 */
public class CompanionAgent {

    public static void premain(String args, Instrumentation inst) {
        System.out.println("[STS伴侣Agent] 已加载");
        inst.addTransformer(new GameTransformer(), true);
    }

    // 也支持运行中动态 attach
    public static void agentmain(String args, Instrumentation inst) {
        premain(args, inst);
    }

    static class GameTransformer implements ClassFileTransformer {

        // 需要注入的目标类（JVM内部格式，用/替代.）
        private static final String ABSTRACT_ROOM =
            "com/megacrit/cardcrawl/rooms/AbstractRoom";
        private static final String ABSTRACT_MONSTER =
            "com/megacrit/cardcrawl/monsters/AbstractMonster";

        @Override
        public byte[] transform(ClassLoader loader, String className,
                Class<?> cls, ProtectionDomain domain, byte[] bytes) {
            try {
                if (ABSTRACT_ROOM.equals(className)) {
                    return patchAbstractRoom(bytes);
                }
                if (ABSTRACT_MONSTER.equals(className)) {
                    return patchAbstractMonster(bytes);
                }
            } catch (Exception e) {
                System.err.println("[STS伴侣Agent] 注入失败 " + className + ": " + e);
            }
            return null; // 返回 null = 不修改
        }

        /** 在房间进入时触发写文件 */
        private byte[] patchAbstractRoom(byte[] bytes) throws Exception {
            ClassPool pool = ClassPool.getDefault();
            pool.appendClassPath(new ByteArrayClassPath(
                "com.megacrit.cardcrawl.rooms.AbstractRoom", bytes));

            CtClass cc = pool.get("com.megacrit.cardcrawl.rooms.AbstractRoom");

            // 注入 onPlayerEntry() 方法开头
            try {
                CtMethod m = cc.getDeclaredMethod("onPlayerEntry");
                m.insertBefore("{ stscompanion.StateExporter.export(\"ROOM_ENTER\"); }");
                System.out.println("[STS伴侣Agent] 已注入 AbstractRoom.onPlayerEntry");
            } catch (NotFoundException e) {
                System.out.println("[STS伴侣Agent] onPlayerEntry 未找到，跳过");
            }

            byte[] result = cc.toBytecode();
            cc.detach();
            return result;
        }

        /** 在怪物行动后触发写文件 */
        private byte[] patchAbstractMonster(byte[] bytes) throws Exception {
            ClassPool pool = ClassPool.getDefault();
            pool.appendClassPath(new ByteArrayClassPath(
                "com.megacrit.cardcrawl.monsters.AbstractMonster", bytes));

            CtClass cc = pool.get("com.megacrit.cardcrawl.monsters.AbstractMonster");

            // 注入 takeTurn() 方法末尾
            try {
                CtMethod m = cc.getDeclaredMethod("takeTurn");
                m.insertAfter("{ stscompanion.StateExporter.export(\"MONSTER_TURN\"); }");
                System.out.println("[STS伴侣Agent] 已注入 AbstractMonster.takeTurn");
            } catch (NotFoundException e) {
                System.out.println("[STS伴侣Agent] takeTurn 未找到，跳过");
            }

            byte[] result = cc.toBytecode();
            cc.detach();
            return result;
        }
    }
}
