#!/usr/bin/env python3
"""
Test script to simulate a signal without waiting for Discord.
Run with: python test_signal.py

Make sure DRY_RUN=true in your .env for safe testing!
"""

import time
from config import (
    BYBIT_API_KEY, BYBIT_API_SECRET, BYBIT_TESTNET, RECV_WINDOW,
    QUOTE, DRY_RUN, STATE_FILE, LOG_LEVEL
)
from bybit_v5 import BybitV5
from signal_parser import parse_signal, signal_hash
from state import load_state, save_state
from trade_engine import TradeEngine
import logging

import sys

# Setup logger
log = logging.getLogger("test")
log.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
h = logging.StreamHandler(sys.stdout)
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")
h.setFormatter(fmt)
log.handlers[:] = [h]

# ============================================================
# AO Trading Signal Format (Embed-style)
# ============================================================
# Test with DCA:
TEST_SIGNAL_WITH_DCA = """
📊 NEW SIGNAL • OL • Entry $0.01740

AO Trading • New Trade Signal
🔴 SHORT SIGNAL - OL/USDT
Leverage: 25x • Trader: haseeb1111

📊 Entry: 0.01740 ⏳ Pending

🎯 Profit Targets:
🎯 TP1: 0.01719 → NEXT
⏳ TP2: 0.01698 Pending
⏳ TP3: 0.01670 Pending
⏳ TP4: 0.01601 Pending

📊 DCA Levels:
⏳ DCA1: 0.01800 Pending

🛡️ Stop Loss: 0.01846

📊 TRADE NOW:
ByBit • MEXC • Blofin • Bitget

AO Trading • Trade Together. Win Together. 🚀
"""

# Test without DCA:
TEST_SIGNAL_NO_DCA = """
📊 NEW SIGNAL • BTC • Entry $42500.00

AO Trading • New Trade Signal
🟢 LONG SIGNAL - BTC/USDT
Leverage: 10x • Trader: haseeb1111

📊 Entry: 42500.00 ⏳ Pending

🎯 Profit Targets:
🎯 TP1: 42800.00 → NEXT
⏳ TP2: 43100.00 Pending
⏳ TP3: 43500.00 Pending

🛡️ Stop Loss: 41800.00

AO Trading • Trade Together. Win Together. 🚀
"""

# Default test signal (with DCA)
TEST_SIGNAL = TEST_SIGNAL_WITH_DCA

def main():
    print("="*60)
    print("SIGNAL TEST SCRIPT")
    print(f"DRY_RUN: {DRY_RUN}")
    print("="*60)

    if not DRY_RUN:
        confirm = input("\n⚠️  DRY_RUN is FALSE! This will place REAL orders!\nType 'YES' to continue: ")
        if confirm != "YES":
            print("Aborted.")
            return

    # Parse the signal
    print("\n1. Parsing signal...")
    sig = parse_signal(TEST_SIGNAL, quote=QUOTE)

    if not sig:
        print("❌ Failed to parse signal!")
        return

    print(f"   Symbol: {sig['symbol']}")
    print(f"   Side: {sig['side']}")
    print(f"   Trigger: {sig['trigger']}")
    print(f"   TPs: {sig['tp_prices']}")
    print(f"   DCAs: {sig['dca_prices']}")
    print(f"   SL: {sig['sl_price']}")

    # Initialize
    print("\n2. Connecting to Bybit...")
    bybit = BybitV5(BYBIT_API_KEY, BYBIT_API_SECRET, testnet=BYBIT_TESTNET, recv_window=RECV_WINDOW)
    st = load_state(STATE_FILE)
    engine = TradeEngine(bybit, st, log)

    # Check current price
    print("\n3. Checking market...")
    try:
        last_price = bybit.last_price("linear", sig['symbol'])
        print(f"   Current price: {last_price}")
        print(f"   Trigger price: {sig['trigger']}")
    except Exception as e:
        print(f"   ⚠️  Could not get price: {e}")
        print("   (Symbol might not exist on Bybit)")
        return

    # Place entry
    print("\n4. Placing conditional entry...")
    trade_id = f"{sig['symbol']}|{sig['side']}|{int(time.time())}"

    try:
        oid = engine.place_conditional_entry(sig, trade_id)
        if oid:
            print(f"   ✅ Entry placed! Order ID: {oid}")

            # Store trade
            st.setdefault("open_trades", {})[trade_id] = {
                "id": trade_id,
                "symbol": sig["symbol"],
                "order_side": "Sell" if sig["side"] == "sell" else "Buy",
                "pos_side": "Short" if sig["side"] == "sell" else "Long",
                "trigger": float(sig["trigger"]),
                "tp_prices": sig.get("tp_prices") or [],
                "tp_splits": None,
                "dca_prices": sig.get("dca_prices") or [],
                "sl_price": sig.get("sl_price"),
                "entry_order_id": oid,
                "status": "pending",
                "placed_ts": time.time(),
                "base_qty": engine.calc_base_qty(sig["symbol"], float(sig["trigger"])),
                "raw": sig.get("raw", ""),
            }
            save_state(STATE_FILE, st)
            print(f"   Trade saved to state")
        else:
            print("   ❌ Entry not placed (price too far or other condition)")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "="*60)
    print("Test complete!")
    if DRY_RUN:
        print("(DRY_RUN mode - no real orders placed)")
    print("="*60)

if __name__ == "__main__":
    main()
