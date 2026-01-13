# Crypto Trading Bot - @mebularts

Free, open-source PyQt5 desktop bot that analyzes crypto pairs with ccxt + pandas-ta, then sends Telegram updates (text + chart). No license gate, no embedded secrets, fully config-driven, and branded for Developer **@mebularts**.

## Features
- Strategy profiles: `scalp` (1m), `intraday` (5m), `swing` (1h) with ccxt OHLCV pulling.
- Indicator stack: RSI, MACD, Stochastic, Aroon, Bollinger Bands, ATR, Parabolic SAR, OBV + market dominance (CoinGecko).
- Multi-indicator voting, ATR-based risk score, TP/SL suggestion, dynamic refresh interval.
- Paper trading simulator (per-trade risk %, cash, PnL, positions) plus read-only portfolio balances via API key/secret.
- Telegram delivery with media group (chart + metrics) and a customizable signature (`Built by @mebularts`) on every message/ad.
- Configurable scheduled ads from `ads.json`; optional images per campaign.
- Desktop UI themed by `qt_material`, pair search, select-all/deselect-all, and a developer badge linking to GitHub.

## Stack
Python 3.10+, PyQt5, qt_material, ccxt, pandas, pandas-ta, matplotlib, requests, python-telegram-bot.

## Quickstart (English)
1. Clone the repo and open a terminal at the repo root.
2. (Recommended) create/activate a virtualenv, then install deps:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy configs: `examples/user.example.json` -> `examples/user.json`; `examples/ads.example.json` -> `examples/ads.json`.
4. Edit `examples/user.json` with your Telegram bot token/chat id, profile, paper settings, and `signature` text.
5. Run the app from repo root: `python examples/main.py` (or `python main.py` if this folder is the root).
6. In the UI: pick pairs (search supported), adjust RSI toggles, optionally enable paper trading, then press **Start**. Ads send automatically based on `ads.json`.

## Kurulum (Turkce Hizli Rehber)
1. Depoyu klonla, kokte terminal ac.
2. (Onerilir) sanal ortam kur ve bagimliliklari yukle: `pip install -r requirements.txt`
3. Konfigleri kopyala: `examples/user.example.json` -> `examples/user.json`; `examples/ads.example.json` -> `examples/ads.json`
4. `examples/user.json` icinde Telegram `bot_token`/`chat_id`, profil, paper ayarlari ve `signature` metnini doldur.
5. Calistir: `python examples/main.py` (veya bu klasor kokse `python main.py`).
6. Arayuzde pariteleri sec, RSI seceneklerini ayarla, istersen paper trading'i ac, **Start**'a bas. Reklamlar `ads.json` zamanlamasiyla gonderilir.

## Configuration Reference (`user.json`)
```json
{
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_CHAT_ID",
    "interval": 900,
    "message_interval": 30,
    "api_key": "YOUR_EXCHANGE_KEY",
    "api_secret": "YOUR_EXCHANGE_SECRET",
    "profile": "swing",
    "paper_start_balance": 10000,
    "paper_risk_pct": 5,
    "signature": "Built by @mebularts (open source)",
    "rsi_thresholds": { "buy": true, "sell": true, "neutral": true, "potential_buy": true, "potential_sell": true },
    "selected_coins": ["BTC/USDT", "ETH/USDT"]
}
```
- `interval`: base seconds between cycles; dynamic interval shrinks/expands based on ATR%.
- `message_interval`: legacy spacing between messages; primary pacing uses the dynamic interval per pair.
- `signature`: optional footer appended to every Telegram signal/ad to keep your brand in the message.
- `rsi_thresholds`: toggle which RSI-related statuses are considered for Buy/Sell/Neutral.
- API keys are only used for read-only balance queries; trades are **not** executed.

## Ads (`ads.json`)
```json
{
  "ads": [
    {
      "title": "Sample Campaign",
      "description": "This is a placeholder ad message.",
      "image_path": "path/to/optional-image.png",
      "link": "https://example.com",
      "active": false,
      "schedule": { "date": "2024-12-31", "time": "23:59:00" }
    }
  ]
}
```
- When `active` is true and `date` + `time` are reached, the ad is sent once and then marked inactive.
- `image_path` is optional; without it, the ad is text-only.
- Signature from `user.json` is appended automatically.

## UI Map / Workflow
- **Developer badge:** top label links to @mebularts GitHub profile.
- **Settings:** Telegram token/chat id, base interval, optional exchange API key/secret, profile selector, message signature field.
- **RSI toggles:** choose which RSI signals can count toward Buy/Sell/Neutral.
- **Pair picker:** search box plus checkboxes for all exchange pairs; select/deselect all buttons.
- **Start:** saves `user.json`, spawns the async bot loop, and begins sending messages for selected pairs.
- **Portfolio:** read-only balances fetched with your API key/secret; shows non-zero assets.
- **Paper trading:** simulate entries/exits using per-trade risk %; cash/PnL labels update live.
- **Ads timer:** background timer checks `ads.json` every minute.

## Telegram Output
- Signals: multi-line text covering profile, status, RSI, vote counts, MACD/Stoch/Aroon, Bollinger Bands, OBV, ATR, dominance, volume, PSAR, TP/SL, next check, and paper trade notes (if enabled). A chart image (close, RSI, MACD, Bollinger Bands) is sent as a media group.
- Ads: title + description + link, plus your signature footer. Optional image is attached if provided.

## Safety and Notes
- Keep `user.json` and `ads.json` out of version control when publishing (covered in `.gitignore`).
- Paper trading is simulation only; no real trades are made.
- Exchange keys are used for balance reads; verify permissions are read-only.
- CoinGecko dominance fetch requires internet access; failures are logged but do not stop the bot.

## Development Tips
- Run from repo root: `python examples/main.py` (or `python main.py` if this folder is the root).
- To refresh markets or handle exchange errors, restart the app; uncaught exceptions are printed to the console.
- If matplotlib or PyQt complains about missing backends on some systems, install platform-specific Qt dependencies and retry.
