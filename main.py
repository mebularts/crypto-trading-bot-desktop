import sys
import json
import io
import threading
from datetime import datetime
from pathlib import Path

import asyncio
import requests
import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QComboBox,
    QPushButton,
    QLabel,
    QScrollArea,
    QLineEdit,
    QRadioButton,
    QGroupBox,
    QFormLayout,
    QWidgetItem,
    QLayoutItem,
    QTextEdit,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from qt_material import apply_stylesheet


BASE_DIR = Path(__file__).resolve().parent
USER_PATH = BASE_DIR / "user.json"
ADS_PATH = BASE_DIR / "ads.json"
ICON_PATH = BASE_DIR / "icon.ico"


class CryptoBot(QWidget):
    """
    Example version of the trading notifier without any license checks
    or bundled personal credentials. Configuration is read from JSON
    files that live next to this script (user.json, ads.json).
    """

    def __init__(self):
        super().__init__()
        self.load_settings()
        self.load_ads()
        self.reset_paper_state()
        self.interval = self.settings.get("interval", 900)
        self.init_ui()
        self.selected_symbols = []
        self.bot_thread = None
        self.ad_timer = QTimer(self)
        self.ad_timer.timeout.connect(self.check_ads_schedule)
        self.ad_timer.start(60_000)  # check ads every minute
        self.setFixedSize(800, 900)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

    def load_settings(self):
        try:
            with open(USER_PATH, "r", encoding="utf-8") as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {
                "bot_token": "",
                "chat_id": "",
                "interval": 900,
                "message_interval": 30,
                "api_key": "",
                "api_secret": "",
                "profile": "swing",
                "paper_start_balance": 10_000,
                "paper_risk_pct": 5,
                "signature": "Built by @mebularts",
                "rsi_thresholds": {
                    "buy": True,
                    "sell": True,
                    "neutral": True,
                    "potential_buy": True,
                    "potential_sell": True,
                },
            }
        # Provide defaults for newly added fields when upgrading from older configs
        self.settings.setdefault("signature", "Built by @mebularts")

    def save_settings(self):
        with open(USER_PATH, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def load_ads(self):
        try:
            with open(ADS_PATH, "r", encoding="utf-8") as f:
                self.ads = json.load(f)["ads"]
        except (FileNotFoundError, json.JSONDecodeError):
            self.ads = []

    def save_ads(self):
        with open(ADS_PATH, "w", encoding="utf-8") as f:
            json.dump({"ads": self.ads}, f, ensure_ascii=False, indent=4)

    def init_ui(self):
        layout = QVBoxLayout()

        dev_label = QLabel(
            'Developer: <a href="https://github.com/mebularts">@mebularts</a> - Open source build'
        )
        dev_label.setTextFormat(Qt.RichText)
        dev_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        dev_label.setOpenExternalLinks(True)
        layout.addWidget(dev_label)

        # Load markets from the chosen exchange (binance by default)
        try:
            self.exchange = ccxt.binance()
            markets = self.exchange.load_markets()
            self.symbols = list(markets.keys())
        except Exception as exc:
            self.exchange = None
            self.symbols = []
            print(f"Exchange init failed: {exc}")

        # Telegram bot settings inputs
        form_layout = QFormLayout()
        self.token_input = QLineEdit(self.settings.get("bot_token", ""), self)
        self.chat_id_input = QLineEdit(self.settings.get("chat_id", ""), self)
        self.interval_input = QLineEdit(str(self.settings.get("interval", 900)), self)
        self.api_key_input = QLineEdit(self.settings.get("api_key", ""), self)
        self.api_secret_input = QLineEdit(self.settings.get("api_secret", ""), self)
        self.api_secret_input.setEchoMode(QLineEdit.Password)
        self.signature_input = QLineEdit(self.settings.get("signature", ""), self)
        self.profile_combo = QComboBox(self)
        self.profile_combo.addItems(["scalp", "intraday", "swing"])
        self.profile_combo.setCurrentText(self.settings.get("profile", "swing"))
        form_layout.addRow("Telegram Bot Token:", self.token_input)
        form_layout.addRow("Telegram Chat ID:", self.chat_id_input)
        form_layout.addRow("Message Interval (seconds):", self.interval_input)
        form_layout.addRow("Exchange API Key (optional):", self.api_key_input)
        form_layout.addRow("Exchange API Secret:", self.api_secret_input)
        form_layout.addRow("Message signature:", self.signature_input)
        form_layout.addRow("Strategy Profile:", self.profile_combo)
        layout.addLayout(form_layout)

        # Paper trading controls
        paper_layout = QHBoxLayout()
        self.paper_checkbox = QCheckBox("Enable paper trading", self)
        self.paper_checkbox.setChecked(False)
        self.paper_risk_input = QLineEdit(str(self.settings.get("paper_risk_pct", 5)), self)
        self.paper_risk_input.setFixedWidth(60)
        self.paper_balance_label = QLabel(
            f"Paper cash: {self.paper_cash:,.2f} USDT", self
        )
        self.paper_pnl_label = QLabel(
            f"Paper PnL: {self.paper_pnl:,.2f} USDT", self
        )
        paper_layout.addWidget(self.paper_checkbox)
        paper_layout.addWidget(QLabel("Risk % per trade:", self))
        paper_layout.addWidget(self.paper_risk_input)
        paper_layout.addWidget(self.paper_balance_label)
        paper_layout.addWidget(self.paper_pnl_label)
        layout.addLayout(paper_layout)

        # RSI checkboxes
        self.rsi_group = QGroupBox("RSI Options")
        rsi_layout = QHBoxLayout()
        self.rsi_checkboxes = {
            "buy": QCheckBox("Buy", self),
            "sell": QCheckBox("Sell", self),
            "neutral": QCheckBox("Neutral", self),
            "potential_buy": QCheckBox("Potential Buy", self),
            "potential_sell": QCheckBox("Potential Sell", self),
        }
        for key, checkbox in self.rsi_checkboxes.items():
            checkbox.setChecked(self.settings["rsi_thresholds"].get(key, True))
            rsi_layout.addWidget(checkbox)
        self.rsi_group.setLayout(rsi_layout)
        layout.addWidget(self.rsi_group)

        # Auto-message toggle
        self.auto_message_radio = QRadioButton("Send automatic messages", self)
        self.auto_message_radio.setChecked(True)
        layout.addWidget(self.auto_message_radio)

        # Portfolio / positions (read-only) view
        portfolio_group = QGroupBox("Portfolio / Positions (read-only)")
        portfolio_layout = QVBoxLayout()
        refresh_button = QPushButton("Refresh Balances", self)
        refresh_button.clicked.connect(self.refresh_portfolio)
        self.portfolio_view = QTextEdit(self)
        self.portfolio_view.setReadOnly(True)
        self.portfolio_view.setPlaceholderText(
            "Enter API key/secret to pull balances. No trades executed."
        )
        portfolio_layout.addWidget(refresh_button)
        portfolio_layout.addWidget(self.portfolio_view)
        portfolio_group.setLayout(portfolio_layout)
        layout.addWidget(portfolio_group)

        # Symbol selector with search
        self.checkbox_widget = QWidget()
        self.checkbox_layout = QVBoxLayout(self.checkbox_widget)
        self.checkboxes = []
        self.build_symbol_checkboxes()

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search coin...")
        self.search_input.textChanged.connect(self.filter_symbols)
        layout.addWidget(self.search_input)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.checkbox_widget)
        layout.addWidget(scroll_area)

        # Control buttons
        start_button = QPushButton("Start", self)
        start_button.clicked.connect(self.start_bot)
        select_all_button = QPushButton("Select all", self)
        select_all_button.clicked.connect(self.select_all)
        deselect_all_button = QPushButton("Deselect all", self)
        deselect_all_button.clicked.connect(self.deselect_all)
        select_button_layout = QHBoxLayout()
        select_button_layout.addWidget(start_button)
        select_button_layout.addWidget(select_all_button)
        select_button_layout.addWidget(deselect_all_button)
        layout.addLayout(select_button_layout)

        self.status_label = QLabel("", self)
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.setWindowTitle("Crypto Trading Bot - @mebularts")

    def build_symbol_checkboxes(self, filter_text: str | None = None):
        self.clear_layout(self.checkbox_layout)
        self.checkboxes = []
        for symbol in self.symbols:
            if filter_text and filter_text.lower() not in symbol.lower():
                continue
            checkbox = QCheckBox(symbol, self)
            self.checkboxes.append(checkbox)
            self.checkbox_layout.addWidget(checkbox)

    def filter_symbols(self):
        filter_text = self.search_input.text()
        self.build_symbol_checkboxes(filter_text)

    def clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if isinstance(item, QWidgetItem):
                item.widget().deleteLater()
            elif isinstance(item, QLayoutItem):
                self.clear_layout(item.layout())
            layout.removeItem(item)

    def select_all(self):
        for cb in self.findChildren(QCheckBox):
            cb.setChecked(True)

    def deselect_all(self):
        for cb in self.findChildren(QCheckBox):
            cb.setChecked(False)

    def start_bot(self):
        self.settings["bot_token"] = self.token_input.text().strip()
        self.settings["chat_id"] = self.chat_id_input.text().strip()
        self.settings["interval"] = int(self.interval_input.text())
        self.settings["api_key"] = self.api_key_input.text().strip()
        self.settings["api_secret"] = self.api_secret_input.text().strip()
        self.settings["profile"] = self.profile_combo.currentText()
        self.settings["signature"] = self.signature_input.text().strip()
        try:
            self.settings["paper_risk_pct"] = float(self.paper_risk_input.text())
        except ValueError:
            self.settings["paper_risk_pct"] = 5.0
        self.settings["rsi_thresholds"] = {
            key: checkbox.isChecked() for key, checkbox in self.rsi_checkboxes.items()
        }
        self.save_settings()

        self.selected_symbols = [
            cb.text() for cb in self.findChildren(QCheckBox) if cb.isChecked()
        ]
        if not self.selected_symbols:
            self.status_label.setText("Select at least one trading pair.")
            return

        if not self.settings["bot_token"] or not self.settings["chat_id"]:
            self.status_label.setText("Fill in Telegram bot token and chat id.")
            return

        self.status_label.setText("Bot started...")
        self.bot_token = self.settings["bot_token"]
        self.bot_chatID = self.settings["chat_id"]
        self.interval = self.settings["interval"]
        self.profile = self.settings["profile"]
        QTimer.singleShot(0, self.update_paper_labels)
        if self.bot_thread is None:
            self.bot_thread = threading.Thread(target=self.run_bot, daemon=True)
            self.bot_thread.start()

    def run_bot(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.bot_loop())
        loop.close()

    def format_with_signature(self, text: str):
        signature = self.settings.get("signature", "").strip()
        if signature:
            return f"{text}\n\n{signature}"
        return text

    async def bot_loop(self):
        while True:
            try:
                await self.dispatch_ads_if_due()
                if self.auto_message_radio.isChecked():
                    for symbol in self.selected_symbols:
                        symbol_interval = await self.analyze_and_send_message(symbol)
                        await asyncio.sleep(symbol_interval or self.interval)
            except Exception as exc:
                print(f"Bot loop error: {exc}")
            await asyncio.sleep(1)

    async def dispatch_ads_if_due(self):
        current_time = datetime.now()
        for ad in self.ads:
            if not ad.get("active"):
                continue
            schedule = ad.get("schedule")
            if not schedule:
                continue
            ad_time = datetime.strptime(
                f"{schedule['date']} {schedule['time']}", "%Y-%m-%d %H:%M:%S"
            )
            if current_time >= ad_time:
                await self.send_ad(ad)
                ad["active"] = False
                self.save_ads()

    def check_ads_schedule(self):
        asyncio.run(self.dispatch_ads_if_due())

    def closeEvent(self, event):
        self.ad_timer.stop()
        event.accept()

    async def send_ad(self, ad):
        try:
            message = f"{ad['title']}\n{ad['description']}\n{ad['link']}"
            message = self.format_with_signature(message)
            bot = Bot(self.bot_token)
            image_path = ad.get("image_path")
            if image_path:
                with open(image_path, "rb") as img:
                    await bot.send_photo(
                        chat_id=self.bot_chatID,
                        photo=img,
                        caption=message,
                        parse_mode="Markdown",
                    )
            else:
                await bot.send_message(
                    chat_id=self.bot_chatID, text=message, parse_mode="Markdown"
                )
        except Exception as exc:
            print(f"Ad send failed: {exc}")

    async def analyze_and_send_message(self, symbol):
        if not self.exchange:
            print("Exchange not initialized.")
            return None
        try:
            timeframe, limit = self.get_profile_params()
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if not ohlcv:
                print(f"No data returned for {symbol}")
                return None

            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            close_prices = df["close"]
            last_close = close_prices.iloc[-1]

            rsi = ta.rsi(close_prices, length=14)
            if rsi is None or rsi.empty:
                print(f"RSI calculation failed for {symbol}")
                return None

            stoch = ta.stoch(df["high"], df["low"], df["close"])
            aroon = ta.aroon(df["high"], df["low"])
            macd = ta.macd(close_prices)
            obv = ta.obv(close_prices, df["volume"])
            bbands = ta.bbands(close_prices, length=20, std=2)
            atr = ta.atr(df["high"], df["low"], close_prices, length=14)
            psar = ta.psar(df["high"], df["low"], close_prices)
            dominance = self.fetch_dominance(symbol) or 0
            atr_value = float(atr.iloc[-1]) if hasattr(atr, "empty") and not atr.empty else 0.0
            atr_pct = (atr_value / last_close) if last_close else 0

            macd_line = macd.iloc[-1]["MACD_12_26_9"] if hasattr(macd, "empty") and not macd.empty else 0
            macd_signal = macd.iloc[-1]["MACDs_12_26_9"] if hasattr(macd, "empty") and not macd.empty else 0
            stoch_k_val = stoch.iloc[-1]["STOCHk_14_3_3"] if hasattr(stoch, "empty") and not stoch.empty else 0
            stoch_d_val = stoch.iloc[-1]["STOCHd_14_3_3"] if hasattr(stoch, "empty") and not stoch.empty else 0
            aroon_up_val = aroon.iloc[-1]["AROONU_14"] if hasattr(aroon, "empty") and not aroon.empty else 0
            aroon_down_val = aroon.iloc[-1]["AROOND_14"] if hasattr(aroon, "empty") and not aroon.empty else 0
            bb_lower = bbands.iloc[-1]["BBL_20_2.0"] if hasattr(bbands, "empty") and not bbands.empty else last_close
            bb_middle = bbands.iloc[-1]["BBM_20_2.0"] if hasattr(bbands, "empty") and not bbands.empty else last_close
            bb_upper = bbands.iloc[-1]["BBU_20_2.0"] if hasattr(bbands, "empty") and not bbands.empty else last_close
            obv_val = obv.iloc[-1] if hasattr(obv, "empty") and not obv.empty else 0
            psar_val = psar.iloc[-1]["PSARl_0.02_0.2"] if isinstance(psar, pd.DataFrame) and not psar.empty else last_close

            votes, status = self.compute_indicator_votes(
                rsi.iloc[-1], macd, stoch, aroon, bbands, last_close
            )
            risk_score = self.compute_risk_score(atr_pct, votes)
            tp, sl = self.compute_tp_sl(status, last_close, atr_value)
            dynamic_interval = self.compute_dynamic_interval(atr_pct)

            volume_24h = int(df["volume"].sum())
            paper_note = self.apply_paper_trading(status, symbol, last_close, atr_value)

            message_lines = [
                f"*{symbol}* | Profile: *{self.profile_combo.currentText()}* | Status: *{status}*",
                f"RSI: {rsi.iloc[-1]:.2f} | Risk: {risk_score}/100 | ATR%: {atr_pct*100:.2f}",
                f"Votes (buy/sell/neutral): {votes['buy']} / {votes['sell']} / {votes['neutral']}",
                f"MACD: {macd_line:.2f} | Signal: {macd_signal:.2f}",
                f"Stoch %K/%D: {stoch_k_val:.2f}/{stoch_d_val:.2f}",
                f"Aroon Up/Down: {aroon_up_val:.2f}/{aroon_down_val:.2f}",
                f"BB L/M/U: {bb_lower:.2f}/{bb_middle:.2f}/{bb_upper:.2f}",
                f"OBV: {obv_val:.2f} | ATR: {atr_value:.2f} | Dominance: {dominance:.2f}%",
                f"24h Vol (bars sum): {volume_24h}",
                f"PSAR: {psar_val:.4f} | TP: {tp:.4f} | SL: {sl:.4f}",
                f"Next check (dynamic): ~{dynamic_interval}s",
            ]
            if paper_note:
                message_lines.append(paper_note)

            message = self.format_with_signature("\n".join(message_lines))
            await self.send_telegram_message_with_graph(symbol, message, df, rsi)
            return dynamic_interval
        except Exception as exc:
            print(f"Error analyzing {symbol}: {exc}")
            return None

    async def send_telegram_message_with_graph(self, symbol, message, df, rsi):
        try:
            plt.figure(figsize=(12, 16))

            plt.subplot(4, 1, 1)
            plt.plot(df["close"], label="Close")
            plt.title(f"{symbol} Close Prices")
            plt.legend()

            plt.subplot(4, 1, 2)
            plt.plot(rsi, label="RSI")
            plt.axhline(70, color="red", linestyle="--")
            plt.axhline(30, color="green", linestyle="--")
            plt.title("RSI")
            plt.legend()

            plt.subplot(4, 1, 3)
            macd = ta.macd(df["close"])
            plt.plot(macd["MACD_12_26_9"], label="MACD")
            plt.plot(macd["MACDs_12_26_9"], label="Signal")
            plt.title("MACD")
            plt.legend()

            plt.subplot(4, 1, 4)
            bbands = ta.bbands(df["close"], length=20, std=2)
            plt.plot(df["close"], label="Close")
            plt.plot(bbands["BBL_20_2.0"], label="Lower Band")
            plt.plot(bbands["BBM_20_2.0"], label="Middle Band")
            plt.plot(bbands["BBU_20_2.0"], label="Upper Band")
            plt.title("Bollinger Bands")
            plt.legend()

            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)

            media = [InputMediaPhoto(media=buf, caption=message, parse_mode="Markdown")]
            bot = Bot(self.bot_token)
            await bot.send_media_group(chat_id=self.bot_chatID, media=media)
            buf.close()
            plt.close()
        except TelegramError as exc:
            print(f"Telegram send error: {exc}")

    def compute_indicator_votes(self, rsi_value, macd, stoch, aroon, bbands, last_close):
        votes = {"buy": 0, "sell": 0, "neutral": 0}

        # RSI vote
        if rsi_value < 30:
            votes["buy"] += 1
        elif rsi_value > 70:
            votes["sell"] += 1
        else:
            votes["neutral"] += 1

        # MACD vote
        try:
            macd_line = macd.iloc[-1]["MACD_12_26_9"]
            macd_signal = macd.iloc[-1]["MACDs_12_26_9"]
            if macd_line - macd_signal > 0:
                votes["buy"] += 1
            elif macd_line - macd_signal < 0:
                votes["sell"] += 1
            else:
                votes["neutral"] += 1
        except Exception:
            votes["neutral"] += 1

        # Stochastic vote
        try:
            stoch_k = stoch.iloc[-1]["STOCHk_14_3_3"]
            if stoch_k < 20:
                votes["buy"] += 1
            elif stoch_k > 80:
                votes["sell"] += 1
            else:
                votes["neutral"] += 1
        except Exception:
            votes["neutral"] += 1

        # Aroon vote
        try:
            aroon_up = aroon.iloc[-1]["AROONU_14"]
            aroon_down = aroon.iloc[-1]["AROOND_14"]
            if aroon_up > 70 and aroon_down < 30:
                votes["buy"] += 1
            elif aroon_down > 70 and aroon_up < 30:
                votes["sell"] += 1
            else:
                votes["neutral"] += 1
        except Exception:
            votes["neutral"] += 1

        # Bollinger band vote
        try:
            lower = bbands.iloc[-1]["BBL_20_2.0"]
            upper = bbands.iloc[-1]["BBU_20_2.0"]
            if last_close < lower:
                votes["buy"] += 1
            elif last_close > upper:
                votes["sell"] += 1
            else:
                votes["neutral"] += 1
        except Exception:
            votes["neutral"] += 1

        # Status from majority
        if votes["buy"] > votes["sell"] and self.rsi_checkboxes["buy"].isChecked():
            status = "Buy"
        elif votes["sell"] > votes["buy"] and self.rsi_checkboxes["sell"].isChecked():
            status = "Sell"
        else:
            status = "Neutral"
        return votes, status

    def compute_risk_score(self, atr_pct, votes):
        vote_spread = abs(votes["buy"] - votes["sell"])
        conflict_penalty = 10 if vote_spread <= 1 else 0
        atr_component = min(70, atr_pct * 3000)  # scales ATR% into 0-70-ish
        base = 30 + atr_component + conflict_penalty
        return int(min(100, max(0, base)))

    def compute_tp_sl(self, status, last_close, atr_value):
        if not last_close or not atr_value:
            return last_close, last_close
        if status == "Buy":
            tp = last_close + 2 * atr_value
            sl = last_close - 1.5 * atr_value
        elif status == "Sell":
            tp = last_close - 2 * atr_value
            sl = last_close + 1.5 * atr_value
        else:
            tp = last_close
            sl = last_close
        return tp, sl

    def compute_dynamic_interval(self, atr_pct):
        factor = 1.0
        if atr_pct > 0.03:
            factor = 0.5
        elif atr_pct > 0.02:
            factor = 0.7
        elif atr_pct < 0.01:
            factor = 1.3
        return max(5, int(self.interval * factor))

    def get_profile_params(self):
        profile = self.profile_combo.currentText()
        if profile == "scalp":
            return "1m", 240
        if profile == "intraday":
            return "5m", 240
        return "1h", 240

    def reset_paper_state(self):
        self.paper_cash = float(self.settings.get("paper_start_balance", 10_000))
        self.paper_positions = {}
        self.paper_pnl = 0.0

    def apply_paper_trading(self, status, symbol, last_price, atr_value):
        if not self.paper_checkbox.isChecked():
            return ""
        if status not in {"Buy", "Sell"}:
            return ""
        try:
            risk_pct = float(self.paper_risk_input.text())
        except Exception:
            risk_pct = 5.0
        risk_pct = max(0.1, min(50.0, risk_pct))
        note = ""
        if status == "Buy" and symbol not in self.paper_positions:
            allocation = self.paper_cash * (risk_pct / 100)
            if allocation <= 0:
                return ""
            qty = allocation / last_price
            self.paper_cash -= allocation
            self.paper_positions[symbol] = {"qty": qty, "entry": last_price}
            note = f"[paper] opened {symbol}: qty {qty:.6f} @ {last_price:.4f}"
        elif status == "Sell" and symbol in self.paper_positions:
            pos = self.paper_positions[symbol]
            proceeds = pos["qty"] * last_price
            spent = pos["qty"] * pos["entry"]
            pnl = proceeds - spent
            self.paper_cash += proceeds
            self.paper_pnl += pnl
            del self.paper_positions[symbol]
            note = f"[paper] closed {symbol}: pnl {pnl:.2f} | cash {self.paper_cash:.2f}"
        QTimer.singleShot(0, self.update_paper_labels)
        return note

    def update_paper_labels(self):
        self.paper_balance_label.setText(f"Paper cash: {self.paper_cash:,.2f} USDT")
        self.paper_pnl_label.setText(f"Paper PnL: {self.paper_pnl:,.2f} USDT")

    def refresh_portfolio(self):
        api_key = self.api_key_input.text().strip()
        api_secret = self.api_secret_input.text().strip()
        if not api_key or not api_secret:
            self.portfolio_view.setPlainText("API key/secret missing. Nothing fetched.")
            return
        try:
            exchange = ccxt.binance({"apiKey": api_key, "secret": api_secret})
            balances = exchange.fetch_balance()
            summary_lines = []
            for asset, total in balances.get("total", {}).items():
                if total and total > 0:
                    free = balances.get("free", {}).get(asset, 0)
                    used = balances.get("used", {}).get(asset, 0)
                    summary_lines.append(
                        f"{asset}: total {total:.4f} | free {free:.4f} | locked {used:.4f}"
                    )
            if not summary_lines:
                self.portfolio_view.setPlainText("No non-zero balances found (read-only).")
            else:
                self.portfolio_view.setPlainText("\n".join(summary_lines))
        except Exception as exc:
            self.portfolio_view.setPlainText(f"Balance fetch failed: {exc}")

    def fetch_dominance(self, symbol):
        # Map common trading pairs to CoinGecko symbols
        symbol_mapping = {
            "BTC/USDT": "btc",
            "ETH/USDT": "eth",
            "LTC/USDT": "ltc",
            "BNB/USDT": "bnb",
            "SOL/USDT": "sol",
            "XRP/USDT": "xrp",
            "DOGE/USDT": "doge",
        }
        try:
            response = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
            response.raise_for_status()
            data = response.json()
            market_cap_percentage = data.get("data", {}).get("market_cap_percentage", {})
            cg_symbol = symbol_mapping.get(symbol)
            if cg_symbol:
                return market_cap_percentage.get(cg_symbol)
        except Exception as exc:
            print(f"Dominance fetch error for {symbol}: {exc}")
        return None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme="dark_blue.xml")
    bot_app = CryptoBot()
    bot_app.show()
    sys.exit(app.exec_())
