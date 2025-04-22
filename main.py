{\rtf1\ansi\ansicpg936\cocoartf2821
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 # \uc0\u9989  OKX \u31574 \u30053 \u26426 \u22120 \u20154  v6.3.2\
import requests\
import pandas as pd\
import numpy as np\
from telegram import Update, ReplyKeyboardMarkup\
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters\
\
BOT_TOKEN = '7592763653:AAHq-Mm3b3WXJObiJ6Iin0sZ4QQ84oXD0x8'\
\
default_coin_list = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "DOGE-USDT-SWAP"]\
\
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    keyboard = [['\uc0\u55357 \u56522  \u31574 \u30053 Top5\u20998 \u26512 ', '\u55357 \u56960  WCT \u19987 \u23646 \u20998 \u26512 ']]\
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)\
    await update.message.reply_text("\uc0\u9989  \u33756 \u21333 \u24050 \u26356 \u26032 \u65292 \u35831 \u36873 \u25321 \u25805 \u20316 \u65306 ", reply_markup=reply_markup)\
\
async def top_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    await update.message.reply_text("\uc0\u55357 \u56522  \u27491 \u22312 \u20998 \u26512 \u25104 \u20132 \u37327 Top10 + \u28072 \u36300 \u24133 Top10\u24065 \u31181 \u65292 \u35831 \u31245 \u20505 ...")\
    try:\
        vol_top10 = get_top_volume_symbols()\
        change_top10 = get_top_change_symbols(limit=10, exclude_list=vol_top10)\
        coin_list = list(set(vol_top10 + change_top10 + default_coin_list))\
    except:\
        coin_list = default_coin_list\
\
    results = []\
    checked = set()\
    for coin in coin_list:\
        if coin in checked: continue\
        checked.add(coin)\
        msg, score, direction = analyze_coin(coin)\
        if score >= 2 and msg:\
            results.append((score, msg))\
\
    if results:\
        results.sort(reverse=True, key=lambda x: x[0])\
        for m in [x[1] for x in results[:5]]:\
            await update.message.reply_text(m)\
    else:\
        await update.message.reply_text("\uc0\u55358 \u56596  \u24403 \u21069 \u26242 \u26080 \u20540 \u24471 \u25512 \u33616 \u30340 \u31574 \u30053 \u65292 \u31245 \u21518 \u20877 \u26469 \u30475 \u30475 \u21543 ~")\
\
async def wct_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    await update.message.reply_text("\uc0\u55357 \u56960  \u27491 \u22312 \u20998 \u26512  WCT-USDT-SWAP\u65292 \u35831 \u31245 \u20505 ...")\
    msg, score, direction = analyze_coin("WCT-USDT-SWAP")\
    if msg:\
        await update.message.reply_text(msg)\
    else:\
        await update.message.reply_text("\uc0\u55357 \u56853  \u26242 \u26080 \u26377 \u25928 \u31574 \u30053 \u24314 \u35758 ")\
\
def get_top_volume_symbols(limit=10):\
    url = "https://www.okx.com/api/v5/market/tickers"\
    params = \{"instType": "SWAP"\}\
    try:\
        res = requests.get(url, params=params).json()\
        if res.get("code") != "0": return []\
        data = res["data"]\
        sorted_data = sorted(data, key=lambda x: float(x["volCcy24h"]), reverse=True)\
        return [item["instId"] for item in sorted_data if item["instId"].endswith("USDT-SWAP")][:limit]\
    except: return []\
\
def get_top_change_symbols(limit=10, exclude_list=None):\
    url = "https://www.okx.com/api/v5/market/tickers"\
    params = \{"instType": "SWAP"\}\
    try:\
        res = requests.get(url, params=params).json()\
        if res.get("code") != "0": return []\
        data = res["data"]\
        filtered = [item for item in data if item["instId"].endswith("USDT-SWAP") and item["instId"] not in exclude_list]\
        sorted_data = sorted(filtered, key=lambda x: abs(float(x["chgPct"])), reverse=True)\
        return [item["instId"] for item in sorted_data[:limit]]\
    except: return []\
\
def get_ohlc(instId, bar='15m', limit=50):\
    url = "https://www.okx.com/api/v5/market/candles"\
    params = \{"instId": instId, "bar": bar, "limit": limit\}\
    res = requests.get(url, params=params).json()\
    if res.get("code") != "0" or not res.get("data"): return []\
    return res["data"][::-1]\
\
def format_price(p):\
    return str(round(p, 6)).rstrip("0").rstrip(".") if p >= 0.01 else f"\{p:.8f\}".rstrip("0")\
\
def gaussian_filter(data, window=5):\
    weights = np.exp(-0.5 * (np.arange(-window, window + 1) / 2) ** 2)\
    weights /= weights.sum()\
    return np.convolve(data, weights, mode='same')[-1]\
\
def get_trend_direction(closes):\
    series = pd.Series(closes)\
    ema12 = series.ewm(span=12).mean()\
    ema26 = series.ewm(span=26).mean()\
    macd_line = ema12 - ema26\
    signal = macd_line.ewm(span=9).mean()\
    if macd_line.iloc[-1] > signal.iloc[-1]: return '\uc0\u22810 '\
    elif macd_line.iloc[-1] < signal.iloc[-1]: return '\uc0\u31354 '\
    return '\uc0\u38663 \u33633 '\
\
def analyze_coin(instId):\
    try:\
        k15 = get_ohlc(instId, '15m', 50)\
        k1h = get_ohlc(instId, '1H', 50)\
        k1d = get_ohlc(instId, '1D', 50)\
        if not k15 or not k1h or not k1d: return None, 0, None\
\
        closes = [float(x[4]) for x in k15]\
        highs = [float(x[2]) for x in k15]\
        lows = [float(x[3]) for x in k15]\
        price = closes[-1]\
        coin = instId.split('-')[0]\
\
        close_series = pd.Series(closes)\
        ema12 = close_series.ewm(span=12).mean()\
        ema26 = close_series.ewm(span=26).mean()\
        macd_line = ema12 - ema26\
        signal_line = macd_line.ewm(span=9).mean()\
        macd = macd_line.iloc[-1]\
        signal = signal_line.iloc[-1]\
\
        delta = close_series.diff()\
        up = delta.where(delta > 0, 0)\
        down = -delta.where(delta < 0, 0)\
        avg_gain = up.rolling(14).mean()\
        avg_loss = down.rolling(14).mean()\
\
        if avg_loss.dropna().empty or avg_gain.dropna().empty:\
            rsi = 50\
        else:\
            last_loss = avg_loss.dropna().iloc[-1]\
            last_gain = avg_gain.dropna().iloc[-1]\
            if last_loss == 0:\
                rsi = 100\
            elif last_gain == 0:\
                rsi = 0\
            else:\
                rs = last_gain / last_loss\
                rsi = 100 - (100 / (1 + rs))\
\
        ema20 = close_series.ewm(span=20).mean().iloc[-1]\
\
        score = 0\
        reasons = []\
        if macd > signal: score += 1; reasons.append("MACD\uc0\u37329 \u21449 ")\
        if rsi < 30: score += 1; reasons.append("RSI\uc0\u20302 \u20301 ")\
        if price > ema20: score += 1; reasons.append("\uc0\u20215 \u26684 \u39640 \u20110 EMA20")\
\
        trend_15m = get_trend_direction(closes)\
        trend_1h = get_trend_direction([float(x[4]) for x in k1h])\
        trend_1d = get_trend_direction([float(x[4]) for x in k1d])\
        if trend_15m == trend_1h == trend_1d and trend_15m in ['\uc0\u22810 ', '\u31354 ']:\
            score += 1\
            reasons.append(f"\uc0\u22810 \u21608 \u26399 \u20849 \u25391 \u65288 \{trend_15m\}\u22836 \u36235 \u21183 \u65289 ")\
\
        g_trend = gaussian_filter(closes)\
        if g_trend > closes[-2]: score += 1; reasons.append("Gaussian\uc0\u36235 \u21183 \u21521 \u19978 ")\
\
        direction = "\uc0\u24320 \u22810 " if macd > signal and rsi < 60 else "\u24320 \u31354 "\
        entry = round(price * (0.995 if direction == "\uc0\u24320 \u22810 " else 1.005), 6)\
        tp = round(price * (1.012 if direction == "\uc0\u24320 \u22810 " else 0.988), 6)\
        sl = round(price * (0.985 if direction == "\uc0\u24320 \u22810 " else 1.015), 6)\
        limit_range = f"\{format_price(entry * 0.998)\} ~ \{format_price(entry * 1.002)\}"\
        tp_pct = f"+\{round((tp - entry) / entry * 100, 2)\}%"\
        sl_pct = f"-\{round((entry - sl) / entry * 100, 2)\}%"\
\
        msg = f"""\uc0\u55357 \u56524  \{coin\}\
\uc0\u24314 \u35758 \u65306 \{direction\}\u65288 \u38480 \u20215 \u25346 \u21333 \u65289 \
\uc0\u24403 \u21069 \u20215 \u65306 \{format_price(price)\}\
\uc0\u25346 \u21333 \u20215 \u65306 \{format_price(entry)\}\
\uc0\u27490 \u30408 \u65306 \{format_price(tp)\}\u65288 \{tp_pct\}\u65289 \u65292 \u27490 \u25439 \u65306 \{format_price(sl)\}\u65288 \{sl_pct\}\u65289 \
\uc0\u25346 \u21333 \u21306 \u38388 \u65306 \{limit_range\}\
\uc0\u55358 \u56800  \u29702 \u30001 \u65306 \{', '.join(reasons)\}"""\
        return msg, score, direction\
    except Exception as e:\
        print(f"\uc0\u20998 \u26512 \u22833 \u36133 \u65288 \{instId\}\u65289 \u65306 \{e\}")\
        return None, 0, None\
\
if __name__ == '__main__':\
    print("\uc0\u9989  \u27491 \u22312 \u21551 \u21160  Bot...")\
    try:\
        app = ApplicationBuilder().token(BOT_TOKEN).build()\
        app.add_handler(CommandHandler("start", start))\
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex("\uc0\u31574 \u30053 Top5\u20998 \u26512 "), top_strategy))\
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex("WCT \uc0\u19987 \u23646 \u20998 \u26512 "), wct_strategy))\
        print("\uc0\u55358 \u56598  \u31574 \u30053 \u26426 \u22120 \u20154 \u24050 \u19978 \u32447 \u65292 \u31561 \u24453  Telegram \u25351 \u20196 ...")\
        app.run_polling()\
    except Exception as e:\
        print(f"\uc0\u10060  \u21551 \u21160 \u22833 \u36133 \u65306 \{e\}")\
}