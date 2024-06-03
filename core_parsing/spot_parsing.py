import re
from typing import Dict, Any


def parse_spot_message(message: str) -> Dict[str, Any]:
    """
    Parse the Discord message to extract spot trading signals.
    """
    try:
        match = re.search(r'\$(\w+)', message)
        symbol = match.group(1) + 'USDT' if match else None
        entries = re.findall(r'Entry \d+ = \$([\d.]+)', message)
        stop_loss_match = re.search(r'Stoploss:.*Below \$([\d.]+)', message)
        stop_loss_price = float(stop_loss_match.group(1)) if stop_loss_match else None
        final_target_match = re.search(r'Final Target: \$([\d.]+)', message)
        final_target_price = float(final_target_match.group(1)) if final_target_match else None

        return {
            'symbol': symbol,
            'entries': [float(entry) for entry in entries],
            'stop_loss_price': stop_loss_price,
            'final_target_price': final_target_price
        }

    except Exception as e:
        raise ValueError(f"Error parsing spot message: {e}")
