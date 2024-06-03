import re

from binance.enums import SIDE_BUY, SIDE_SELL


def parse_future_message(message: str) -> (
        tuple)[str, str | None, str | None, float | None, float | None, float | None]:
    """
    Parse the Discord message to extract trading signals and commands.
    """
    try:
        symbol_pattern = r'\$(\w+)'
        side_pattern = r'(LONG|SHORT)'
        entry_pattern = r'Entry\s\d\s=\s\$([\d.]+)'
        stoploss_pattern = r'Stoploss:\s4H\sClose\s(Above|Below)\s\$([\d.]+)'
        target_pattern = r'Target:\s\$([\d.]+)'
        close_order_pattern = r'Close\sOrder'
        change_stoploss_pattern = r'Change\sStoploss\s=\s\$([\d.]+)'

        symbol_match = re.search(symbol_pattern, message)
        side_match = re.search(side_pattern, message)
        entry_matches = re.findall(entry_pattern, message)
        stoploss_match = re.search(stoploss_pattern, message)
        target_match = re.search(target_pattern, message)
        close_order_match = re.search(close_order_pattern, message)
        change_stoploss_match = re.search(change_stoploss_pattern, message)

        if close_order_match:
            return 'CLOSE_ORDER', None, None, None, None, None

        if change_stoploss_match:
            new_stoploss_price = float(change_stoploss_match.group(1))
            return 'CHANGE_STOPLOSS', None, None, new_stoploss_price, None, None

        if not (symbol_match and side_match and entry_matches and stoploss_match and target_match):
            raise ValueError("Message format is incorrect or missing information")

        symbol = symbol_match.group(1).upper() + 'USDT'
        side = SIDE_BUY if side_match.group(1) == 'LONG' else SIDE_SELL
        entry_prices = [float(price) for price in entry_matches]
        stoploss_price = float(stoploss_match.group(2))
        target_price = float(target_match.group(1))

        entry_price = entry_prices[0]

        return 'TRADE_SIGNAL', symbol, side, entry_price, stoploss_price, target_price

    except Exception as e:
        raise ValueError(f"Error parsing future message: {e}")
