import requests
import json

def get_top_performers():
    """바이낸스 상위 상승 코인들 조회"""
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url)
        data = response.json()
        
        # USDT 페어만 필터링
        usdt_pairs = []
        for ticker in data:
            if (ticker['symbol'].endswith('USDT') and 
                float(ticker['priceChangePercent']) > 0 and
                float(ticker['quoteVolume']) > 100000):
                usdt_pairs.append(ticker)
        
        # 상승률로 정렬
        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']), reverse=True)
        
        print("🔥 바이낸스 24시간 상위 상승 코인 (Top 20):")
        print("-" * 60)
        
        for i, ticker in enumerate(sorted_pairs[:20], 1):
            symbol = ticker['symbol']
            change = float(ticker['priceChangePercent'])
            volume = float(ticker['quoteVolume']) / 1000000
            price = float(ticker['lastPrice'])
            
            print(f"{i:2d}. {symbol:<12} +{change:6.2f}% | ${price:10.6f} | Vol: ${volume:6.1f}M")
        
        return [t['symbol'] for t in sorted_pairs[:20]]
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return []

if __name__ == "__main__":
    get_top_performers()
