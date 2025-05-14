import requests
import json
import time
from datetime import datetime
import pytz
from dhanhq import dhanhq

#########


ACCESS_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ5NjQ5OTkyLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwMzg0MjUxMiJ9.LCLcfpnfLCGe_SKat1HgoX03_hwRAqXTR8PWY2-etBofqYBoksIIKxyRDQMiJVXD480BsxAKRunGzh3OoHf75Q'
BASE_URL = 'https://api.dhan.co'
HEADERS = {
    'access-token': ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

client_id = "1103842512"
dhan = dhanhq(client_id , ACCESS_TOKEN)  # Replace with your actual access token




total_sellQTY = 0 
count = 1

BOT_TOKEN = "7636078690:AAG2vq4Ler0TTnDewrNQfXiX6CSLFzZZMok"
CHAT_ID = "922195607"

ist = pytz.timezone('Asia/Kolkata')
today = datetime.now(ist).date()

# Track last deactivation date
last_deactivated_date = None

def is_after_8am_ist():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    return now_ist.hour >= 8

# def is_trading_day():
#     now = datetime.now()
#     weekday = now.weekday()
#     # 0 = Monday, ..., 6 = Sunday
#     return weekday < 5  # True for Monday to Friday





def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    r = requests.post(url, data=payload)
    if r.status_code == 200:
        print("Telegram message sent.")
    else:
        print("Failed to send message:", r.text)





def enable_kill_switch():
    """ Enables kill switch """
    #https://api.dhan.co/killSwitch?killSwitchStatus=ACTIVATE
    url = f"{BASE_URL}/settings/kill-switch"
    response = requests.post('https://api.dhan.co/killSwitch?killSwitchStatus=ACTIVATE', headers=HEADERS)
    if response.status_code == 200:
        print(" Kill switch ENABLED.")
        #time.sleep(10)
        
    else:
        print(" Failed to enable kill switch:", response.text)

def disable_kill_switch():
    """ Disables kill switch """
    url = f"{BASE_URL}/killSwitch?killSwitchStatus=DEACTIVATE"
    response = requests.post(url, headers=HEADERS)
    if response.status_code == 200:
        print(" Kill switch DISABLED.")
    else:
        print(" Failed to disable kill switch:", response.text)




def get_daily_pnl():
    url = f"{BASE_URL}/positions"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        positions = response.json()
        total_realized_pnl = 0
        total_unrealized_pnl = 0

        for pos in positions:
            #print(pos)
            # Realized P&L: from closed positions
            realized = float(pos.get('realizedProfit', 0))
            # Unrealized P&L: from open positions
            unrealized = float(pos.get('unrealizedProfit', 0))

            total_realized_pnl += realized
            total_unrealized_pnl += unrealized

        total_pnl = total_realized_pnl + total_unrealized_pnl
        #print(total_realized_pnl , total_unrealized_pnl)
        # print(f"Realized P&L: ₹{total_realized_pnl}")
        # print(f"Unrealized P&L: ₹{total_unrealized_pnl}")
        # print(f"Total P&L for today: ₹{total_pnl}")
        return total_pnl
    else:
        print(f"Error fetching positions: {response.status_code} - {response.text}")
        return None




def get_today_trade_count():
    
    
    global total_sellQTY
    total_sellQTY = 0
    url = f"{BASE_URL}/trades"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        trades = response.json()
        for trade in trades:
            if(trade["transactionType"] == 'SELL'):
                total_sellQTY += trade["tradedQuantity"]
    
    # if(total_sellQTY == 300):
    #     #print("DONE")
    #     enable_kill_switch()
        



        #print(json.dumps(trades))
        trade_count = len(trades)
        print(f"Total trades executed today: {trade_count}")
        return trade_count
    else:
        print(f"Error fetching trade book: {response.status_code} - {response.text}")
        return 0


#############################################################################


def get_positions():
    url = f"{BASE_URL}/positions"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error fetching positions:", response.text)
        return []

def place_order(order_data):
    url = f"{BASE_URL}/orders"
    response = requests.post(url, json=order_data, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error placing order:", response.text)
        return None

def close_all_positions():
    positions = get_positions()
    #print("nabd")
    if not positions:
        print("No open positions.")
        return

    for pos in positions:
        #print(pos)
        net_qty = int(pos.get("netQty", 0))
        print("Positions are already closed")
        if net_qty != 0:
            security_id = pos["securityId"]
            trading_symbol = pos["tradingSymbol"]
            product_type = pos["productType"]
            exchange_segment = pos["exchangeSegment"]

            print(f"Closing position for: {trading_symbol}, Qty: {net_qty}")

            # Place opposite order to square off
            order_data = {
                "transactionType": "SELL" if net_qty > 0 else "BUY",
                "securityId": security_id,
                "quantity": abs(net_qty),
                "orderType": "MARKET",
                "productType": product_type,
                "exchangeSegment": exchange_segment,
                "orderValidity": "DAY",
                "price": 0,
                "tag": "AutoClose"
            }

            response = place_order(order_data)
            print(f"Square-off response: {response}")
            time.sleep(1)  # avoid rate limits


def cancel_pending_orders():
    # Fetch all orders
    orders = dhan.get_order_list()
    if(not orders.get('data')):
        print("No Pending Orders")

    for order in orders.get('data'):
        print(order['status'])
        if order.get("orderStatus") == "PENDING":
            order_id = order.get("orderId")
            print(f"Cancelling order: {order_id}")
            response = dhan.cancel_order(order_id)
            print(f"Response: {response}")



cancel_pending_orders()

flag = 1

##############################################################################

while False:
    print("********************************************************")
    today = datetime.now(ist).date()
    time.sleep(1)
    c = get_today_trade_count()
    p = get_daily_pnl()
    if(p == 0 and flag == 1):
        send_telegram_message("⚠️ Loss Alert: ₹3️⃣0️⃣0️⃣0️⃣ loss hit. Consider reviewing your trades.")
        flag = 0
    print("Today PNL:" , p )
    if(is_after_8am_ist() and last_deactivated_date != today):
        print("Eligible for activation")
        if(total_sellQTY >= 300 or p  -3900):
            if(count ==2):
                flag = 1
                print("Activated")
                cancel_pending_orders()
                time.sleep(1)
                close_all_positions()
                time.sleep(1)
                # enable_kill_switch()
                # disable_kill_switch()
                # enable_kill_switch()
                count = 1
                last_deactivated_date = today
                send_telegram_message("Kill Switch activated for the day")
                
                
                
            else:
                count += 1
        else:
            print("Loss limint OR quantity not croeesd")
    else:
        print("Kill Switch activated for the day")
        
        















# import json

# ACCESS_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ5NjQ5OTkyLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwMzg0MjUxMiJ9.LCLcfpnfLCGe_SKat1HgoX03_hwRAqXTR8PWY2-etBofqYBoksIIKxyRDQMiJVXD480BsxAKRunGzh3OoHf75Q'  # Replace with your actual access token
# BASE_URL = 'https://api.dhan.co'
# HEADERS = {
#     'access-token': ACCESS_TOKEN,
#     'Content-Type': 'application/json'
# }

# def get_today_trade_count():
#     url = f"{BASE_URL}/trades"
#     response = requests.get(url, headers=HEADERS)
#     if response.status_code == 200:
#         trades = response.json()
#         print(json.dumps(trades))
#         trade_count = len(trades)
#         print(f"Total trades executed today: {trade_count}")
#         return trade_count
#     else:
#         print(f"Error fetching trade book: {response.status_code} - {response.text}")
#         return 0

# # Example usage
# get_today_trade_count()
