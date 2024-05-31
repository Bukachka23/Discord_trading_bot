from enum import Enum


class EnvVariables(Enum):
    DISCORD_BOT_TOKEN = 'DISCORD_BOT_TOKEN'
    BINANCE_API_KEY = 'BINANCE_API_KEY'
    BINANCE_API_SECRET = 'BINANCE_API_SECRET'


class OrderType(Enum):
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'


class TradingConstants(Enum):
    LEVERAGE = 5
    RISK_PERCENTAGE = 0.05
