# Crypto Trading Bot - @mebularts

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#)
[![PyQt5](https://img.shields.io/badge/Desktop-PyQt5-41cd52?logo=qt&logoColor=white)](#)
[![Telegram](https://img.shields.io/badge/Telegram-@mebularts-0099ff?logo=telegram&logoColor=white)](https://t.me/mebularts)
[![License](https://img.shields.io/badge/License-MIT-000000)](LICENSE)

Open-source PyQt5 desktop bot that scans crypto pairs with ccxt + pandas-ta, scores signals, and ships rich Telegram messages (charts included). Paper trading, read-only balances, ad scheduling, and a brandable signature are built in for Developer **@mebularts**.

## Highlights
- Strategy profiles: scalp (1m), intraday (5m), swing (1h) with ccxt OHLCV.
- Indicator stack: RSI, MACD, Stochastic, Aroon, Bollinger Bands, ATR, Parabolic SAR, OBV, CoinGecko dominance.
- Multi-indicator voting, ATR-based risk score, TP/SL suggestion, dynamic refresh interval.
- Telegram delivery: media group with chart (price, RSI, MACD, Bollinger Bands) plus text summary and optional signature footer.
- Paper trading sim: risk %, cash, PnL, and position tracking in-app; real trades are never placed.
- Ads: schedule one-off campaigns from `ads.json` (text or image) with your signature appended automatically.
- UI: dark theme via `qt_material`, pair search, select/deselect all, developer badge linking to GitHub.

## Stack
Python 3.10+, PyQt5, qt_material, ccxt, pandas, pandas-ta, matplotlib, requests, python-telegram-bot.

## Quickstart (EN)
1) Clone repo and open a terminal here.  
2) Install deps (virtualenv recommended):
   ```bash
   pip install -r requirements.txt
   ```
3) Copy configs:
   ```bash
   copy user.example.json user.json
   copy ads.example.json ads.json
   ```
4) Edit `user.json`: set `bot_token`, `chat_id`, pick `profile`, adjust paper trading, and set your `signature` text.  
5) Run the app:
   ```bash
   python main.py
   ```
6) In the UI: choose pairs (search supported), tweak RSI toggles, optionally enable paper trading, then press **Start**. Ads send based on `ads.json`.

## Hizi TR rehber
1) `pip install -r requirements.txt`  
2) `user.example.json` -> `user.json`, `ads.example.json` -> `ads.json`  
3) `user.json` icinde `bot_token`/`chat_id`, profil, paper ayarlari, `signature` metni doldur.  
4) Calistir: `python main.py`, pariteleri sec, RSI seceneklerini ayarla, gerekirse paper trading'i ac, **Start**'a bas.  
5) Reklamlar `ads.json` takvimine gore gonderilir, mesajlara imza eklenir.

## Config reference (`user.json`)
| Key | Description |
| --- | --- |
| `bot_token`, `chat_id` | Telegram bot token and target chat. |
| `interval` | Base seconds between cycles (dynamic interval adjusts via ATR%). |
| `message_interval` | Legacy pacing; main cadence comes from dynamic interval. |
| `api_key`, `api_secret` | Exchange keys for read-only balance view (no trading). |
| `profile` | `scalp` \| `intraday` \| `swing` timeframe presets. |
| `paper_start_balance`, `paper_risk_pct` | Paper trading bankroll and per-trade risk %. |
| `signature` | Optional footer appended to every signal/ad (branding). |
| `rsi_thresholds` | Enable/disable RSI-related statuses considered in voting. |
| `selected_coins` | Default pairs to preselect in the UI. |

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
- When `active` is true and the scheduled time is reached, the ad is sent once and then deactivated.
- `image_path` optional; without it, the ad is text-only.
- Signature from `user.json` is appended automatically.

## UI flow
- **Developer badge:** clickable link to @mebularts GitHub profile.  
- **Settings:** Telegram token/chat id, base interval, optional exchange keys, profile selector, signature field.  
- **RSI toggles:** choose which RSI signals count toward Buy/Sell/Neutral.  
- **Pairs:** search box + checkbox list, select/deselect all.  
- **Start:** saves config, starts async loop, sends Telegram messages for selected pairs.  
- **Portfolio:** read-only balances via ccxt when API keys are provided.  
- **Paper trading:** simulates entries/exits using risk %, updates cash/PnL labels live.  
- **Ads timer:** checks `ads.json` every minute and dispatches scheduled campaigns.

## Safety and notes
- Real trades are never placed; exchange keys are only used for balance fetch.  
- Keep `user.json` and `ads.json` out of version control (already in `.gitignore`).  
- CoinGecko dominance fetch requires internet; failures are logged but non-blocking.  
- Add your own UI screenshot (e.g., `docs/screenshot.png`) if you want a visual preview in the README.

## Contribute
Issues and PRs are welcome. If you spot a regression or want a new indicator/profile, open an issue with details.
