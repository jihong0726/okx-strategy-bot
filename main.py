import requests
import pandas as pd
import numpy as np
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = '7592763653:AAHq-Mm3b3WXJObiJ6Iin0sZ4QQ84oXD0x8'
default_coin_list = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "DOGE-USDT-SWAP"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['📊 策略Top5分析', '🚀 WCT 专属分析']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("✅ 菜单已更新，请选择操作：", reply_markup=reply_markup)

async def top_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 正在分析成交量Top10 + 涨跌幅Top10币种，请稍候...")
    try:
        vol_top10 = get_top_volume_symbols()
        change_top10 = get_top_change_symbols(limit=10, exclude_list=vol_top10)
        coin_list = list(set(vol_top10 + change_top10 + default_coin_list))
    except:
        coin_list = default_coin_list

    results = []
    checked = set()
    for coin in coin_list:
        if coin in checked: continue
        checked.add(coin)
        msg, score, direction = analyze_coin(coin)
        if score >= 2 and msg:
            results.append((score, msg))

    if results:
        results.sort(reverse=True, key=lambda x: x[0])
        for m in [x[1] for x in results[:5]]:
            await update.message.reply_text(m)
    else:
        await update.message.reply_text("🤔 当前暂无值得推荐的策略，稍后再来看看吧~")

async def wct_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 正在分析 WCT-USDT-SWAP，请稍候...")
    msg, score, direction = analyze_coin("WCT-USDT-SWAP")
    if msg:
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("😶 当前暂未发现明显信号，可稍后再观察。")

def get_top_volume_symbols(limit=10):
    try:
        url = "https://www.okx.com/api/v5/market/tickers"
        res = requests.get(url, params={"instType": "SWAP"}).json()
        data = res.get("data", [])
        return [x["instId"] for x in sorted(data, key=lambda x: float(x["volCcy24h"]), reverse=True)
                if x["instId"].endswith("USDT-SWAP")][:limit]
    except:
        return []

def get_top_change_symbols(limit=10, exclude_list=None):
    try:
        exclude_list = exclude_list or []
        url = "https://www.okx.com/api/v5/market/tickers"
        res = requests.get(url, params={"instType": "SWAP"}).json()
        data = res.get("data", [])
        filtered = [x for x in data if x["instId"].endswith("USDT-SWAP") and x["instId"] not in exclude_list]
        sorted_data = sorted(filtered, key=lambda x: abs(float(x["chgPct"])), reverse=True)
        return [x["instId"] for x in sorted_data[:limit]]
    except:
        return []

def get_ohlc(instId, bar='15m', limit=50):
    url = "https://www.okx.com/api/v5/market/candles"
    res = requests.get(url, params={"instId": instId, "bar": bar, "limit": limit}).json()
    if res.get("code") != "0" or not res.get("data"): return []
    return res["data"][::-1]

def format_price(p):
    return str(round(p, 6)).rstrip("0").rstrip(".") if p >= 0.01 else f"{p:.8f}".rstrip("0")

def gaussian_filter(data, window=5):
    weights = np.exp(-0.5 * (np.arange(-window, window + 1) / 2) ** 2)
    weights /= weights.sum()
    return np.convolve(data, weights, mode='same')[-1]

def get_trend_direction(closes):
    series = pd.Series(closes)
    ema12 = series.ewm(span=12).mean()
    ema26 = series.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9).mean()
    if macd_line.iloc[-1] > signal.iloc[-1]: return '多'
    elif macd_line.iloc[-1] < signal.iloc[-1]: return '空'
    return '震荡'

def calculate_adx(highs, lows, closes, period=14):
    high = pd.Series(highs)
    low = pd.Series(lows)
    close = pd.Series(closes)
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    return adx.iloc[-1], plus_di.iloc[-1], minus_di.iloc[-1]

def calculate_qqe(closes):
    rsi = pd.Series(closes).diff().apply(lambda x: x if x > 0 else 0).rolling(14).mean()
    smoothed_rsi = rsi.ewm(span=5).mean()
    trailing = smoothed_rsi.shift(1)
    return smoothed_rsi.iloc[-1] > trailing.iloc[-1]

def analyze_coin(instId):
    try:
        k15 = get_ohlc(instId, '15m', 50)
        k1h = get_ohlc(instId, '1H', 50)
        k1d = get_ohlc(instId, '1D', 50)
        if not k15 or not k1h or not k1d: return None, 0, None

        closes = [float(x[4]) for x in k15]
        highs = [float(x[2]) for x in k15]
        lows = [float(x[3]) for x in k15]
        price = closes[-1]
        coin = instId.split('-')[0]

        close_series = pd.Series(closes)
        ema12 = close_series.ewm(span=12).mean()
        ema26 = close_series.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        macd = macd_line.iloc[-1]
        signal = signal_line.iloc[-1]

        delta = close_series.diff()
        up = delta.where(delta > 0, 0)
        down = -delta.where(delta < 0, 0)
        avg_gain = up.rolling(14).mean()
        avg_loss = down.rolling(14).mean()

        if avg_loss.dropna().empty or avg_gain.dropna().empty:
            rsi = 50
        else:
            last_loss = avg_loss.dropna().iloc[-1]
            last_gain = avg_gain.dropna().iloc[-1]
            if last_loss == 0:
                rsi = 100
            elif last_gain == 0:
                rsi = 0
            else:
                rs = last_gain / last_loss
                rsi = 100 - (100 / (1 + rs))

        sma50 = close_series.rolling(50).mean().iloc[-1]
        sma200 = close_series.rolling(200).mean().iloc[-1] if len(close_series) >= 200 else None
        ema20 = close_series.ewm(span=20).mean().iloc[-1]

        score = 0
        reasons = []
        if macd > signal: score += 1; reasons.append("MACD金叉")
        if rsi < 30: score += 1; reasons.append("RSI低位")
        if sma200 and sma50 > sma200: score += 1; reasons.append("SMA50上穿SMA200（多头趋势）")
        if price > ema20: score += 1; reasons.append("价格高于EMA20")

        trend_15m = get_trend_direction(closes)
        trend_1h = get_trend_direction([float(x[4]) for x in k1h])
        trend_1d = get_trend_direction([float(x[4]) for x in k1d])
        if trend_15m == trend_1h == trend_1d and trend_15m in ['多', '空']:
            score += 1; reasons.append(f"多周期共振（{trend_15m}头趋势）")

        adx, plus_di, minus_di = calculate_adx(highs, lows, closes)
        if adx > 20:
            if plus_di > minus_di: score += 1; reasons.append(f"ADX强趋势：{round(adx,1)}（多头）")
            elif minus_di > plus_di: score += 1; reasons.append(f"ADX强趋势：{round(adx,1)}（空头）")

        if calculate_qqe(closes): score += 1; reasons.append("QQE模拟金叉信号")
        g_trend = gaussian_filter(closes)
        if g_trend > closes[-2]: score += 1; reasons.append("Gaussian平滑趋势向上")

        if rsi > 70 and macd < signal: reasons.append("⚠️ RSI高位 + MACD死叉")
        if rsi < 30 and macd > signal: reasons.append("⚠️ RSI低位 + MACD金叉")

        direction = "开多" if macd > signal and rsi < 60 else "开空"
        entry = round(price * (0.995 if direction == "开多" else 1.005), 6)
        tp = round(price * (1.012 if direction == "开多" else 0.988), 6)
        sl = round(price * (0.985 if direction == "开多" else 1.015), 6)

        tp_pct = f"+{round((tp - entry) / entry * 100, 2)}%" if direction == "开多" else f"-{round((entry - tp) / entry * 100, 2)}%"
        sl_pct = f"-{round((entry - sl) / entry * 100, 2)}%" if direction == "开多" else f"+{round((sl - entry) / entry * 100, 2)}%"
        limit_range = f"{format_price(entry * 0.998)} ~ {format_price(entry * 1.002)}"

        if score >= 3:
            msg = f"""📌 {coin}
建议：{direction}（限价挂单）
当前价：{format_price(price)}
挂单价：{format_price(entry)}
止盈：{format_price(tp)}（{tp_pct}），止损：{format_price(sl)}（{sl_pct}）
建议挂单区间：{limit_range}
🧠 理由：{', '.join(reasons)}"""
            return msg, score, direction
        elif score == 2:
            msg = f"""📌 {coin}
建议：关注观察（倾向：{direction}）
当前价：{format_price(price)}
预估挂单：{format_price(entry)}，止盈：{format_price(tp)}，止损：{format_price(sl)}
建议挂单区间：{limit_range}
🧠 理由：{', '.join(reasons)}"""
            return msg, score, direction
        return None, score, None
    except Exception as e:
        print(f"分析失败（{instId}）：{e}")
        return None, 0, None

if __name__ == '__main__':
    print("✅ 脚本启动中，请稍候...")
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex("策略Top5分析"), top_strategy))
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex("WCT 专属分析"), wct_strategy))
        print("🤖 策略机器人已启动，等待 Telegram 指令中...")
        app.run_polling()
    except Exception as e:
        print(f"❌ 启动失败：{e}")
