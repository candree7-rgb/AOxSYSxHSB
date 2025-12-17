import html
import re
import time
import requests
from typing import Any, Dict, List, Optional


class DiscordReader:
    """Discord channel reader with embed support for AO Trading signals."""

    def __init__(self, token: str, channel_id: str):
        self.token = token
        self.channel_id = channel_id
        self.base_url = "https://discord.com/api/v10"
        self.headers = {
            "Authorization": f"Bot {token}",
            "User-Agent": "AO-Trading-Bot/1.0",
        }

    def fetch_after(self, after_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch messages from channel after given message ID."""
        url = f"{self.base_url}/channels/{self.channel_id}/messages?limit={limit}"
        if after_id:
            url += f"&after={after_id}"

        for attempt in range(3):
            try:
                r = requests.get(url, headers=self.headers, timeout=15)

                # Handle rate limiting
                if r.status_code == 429:
                    retry_after = float(r.json().get("retry_after", 5)) + 1
                    time.sleep(retry_after)
                    continue

                r.raise_for_status()
                return r.json()

            except requests.RequestException:
                if attempt < 2:
                    time.sleep(3)
                continue

        return []

    def extract_text(self, msg: Dict[str, Any]) -> str:
        """Extract all text from message including embeds.

        Combines:
        - Regular message content
        - Embed titles, descriptions, and field values
        """
        parts = []

        # Regular message content
        content = msg.get("content", "")
        if content:
            parts.append(content)

        # Process embeds (AO Trading uses these)
        for embed in msg.get("embeds", []):
            # Embed title
            title = embed.get("title", "")
            if title:
                parts.append(title)

            # Embed description (main signal content)
            description = embed.get("description", "")
            if description:
                parts.append(description)

            # Embed fields (TP levels, DCA, etc.)
            for field in embed.get("fields", []):
                field_name = field.get("name", "")
                field_value = field.get("value", "")
                if field_name:
                    parts.append(field_name)
                if field_value:
                    parts.append(field_value)

            # Footer text
            footer = embed.get("footer", {})
            footer_text = footer.get("text", "")
            if footer_text:
                parts.append(footer_text)

        # Join all parts
        text = " | ".join(filter(None, parts))

        # Clean up Discord formatting
        text = html.unescape(text)
        # Remove markdown but keep structure
        text = re.sub(r"<@[!&]?\d+>", "", text)  # Remove mentions
        text = re.sub(r"<#\d+>", "", text)  # Remove channel mentions
        text = re.sub(r"<a?:\w+:\d+>", "", text)  # Remove custom emojis

        return text.strip()

    def message_timestamp_unix(self, msg: Dict[str, Any]) -> Optional[float]:
        """Extract Unix timestamp from Discord message ID (snowflake)."""
        try:
            msg_id = int(msg.get("id", 0))
            if msg_id:
                # Discord epoch: 2015-01-01
                discord_epoch = 1420070400000
                timestamp_ms = (msg_id >> 22) + discord_epoch
                return timestamp_ms / 1000.0
        except (ValueError, TypeError):
            pass

        # Fallback: try timestamp field
        ts_str = msg.get("timestamp")
        if ts_str:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                return dt.timestamp()
            except Exception:
                pass

        return None

    def get_latest_message_id(self) -> Optional[str]:
        """Get the ID of the latest message in the channel."""
        msgs = self.fetch_after(limit=1)
        if msgs:
            return msgs[0].get("id")
        return None
