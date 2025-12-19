import re
import hashlib
from typing import Any, Dict, Optional, List

NUM = r"([0-9]+(?:\.[0-9]+)?)"

# ============================================================
# AO Trading Signal Parser (Embed format)
# ============================================================
# Example signal format:
#   🔴 SHORT SIGNAL - OL/USDT
#   Leverage: 25x • Trader: haseeb1111
#   📊 Entry: 0.01740 ⏳ Pending
#   🎯 TP1: 0.01719 → NEXT
#   ⏳ TP2: 0.01698 Pending
#   📊 DCA Levels:
#   ⏳ DCA1: 0.01800 Pending
#   🛡️ Stop Loss: 0.01846
# ============================================================

# Signal type detection
# Accept: "NEW SIGNAL", "NEW TRADE SIGNAL", "LONG SIGNAL", "SHORT SIGNAL", or "Trade Signal"
RE_NEW_SIGNAL = re.compile(r"NEW SIGNAL|NEW TRADE SIGNAL|(?:LONG|SHORT)\s+SIGNAL|Trade\s+Signal", re.I)
RE_CANCELLED = re.compile(r"TRADE CANCELLED|TRADE CLOSED", re.I)

# Side and symbol: "SHORT SIGNAL - OL/USDT" or "LONG SIGNAL - BTC/USDT"
RE_SIDE_SYMBOL = re.compile(r"(LONG|SHORT)\s+SIGNAL\s*[-–—]\s*([A-Z0-9]+)\s*/\s*([A-Z0-9]+)", re.I)

# Entry price: "Entry: 0.01740" or "Entry $0.01740" or "Entry: $0.01740"
RE_ENTRY = re.compile(r"Entry[:\s]*\$?" + NUM, re.I)

# Take Profit levels: "TP1: 0.01719" or "TP1: $0.01719"
RE_TP = re.compile(r"TP(\d+)[:\s]*\$?" + NUM, re.I)

# DCA level: "DCA1: 0.01800" or "DCA1: $0.01800" (only DCA1 supported)
RE_DCA = re.compile(r"DCA\s*#?\s*1?[:\s]*\$?" + NUM, re.I)

# Stop Loss: "Stop Loss: 0.01846" or "Stop Loss: $0.01846"
RE_SL = re.compile(r"Stop\s*Loss[:\s]*\$?" + NUM, re.I)


def parse_signal(text: str, quote: str = "USDT") -> Optional[Dict[str, Any]]:
    """Parse AO Trading signal from text.

    Args:
        text: Combined text from Discord message (content + embeds)
        quote: Expected quote currency (e.g. "USDT")

    Returns:
        Parsed signal dict or None if not a valid signal
    """
    # Must be a NEW SIGNAL
    if not RE_NEW_SIGNAL.search(text):
        return None

    # Skip cancelled/closed trades
    if RE_CANCELLED.search(text):
        return None

    # Also skip if "closed" appears as status (with hourglass emoji)
    if re.search(r"⏳\s*closed", text, re.I):
        return None

    # Parse side and symbol
    m_side = RE_SIDE_SYMBOL.search(text)
    if not m_side:
        return None

    side_word = m_side.group(1).upper()
    base = m_side.group(2).upper()
    quote_found = m_side.group(3).upper()

    # Verify quote currency matches
    if quote_found != quote.upper():
        return None

    side = "sell" if side_word == "SHORT" else "buy"
    symbol = f"{base}{quote}"

    # Parse entry price
    m_entry = RE_ENTRY.search(text)
    if not m_entry:
        return None
    trigger = float(m_entry.group(1).replace(",", ""))

    # Parse Take Profit levels (TP1, TP2, TP3, TP4, ...)
    tps: List[float] = []
    for m in RE_TP.finditer(text):
        idx = int(m.group(1))
        price = float(m.group(2).replace(",", ""))
        # Ensure list is long enough
        while len(tps) < idx:
            tps.append(0.0)
        tps[idx - 1] = price
    # Remove any zero placeholders
    tps = [p for p in tps if p > 0]

    if not tps:
        return None  # No TPs = invalid signal

    # Parse DCA (only 0-1 DCA for AO Trading)
    dcas: List[float] = []
    m_dca = RE_DCA.search(text)
    if m_dca:
        dca_price = float(m_dca.group(1).replace(",", ""))
        if dca_price > 0:
            dcas.append(dca_price)

    # Parse Stop Loss
    sl_price = None
    m_sl = RE_SL.search(text)
    if m_sl:
        sl_price = float(m_sl.group(1).replace(",", ""))

    return {
        "base": base,
        "symbol": symbol,
        "side": side,           # "buy" or "sell"
        "trigger": trigger,
        "tp_prices": tps,       # List of TP prices
        "dca_prices": dcas,     # List with 0-1 DCA price
        "sl_price": sl_price,
        "raw": text[:500],      # Keep first 500 chars for debugging
    }


def signal_hash(sig: Dict[str, Any]) -> str:
    """Generate unique hash for signal deduplication."""
    core = f"{sig.get('symbol')}|{sig.get('side')}|{sig.get('trigger')}|{sig.get('tp_prices')}|{sig.get('dca_prices')}"
    return hashlib.md5(core.encode("utf-8")).hexdigest()
