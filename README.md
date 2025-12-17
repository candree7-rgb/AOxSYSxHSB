### AO Trading Bot (Bybit Direct)

Automated trading bot that reads AO Trading signals from Discord and executes them on Bybit.

## Features

- Discord Signal (Embeds) -> Bybit conditional entry
- 3 Take-Profit levels with configurable splits (default: 30/30/30)
- 0-1 DCA per signal (conditional add)
- SL moves to Breakeven after TP1 fill (via WebSocket)
- Trailing stop activates after TP3 hit
- Entry expires after configurable time
- Google Sheets export for trade statistics

## Signal Format (AO Trading)

```
📊 NEW SIGNAL • OL • Entry $0.01740

🔴 SHORT SIGNAL - OL/USDT
Leverage: 25x • Trader: haseeb1111

📊 Entry: 0.01740 ⏳ Pending

🎯 TP1: 0.01719 → NEXT
⏳ TP2: 0.01698 Pending
⏳ TP3: 0.01670 Pending

📊 DCA Levels:
⏳ DCA1: 0.01800 Pending

🛡️ Stop Loss: 0.01846
```

## Setup

1. Copy environment config:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   - `DISCORD_TOKEN` - Discord bot token
   - `CHANNEL_ID` - Channel ID to monitor
   - `BYBIT_API_KEY` / `BYBIT_API_SECRET` - Bybit API credentials

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

## Testing

Test signal parsing without live trading:
```bash
python test_signal.py
```

Make sure `DRY_RUN=true` in your `.env` for safe testing!

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `LEVERAGE` | 5 | Trade leverage |
| `RISK_PCT` | 5 | % of equity per trade |
| `TP_SPLITS` | 30,30,30 | Position % per TP level |
| `DCA_QTY_MULTS` | 1.5 | DCA size multiplier |
| `TRAIL_AFTER_TP_INDEX` | 3 | Start trailing after TPn |
| `DRY_RUN` | true | Simulation mode |

See `.env.example` for full configuration options.
