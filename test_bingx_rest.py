import requests
import time

def get_bingx_prices():
    """
    Простой тест через REST API BingX для получения текущих цен.
    """
    coins = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    base_url = "https://open-api.bingx.com"
    endpoint = "/openApi/spot/v1/ticker/price"
    
    print(f"Запуск REST-теста BingX для монет: {', '.join(coins)}")
    print("-" * 50)
    
    try:
        for coin in coins:
            params = {"symbol": coin}
            response = requests.get(base_url + endpoint, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    # Проверяем структуру data['data']
                    ticker_data = data.get("data")
                    
                    price = None
                    if isinstance(ticker_data, list) and len(ticker_data) > 0:
                        # Обработка структуры [{'trades': [{'price': '...'}]}]
                        trades = ticker_data[0].get("trades")
                        if isinstance(trades, list) and len(trades) > 0:
                            price = trades[0].get("price")
                        else:
                            # На случай если структура просто [{'price': '...'}]
                            price = ticker_data[0].get("price")
                    elif isinstance(ticker_data, dict):
                        price = ticker_data.get("price")
                    
                    if price:
                        print(f"[{time.strftime('%H:%M:%S')}] {coin}: {price}")
                    else:
                        print(f"Не удалось найти цену для {coin}. Структура ответа: {ticker_data}")
                else:
                    print(f"Ошибка BingX API для {coin}: {data.get('msg')}")
            else:
                print(f"Ошибка сети: {response.status_code}")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    
    print("-" * 50)
    print("Тест завершен.")

if __name__ == "__main__":
    get_bingx_prices()
