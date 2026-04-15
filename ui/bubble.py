"""
Info panel BubbleWindow v3 — collapsible sections + settings panel + event advice.
  Phase2: settings panel, event section, optimized alerts, better layout.
"""
from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                              QFrame, QPushButton, QScrollArea, QSizePolicy,
                              QLineEdit, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent

# STS palette
BG_DARK    = "#1a1209"
BG_SECTION = "#221608"
BG_HEADER  = "#2a1a08"
GOLD       = "#c9a84c"
GOLD_LIGHT = "#f0d080"
RED_WARN   = "#c0392b"
ORANGE     = "#e67e22"
GREEN      = "#27ae60"
GREY       = "#888"
WHITE      = "#f0e6d3"
BLUE       = "#5dade2"
PURPLE     = "#9b59b6"
TEAL       = "#1abc9c"


def _grade_color(grade: str) -> str:
    return {"S": "#FFD700", "A": "#7FFFD4", "B": "#87CEEB",
            "C": "#FFA500", "D": RED_WARN}.get(grade, WHITE)


class _CollapsibleSection(QFrame):
    def __init__(self, title: str, parent=None, collapsed: bool = False):
        super().__init__(parent)
        self.setStyleSheet(f"background:transparent;")
        self._collapsed = collapsed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header = QPushButton(f"{'▶' if collapsed else '▼'}  {title}")
        self._header.setStyleSheet(f"""
            QPushButton {{
                color: {GOLD}; font-size: 10px; font-weight: bold;
                background: {BG_HEADER}; border: none;
                padding: 4px 4px; text-align: left;
                letter-spacing: 1px; border-radius: 3px;
            }}
            QPushButton:hover {{ background: #3a2510; }}
        """)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.clicked.connect(self.toggle)
        self._title_text = title
        layout.addWidget(self._header)

        self._content = QFrame()
        self._content.setStyleSheet("background:transparent;")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(4, 2, 4, 2)
        self._content_layout.setSpacing(2)
        self._content.setVisible(not collapsed)
        layout.addWidget(self._content)

    def add_widget(self, w: QWidget):
        self._content_layout.addWidget(w)

    def toggle(self):
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)
        arrow = "▶" if self._collapsed else "▼"
        self._header.setText(f"{arrow}  {self._title_text}")

    def set_collapsed(self, collapsed: bool):
        if self._collapsed != collapsed:
            self.toggle()


def _row_label(text: str = "", color: str = WHITE, size: int = 12) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setTextFormat(Qt.TextFormat.RichText)
    lbl.setStyleSheet(f"color:{color}; font-size:{size}px; background:transparent;")
    return lbl


def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"background:{GOLD}; border:none; min-height:1px; max-height:1px; margin:2px 0;")
    return f


class BubbleWindow(QWidget):
    def __init__(self, pet_widget):
        super().__init__()
        self._pet = pet_widget
        self._last_alerts: list[str] = []
        self._combat_state_active = False
        self._setup_window()
        self._build_ui()
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(220)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint      |
            Qt.WindowType.WindowStaysOnTopHint     |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(300)
        self.setWindowOpacity(0)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(0)

        card = QFrame(self)
        card.setStyleSheet(f"""
            QFrame {{
                background: {BG_DARK};
                border: 2px solid {GOLD};
                border-radius: 10px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(1)

        # ── Title ────────────────────────────────────────
        self._lbl_title = _row_label(color=GOLD_LIGHT, size=13)
        self._lbl_title.setStyleSheet(
            f"color:{GOLD_LIGHT}; font-size:13px; font-weight:bold; background:transparent;")
        card_layout.addWidget(self._lbl_title)

        self._lbl_status = _row_label(size=10)
        card_layout.addWidget(self._lbl_status)
        card_layout.addWidget(_divider())

        # ── Scroll area ─────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {BG_DARK}; width: 6px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {GOLD}; border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        scroll_content = QWidget()
        self._sections_layout = QVBoxLayout(scroll_content)
        self._sections_layout.setContentsMargins(0, 0, 0, 0)
        self._sections_layout.setSpacing(2)

        # Section: Archetype
        self._sec_arch = _CollapsibleSection("🎭  流派")
        self._lbl_arch = _row_label(size=12)
        self._lbl_score = _row_label(size=18)
        arch_row = QHBoxLayout()
        arch_row.addWidget(self._lbl_arch, 1)
        arch_row.addWidget(self._lbl_score)
        arch_w = QWidget(); arch_w.setLayout(arch_row)
        arch_w.setStyleSheet("background:transparent;")
        self._sec_arch.add_widget(arch_w)
        self._lbl_winrate = _row_label(color=GREY, size=11)
        self._sec_arch.add_widget(self._lbl_winrate)
        self._sections_layout.addWidget(self._sec_arch)

        # Section: Alerts (moved up for visibility)
        self._sec_alerts = _CollapsibleSection("🚨  警告")
        self._lbl_alerts = _row_label(color=RED_WARN, size=12)
        self._sec_alerts.add_widget(self._lbl_alerts)
        self._sections_layout.addWidget(self._sec_alerts)

        # Section: Current Room (intent prediction)
        self._sec_combat = _CollapsibleSection("⚔️  敌方动向")
        self._lbl_combat = _row_label(size=11)
        self._sec_combat.add_widget(self._lbl_combat)
        self._sections_layout.addWidget(self._sec_combat)

        # Section: Event Advice (hidden by default)
        self._sec_event = _CollapsibleSection("🎲  事件建议")
        self._lbl_event = _row_label(size=11)
        self._sec_event.add_widget(self._lbl_event)
        self._sec_event.setVisible(False)
        self._sections_layout.addWidget(self._sec_event)

        # Section: Shop (hidden by default)
        self._sec_shop = _CollapsibleSection("🛒  商店建议")
        self._lbl_shop = _row_label(size=11)
        self._sec_shop.add_widget(self._lbl_shop)
        self._sec_shop.setVisible(False)
        self._sections_layout.addWidget(self._sec_shop)

        # Section: Card Advice (collapsed by default to save space)
        self._sec_cards = _CollapsibleSection("🃏  卡牌建议", collapsed=True)
        self._lbl_cards = _row_label(size=10)
        self._sec_cards.add_widget(self._lbl_cards)
        self._sections_layout.addWidget(self._sec_cards)

        # Section: Relic Synergy
        self._sec_relic_syn = _CollapsibleSection("✨  遗物协同")
        self._lbl_relic_syn = _row_label(size=10)
        self._sec_relic_syn.add_widget(self._lbl_relic_syn)
        self._sec_relic_syn.setVisible(False)
        self._sections_layout.addWidget(self._sec_relic_syn)

        # Section: Challenge Tips (hidden by default, only shown when triggered)
        self._sec_extreme = _CollapsibleSection("🔥  挑战套路")
        self._lbl_extreme = _row_label(size=11, color=PURPLE)
        self._sec_extreme.add_widget(self._lbl_extreme)
        self._sec_extreme.setVisible(False)
        self._sections_layout.addWidget(self._sec_extreme)

        # Section: Chat History (collapsed)
        self._sec_chat = _CollapsibleSection("💬  对话记录", collapsed=True)
        self._lbl_chat = _row_label(color=GREY, size=11)
        self._sec_chat.add_widget(self._lbl_chat)
        self._sections_layout.addWidget(self._sec_chat)

        # Section: Settings (collapsed)
        self._sec_settings = _CollapsibleSection("⚙️  设置", collapsed=True)
        self._build_settings_content()
        self._sections_layout.addWidget(self._sec_settings)

        self._sections_layout.addStretch()
        scroll.setWidget(scroll_content)
        scroll.setMaximumHeight(350)
        card_layout.addWidget(scroll)

        # Close button
        btn = QPushButton("✕  关闭")
        btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{GREY};
                border:none; font-size:10px; padding:1px;
                text-align:right;
            }}
            QPushButton:hover {{ color:{WHITE}; }}
        """)
        btn.clicked.connect(self.hide_bubble)
        card_layout.addWidget(btn)

        root.addWidget(card)

    def _build_settings_content(self):
        """Build settings panel with name input and toggles."""
        from core.config import get as cfg_get, set_val

        # Player name
        name_row = QWidget()
        name_row.setStyleSheet("background:transparent;")
        name_layout = QHBoxLayout(name_row)
        name_layout.setContentsMargins(0, 2, 0, 2)
        name_lbl = _row_label("昵称：", GOLD, 11)
        name_lbl.setFixedWidth(40)
        name_layout.addWidget(name_lbl)

        self._name_input = QLineEdit(cfg_get("player_name") or "主人")
        self._name_input.setMaxLength(12)
        self._name_input.setStyleSheet(f"""
            QLineEdit {{
                background: {BG_SECTION}; color: {WHITE};
                border: 1px solid {GOLD}; border-radius: 4px;
                padding: 3px 6px; font-size: 11px;
            }}
            QLineEdit:focus {{ border-color: {GOLD_LIGHT}; }}
        """)
        self._name_input.editingFinished.connect(
            lambda: set_val("player_name", self._name_input.text().strip() or "主人"))
        self._name_input.installEventFilter(self)
        name_layout.addWidget(self._name_input)
        self._sec_settings.add_widget(name_row)

        # Chat bubble toggle
        self._chk_chat = QCheckBox("聊天气泡")
        self._chk_chat.setChecked(cfg_get("chat_bubble_enabled"))
        self._chk_chat.setStyleSheet(f"""
            QCheckBox {{
                color: {WHITE}; font-size: 11px;
                background: transparent; spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {GOLD}; border-radius: 3px;
                background: {BG_SECTION};
            }}
            QCheckBox::indicator:checked {{
                background: {GOLD};
            }}
        """)
        self._chk_chat.toggled.connect(
            lambda v: set_val("chat_bubble_enabled", v))
        self._sec_settings.add_widget(self._chk_chat)

        # Extreme tips toggle
        self._chk_extreme = QCheckBox("冒险建议")
        self._chk_extreme.setChecked(cfg_get("extreme_tips_enabled"))
        self._chk_extreme.setStyleSheet(self._chk_chat.styleSheet())
        self._chk_extreme.toggled.connect(
            lambda v: set_val("extreme_tips_enabled", v))
        self._sec_settings.add_widget(self._chk_extreme)

    # ── Data update ──────────────────────────────────────
    def update_data(self, character: str, result,
                    act_label: str = "",
                    fights=None,
                    current_fight=None,
                    card_advice=None,
                    shop_advice=None,
                    event_advice=None,
                    chat_history=None,
                    extreme_tip=None,
                    ):
        char_display = {
            "IRONCLAD": "🗡️ 铁甲", "THE_SILENT": "🤫 寂静",
            "DEFECT": "🤖 机器人", "WATCHER": "🧘 观者",
        }.get(character, character)
        stage = act_label if act_label else f"关卡{result.act}"

        # Title
        self._lbl_title.setText(f"{char_display}  第 {result.floor} 层  {stage}")

        # Status bar
        hp_ratio = result.hp / max(result.max_hp, 1)
        hp_color = RED_WARN if hp_ratio < 0.35 else (ORANGE if hp_ratio < 0.6 else GREEN)
        in_combat = (current_fight is not None)
        hp_note = f' <span style="color:#555;font-size:10px;">(进场值)</span>' if in_combat else ''
        self._lbl_status.setText(
            f'❤️ <span style="color:{hp_color}">{result.hp}/{result.max_hp}</span>{hp_note}'
            f'　🃏 {result.deck_size} 张　💰 {getattr(result, "gold", "?")}'
            + (f'　💀 诅咒{result.curse_count}' if result.curse_count else '')
        )

        # Archetype
        grade_color = _grade_color(result.grade)
        self._lbl_arch.setText(
            f'{result.archetype_icon} <b>{result.archetype_name}</b>')
        self._lbl_score.setText(
            f'<span style="color:{grade_color};font-size:18px;">{result.grade}</span>'
            f'<span style="color:{GREY};font-size:11px;"> {result.score}分</span>')
        self._lbl_score.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        filled = int(result.win_rate / 5)
        bar = "█" * filled + "░" * (20 - filled)
        wr_color = GREEN if result.win_rate >= 55 else (GOLD if result.win_rate >= 40 else RED_WARN)
        self._lbl_winrate.setText(
            f'<span style="color:{wr_color};font-family:monospace;font-size:9px;">{bar}</span>'
            f'<span style="color:{GREY};font-size:9px;"> 胜率约 {result.win_rate}%</span>')

        # Alerts (with severity colors)
        self._last_alerts = result.alerts[:]
        if result.alerts:
            alert_lines = []
            for a in result.alerts[:3]:  # max 3 alerts
                if "💀" in a or "危险" in a or "极低" in a:
                    color = RED_WARN
                elif "⚔️" in a or "Boss" in a:
                    color = ORANGE
                else:
                    color = RED_WARN
                alert_lines.append(
                    f'<p style="margin:1px 0;color:{color};font-size:10px;">{a}</p>')
            self._lbl_alerts.setText("".join(alert_lines))
            self._sec_alerts.set_collapsed(False)
            self._sec_alerts.setVisible(True)
        else:
            self._sec_alerts.setVisible(False)

        # Current room
        if not self._combat_state_active:
            self._update_combat_section(current_fight, fights)

        # Event advice
        if event_advice:
            self._sec_event.setVisible(True)
            self._update_event_section(event_advice)
        else:
            self._sec_event.setVisible(False)

        # Shop section
        if shop_advice:
            self._sec_shop.setVisible(True)
            self._update_shop_section(shop_advice)
        else:
            self._sec_shop.setVisible(False)

        # Card advice
        self._update_card_section(card_advice, result)

        # Relic synergy
        if card_advice and hasattr(card_advice, 'relic_synergies') and card_advice.relic_synergies:
            self._sec_relic_syn.setVisible(True)
            syn_html = "".join(
                f'<p style="margin:1px 0;">{s}</p>' for s in card_advice.relic_synergies)
            self._lbl_relic_syn.setText(syn_html)
        else:
            self._sec_relic_syn.setVisible(False)

        # Challenge tips (only show when triggered)
        if extreme_tip:
            self._sec_extreme.setVisible(True)
            self._lbl_extreme.setText(
                f'<span style="color:{PURPLE};">{extreme_tip}</span>')
        else:
            self._sec_extreme.setVisible(False)

        # Chat history
        if chat_history:
            self._update_chat_history(chat_history)

        self.adjustSize()

    def _update_combat_section(self, current_fight, fights):
        if current_fight:
            cf = current_fight
            name = cf.info.display if cf.info else cf.enemy_name
            danger_bar = "🔴" * cf.danger + "⚫" * (5 - cf.danger)
            html = f'<b style="color:{GOLD_LIGHT};">{name}</b>  {danger_bar}<br>'
            if cf.info and cf.info.traits:
                html += f'<span style="color:{GREY};">📌 {cf.info.traits[0]}</span><br>'
            if cf.info:
                html += f'💡 {cf.info.strategy}'
                if cf.info.avoid_cards:
                    html += f'<br><span style="color:{RED_WARN};">⚠️ 避免：{", ".join(cf.info.avoid_cards[:2])}</span>'
            self._lbl_combat.setText(html)
        elif fights:
            lines = [f'<span style="color:{GREY};font-size:10px;">即将遭遇：</span>']
            icons = {"M": "⚔️", "E": "💀精英", "B": "👑Boss"}
            for f in fights[:3]:
                name = f.info.display if f.info else f.enemy_name
                danger = "🔴" * f.danger + "⚫" * (5 - f.danger)
                tip = f.info.strategy if f.info else ""
                line = f'{icons.get(f.room_type,"⚔️")} <b style="color:{GOLD_LIGHT};">{name}</b> {danger}'
                if tip:
                    line += f'<br><span style="color:{GREY};">  💡 {tip}</span>'
                lines.append(line)
            self._lbl_combat.setText("<br>".join(lines))
        else:
            self._lbl_combat.setText(f'<span style="color:{GREY};">无战斗信息</span>')

    def _update_event_section(self, advice: dict):
        """Update event advice section."""
        lines = []

        # Specific event identification
        specific = advice.get("specific_event")
        specific_advice = advice.get("specific_advice", "")
        if specific:
            lines.append(f'<b style="color:{GOLD_LIGHT};">🎲 {specific}</b>')
            if specific_advice:
                lines.append(f'<span style="color:{WHITE};">{specific_advice}</span>')

        # Priority
        priority = advice.get("priority", "")
        if priority:
            lines.append(f'<span style="color:{GOLD};font-size:10px;">📋 {priority}</span>')

        # State-based tips
        for tip in advice.get("tips", [])[:3]:
            lines.append(f'<span style="color:{WHITE};font-size:10px;">{tip}</span>')

        self._lbl_event.setText("<br>".join(lines) if lines else
                                f'<span style="color:{GREY};">暂无事件建议</span>')

    def _update_shop_section(self, advice: dict):
        lines = []
        budget = advice.get("budget_tip", "")
        gold = advice.get("gold", 0)
        lines.append(f'<span style="color:{GOLD};">💰 {gold}金 — {budget}</span>')
        for item in advice.get("priorities", [])[:3]:
            if isinstance(item, tuple) and len(item) >= 2:
                action, reason = item[0], item[1]
                color = GREEN if "移除" in action else (BLUE if "核心" in action else GOLD_LIGHT)
                lines.append(
                    f'<span style="color:{color};">• {action}</span>'
                    f'<br><span style="color:{GREY};font-size:10px;">  {reason}</span>')
        self._lbl_shop.setText("<br>".join(lines) if lines else
                               f'<span style="color:{GREY};">商店暂无特别推荐</span>')

    def _update_card_section(self, card_advice, result):
        if card_advice:
            ca = card_advice
            lines = [f'<span style="color:{GOLD_LIGHT};font-size:10px;">{ca.summary}</span>']

            if ca.pickup:
                items = []
                for p in ca.pickup[:3]:
                    if isinstance(p, tuple):
                        items.append(f'{p[0]} <span style="color:{GREY};font-size:9px;">↳ {p[1]}</span>')
                    else:
                        items.append(p)
                lines.append(f'<span style="color:{GREEN};font-size:10px;">📥 拿取：</span>'
                             + " / ".join(f'<span style="color:{WHITE};font-size:10px;">{i}</span>' for i in items))

            if ca.remove:
                items = []
                for r in ca.remove[:2]:
                    if isinstance(r, tuple):
                        items.append(r[0])
                    else:
                        items.append(r)
                lines.append(f'<span style="color:{RED_WARN};font-size:10px;">🗑 移除：{" / ".join(items)}</span>')

            if ca.upgrade:
                items = []
                for u in ca.upgrade[:3]:
                    if isinstance(u, tuple):
                        items.append(f'{u[0]} <span style="color:{GREY};font-size:9px;">↳ {u[1]}</span>')
                    else:
                        items.append(u)
                lines.append(f'<span style="color:{BLUE};font-size:10px;">⬆ 升级：</span>'
                             + " / ".join(f'<span style="color:{WHITE};font-size:10px;">{i}</span>' for i in items))

            self._lbl_cards.setText("<br>".join(lines))
        else:
            card_tips = [t for t in result.tips if any(
                k in t for k in ["缺失","优先","协同","核心","方向","升级","移除"])]
            if not card_tips:
                card_tips = result.tips[:2]
            card_html = "".join(
                f'<p style="margin:1px 0;font-size:10px;">💡 {t}</p>' for t in card_tips[:2])
            self._lbl_cards.setText(
                card_html or f'<span style="color:{GREY};">暂无建议</span>')

    def _update_chat_history(self, history: list[dict]):
        if not history:
            self._lbl_chat.setText(f'<span style="color:{GREY};">暂无对话</span>')
            return
        lines = []
        cat_colors = {"room": GOLD_LIGHT, "extreme": PURPLE, "tip": WHITE,
                      "opening": TEAL, "act": GOLD, "idle": GREY}
        for msg in history[-8:]:
            color = cat_colors.get(msg.get("category", "tip"), WHITE)
            text = msg.get("text", "")
            lines.append(f'<span style="color:{color};font-size:10px;">• {text}</span>')
        self._lbl_chat.setText("<br>".join(lines))

    # ── Real-time combat state ───────────────────────────
    def update_combat_state(self, state: dict | None):
        from core.combat_advisor import get_enemy_info

        if not state or state.get("event") == "BATTLE_END":
            self._combat_state_active = False
            return

        event_type = state.get("event", "")

        # Neow / game start — show event options if available
        if event_type in ("GAME_START", "ACT_START"):
            self._combat_state_active = True
            lines = []
            event_name = state.get("event_name", "")
            floor_num = state.get("player", {}).get("floor", 0)

            if event_name == "NeowEvent" or floor_num == 0:
                lines.append(f'<b style="color:{GOLD_LIGHT};">🐳 Neow 的祝福</b>')
                options = state.get("event_options", [])
                if options:
                    # Score all options to find the best
                    scored = []
                    for i, opt in enumerate(options):
                        text = opt.get("text", "")
                        disabled = opt.get("disabled", False)
                        advice, score = _neow_option_advice(text)
                        scored.append((i, text, disabled, advice, score))
                    # Find best non-disabled option
                    best_idx = -1
                    best_score = -999
                    for i, text, disabled, advice, score in scored:
                        if not disabled and score > best_score:
                            best_score = score
                            best_idx = i
                    lines.append(f'<span style="color:{GREY};font-size:10px;">可选奖励：</span>')
                    for i, text, disabled, advice, score in scored:
                        color = GREY if disabled else WHITE
                        is_best = (i == best_idx and best_score > 0)
                        prefix = "🔒" if disabled else ("★" if is_best else f"  {i+1}.")
                        line = f'<span style="color:{color};font-size:11px;">{prefix} {text}</span>'
                        if advice:
                            if is_best:
                                a_color = "#FFD700"  # bright gold for best
                                advice = f"⭐ 最佳推荐 — {advice}"
                            else:
                                a_color = RED_WARN if "⚠" in advice else (GREEN if "✅" in advice else GOLD)
                            line += f'<br><span style="color:{a_color};font-size:10px;">  {advice}</span>'
                        lines.append(line)
                else:
                    lines.append(f'<span style="color:{WHITE};">仔细选择 Neow 的赠礼，影响全局！</span>')
                    lines.append(f'<span style="color:{GREEN};font-size:10px;">✅ 移除牌/升级牌 通常是最佳选择</span>')
                    lines.append(f'<span style="color:{GOLD};font-size:10px;">👍 随机遗物/稀有牌 也不错</span>')
                    lines.append(f'<span style="color:{RED_WARN};font-size:10px;">⚠️ 交换初始遗物风险极大，初始遗物是角色核心</span>')
            else:
                lines.append(f'<b style="color:{GOLD_LIGHT};">📍 新区域开始</b>')

            p = state.get("player", {})
            hp, max_hp = p.get("hp", 0), p.get("max_hp", 1)
            hp_r = hp / max(max_hp, 1)
            hc = RED_WARN if hp_r < 0.35 else (ORANGE if hp_r < 0.6 else GREEN)
            lines.append(f'❤️<span style="color:{hc};">{hp}/{max_hp}</span>')

            self._lbl_combat.setText("<br>".join(lines))
            self.adjustSize()
            return

        self._combat_state_active = True
        monsters = state.get("monsters", [])
        p = state.get("player", {})

        lines = []

        hp, max_hp = p.get("hp", 0), p.get("max_hp", 1)
        blk = p.get("block", 0)
        nrg = p.get("energy", 0)
        hp_r = hp / max(max_hp, 1)
        hc = RED_WARN if hp_r < 0.35 else (ORANGE if hp_r < 0.6 else GREEN)
        p_parts = [f'❤️<span style="color:{hc};">{hp}/{max_hp}</span>']
        if blk:
            p_parts.append(f'🛡️{blk}')
        p_parts.append(f'⚡{nrg}')
        lines.append("  ".join(p_parts))

        # Section label: next attack prediction
        lines.append(f'<span style="color:{GREY};font-size:9px;">── 敌人下一步行动预测 ──</span>')

        # Tactical advice
        total_incoming = 0
        for m in monsters:
            dmg = m.get("dmg", 0)
            multi = m.get("multi", 1)
            if dmg > 0:
                total_incoming += dmg * multi

        if total_incoming > 0:
            need_block = max(0, total_incoming - blk)
            if need_block > hp * 0.5:
                lines.append(f'<span style="color:{RED_WARN};font-weight:bold;">'
                             f'⚠️ 预计受到 {total_incoming} 点伤害，优先防御！</span>')
            elif need_block > 0:
                lines.append(f'<span style="color:{ORANGE};">'
                             f'🛡️ 还需 {need_block} 点格挡抵消伤害</span>')
            else:
                lines.append(f'<span style="color:{GREEN};">'
                             f'✅ 格挡充足，可以积极输出</span>')

        INTENT_ZH = {
            "ATTACK": "攻击", "ATTACK_DEBUFF": "攻击+减益",
            "ATTACK_BUFF": "攻击+增益", "ATTACK_DEFEND": "攻击+防御",
            "DEFEND": "防御", "DEFEND_BUFF": "防御+增益",
            "BUFF": "增益", "DEBUFF": "减益", "STRONG_DEBUFF": "强减益",
            "MAGIC": "魔法", "SLEEP": "等待", "STUN": "眩晕",
            "ESCAPE": "逃跑", "UNKNOWN": "未知",
        }

        # Hand analysis — key card advice
        hand = state.get("hand", [])
        if hand:
            hand_tips = _analyze_hand(hand, total_incoming, blk, nrg)
            for tip in hand_tips[:1]:  # max 1 tip to keep combat view clean
                lines.append(f'<span style="color:{TEAL};font-size:10px;">🃏 {tip}</span>')

        strategy_set = set()
        for m in monsters:
            name = m.get("name", "?")
            # Use Chinese name from DB when available
            info = get_enemy_info(name)
            display_name = info.display if info else name
            mhp = m.get("hp", 0)
            mmhp = m.get("max_hp", 1)
            mblk = m.get("block", 0)
            intent_k = m.get("intent", "UNKNOWN")
            intent_z = INTENT_ZH.get(intent_k, intent_k)
            dmg = m.get("dmg", -1)
            multi = m.get("multi", 1)

            ratio = mhp / max(mmhp, 1)
            filled = int(ratio * 6)
            hp_bar = (f'<span style="color:{GREEN};">{"█"*filled}</span>'
                      f'<span style="color:#444;">{"█"*(6-filled)}</span>')

            dmg_s = ""
            if dmg > 0:
                dmg_s = (f' <span style="color:{RED_WARN};">'
                         f'💥{dmg}{"×"+str(multi) if multi>1 else ""}</span>')
            blk_s = f' 🛡️{mblk}' if mblk else ""

            lines.append(
                f'<b style="color:{GOLD_LIGHT};font-size:10px;">{display_name}</b> '
                f'{hp_bar} {mhp}/{mmhp}{blk_s}<br>'
                f'<span style="color:{GREY};font-size:10px;">  → {intent_z}{dmg_s}</span>')

            if info and info.strategy not in strategy_set:
                strategy_set.add(info.strategy)
                lines.append(
                    f'<span style="color:#aed6f1;font-size:10px;">💡 {info.strategy}</span>')

        self._lbl_combat.setText("<br>".join(lines))
        self.adjustSize()

    def get_last_alerts(self) -> list[str]:
        return self._last_alerts

    # ── Show / Hide ──────────────────────────────────────
    def show_bubble(self):
        self._position_near_pet()
        self.show()
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def hide_bubble(self):
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_out)
        self._fade_anim.start()

    def _on_fade_out(self):
        try:
            self._fade_anim.finished.disconnect()
        except Exception:
            pass
        if self.windowOpacity() < 0.05:
            self.hide()

    def _position_near_pet(self):
        from PyQt6.QtWidgets import QApplication
        self.adjustSize()
        pet_rect = self._pet.geometry()
        x = pet_rect.left() - self.width() - 10
        y = pet_rect.top() + (pet_rect.height() - self.height()) // 2
        screen = QApplication.primaryScreen().geometry()
        if x < 0:
            x = pet_rect.right() + 10
        x = max(0, min(x, screen.width() - self.width()))
        y = max(0, min(y, screen.height() - self.height()))
        self.move(x, y)

    def reposition(self):
        if self.isVisible() and self.windowOpacity() > 0.05:
            self._position_near_pet()

    def is_visible(self) -> bool:
        return self.isVisible() and self.windowOpacity() > 0.1

    def mousePressEvent(self, event):
        self.activateWindow()
        super().mousePressEvent(event)

    def eventFilter(self, obj, event):
        if obj is self._name_input and event.type() == QEvent.Type.MouseButtonPress:
            self.activateWindow()
            self._name_input.setFocus()
        return super().eventFilter(obj, event)


def _neow_option_advice(text: str) -> tuple[str, int]:
    """Analyze a Neow option and return (recommendation, score).
    Score: higher = better option. Used to mark best recommendation."""
    t = text.lower()
    # Relic swap (highest risk — lose starting relic for random Boss relic)
    if any(k in t for k in ("替换", "交换", "boss遗物", "初始遗物",
                             "starting relic", "boss relic")):
        return ("⚠️ 会失去初始遗物！风险极大，不推荐", -10)
    # Transform (random result)
    if "变换" in t or "变化" in t or "转化" in t:
        return ("⚠️ 随机变换，结果不可控", -5)
    # Remove card (精简牌组 is key strategy)
    if "移除" in t:
        return ("✅ 推荐！精简牌组提升抽牌质量", 90)
    # Upgrade a card
    if "升级" in t and ("随机" not in t):
        return ("✅ 推荐！升级核心牌效果翻倍", 85)
    # Upgrade random card
    if "升级" in t and "随机" in t:
        return ("👍 随机升级，运气成分大", 50)
    # Choose a rare card
    if "稀有" in t and ("选" in t or "获得" in t):
        return ("✅ 推荐！稀有牌质量高", 80)
    # Random rare card
    if "稀有" in t:
        return ("👍 随机稀有牌，多数不错", 65)
    # Colorless card
    if "无色" in t:
        return ("👍 无色牌有好选择（如「离心」「紧急按钮」）", 55)
    # Random relic
    if "遗物" in t and "随机" in t:
        return ("👍 随机遗物，影响全局", 60)
    if "遗物" in t:
        return ("👍 遗物对全局有影响", 60)
    # Gold
    if any(k in t for k in ("金币", "250金", "100金", "金")):
        return ("💰 金币为商店服务，不如牌/遗物直接", 35)
    # Max HP gain
    if ("生命" in t or "hp" in t) and any(k in t for k in ("获得", "增加", "提升", "最大")):
        return ("👍 额外血量提升容错", 45)
    # HP loss (as cost for something else)
    if ("生命" in t or "hp" in t) and any(k in t for k in ("失去", "损失", "减少")):
        return ("⚠️ 注意HP代价，权衡收益", 20)
    # Potions
    if "药水" in t:
        return ("🧪 药水仅一次性，收益最低", 15)
    # Card choice (choose from 3)
    if "选择" in t and "牌" in t:
        return ("👍 可以选牌，看具体选项", 55)
    # Damage all enemies
    if "伤害" in t and "所有" in t:
        return ("💰 一般，帮助清第一场", 25)
    return ("", 0)


# Key cards that deserve special mention when in hand
_HAND_KEY_CARDS = {
    # id: (upgraded_tip, normal_tip)
    "Bash":        ("「痛击+」先打，施加3回合易伤", "「痛击」先打，施加易伤"),
    "Eruption":    ("「爆发+」仅1费，适合切愤怒", "「爆发」切入愤怒架势"),
    "Feed":        ("「吞噬+」击杀回4血+涨上限", "「吞噬」击杀可涨血上限"),
    "Demon Form":  ("「恶魔化+」2费，尽快打出", "「恶魔化」尽快打出获得力量"),
    "Corruption":  ("「堕落+」2费，技能牌全部0费", "「堕落」让技能牌变0费"),
    "Catalyst":    ("「催化剂+」毒翻3倍！", "「催化剂」翻倍毒"),
    "Wraith Form": ("「幽灵形态+」3回合无实体", "「幽灵形态」获得无实体"),
    "Noxious Fumes":("「毒雾+」每回合3毒", "「毒雾」持续上毒"),
    "Echo Form":   ("「回响形态+」2费，每回合首牌翻倍", "「回响形态」首牌翻倍"),
    "Defragment":  ("「碎片整理+」+2集中", "「碎片整理」+1集中"),
    "Mental Fortress": ("「精神堡垒+」换架势+6格挡", "「精神堡垒」换架势+4格挡"),
    "Rushdown":    ("「急躁+」进入愤怒抽2张", "「急躁」进入愤怒抽1张"),
    "Limit Break": ("「突破极限+」不消耗，力量翻倍", "「突破极限」力量翻倍"),
    "Offering":    ("「祭品+」抽5张+2能量", "「祭品」抽3张+2能量"),
    "Barricade":   ("「壁垒+」2费，格挡不消失", "「壁垒」格挡不消失"),
    "Footwork":    ("「足部工作+」+3敏捷", "「足部工作」+2敏捷"),
    "Burst":       ("「弹幕+」2张技能翻倍", "「弹幕」下张技能翻倍"),
    "Blasphemy":   ("「渎神+」可保留，下回合神性", "「渎神」下回合进入神性"),
}


def _analyze_hand(hand: list[dict], incoming: int, block: int, energy: int) -> list[str]:
    """Analyze hand cards and return brief play tips."""
    tips = []

    # Check for key cards
    for card in hand:
        cid = card.get("id", "")
        upgraded = card.get("upgraded", False)
        cost = card.get("cost_turn", card.get("cost", 99))

        if cid in _HAND_KEY_CARDS:
            tip_up, tip_norm = _HAND_KEY_CARDS[cid]
            tip = tip_up if upgraded else tip_norm
            if cost <= energy:
                tips.append(tip)

    # Count powers in hand
    powers = [c for c in hand if c.get("type") == "POWER"
              and c.get("cost_turn", c.get("cost", 99)) <= energy]
    if powers and not tips:
        names = [c.get("name", "") for c in powers[:2]]
        tips.append(f"优先使用能力牌：{'、'.join(names)}")

    # If enemy is not attacking, suggest offense
    if incoming == 0 and not tips:
        attacks = [c for c in hand if c.get("type") == "ATTACK"]
        upgraded_attacks = [c for c in attacks if c.get("upgraded")]
        if upgraded_attacks:
            names = [c.get("name", "") + "+" for c in upgraded_attacks[:2]]
            tips.append(f"敌人不攻击，全力输出！{'、'.join(names)}伤害更高")
        elif attacks:
            tips.append("敌人不攻击，全力输出！")

    return tips

