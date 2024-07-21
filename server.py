############################################################
## Author: Thanh Nhan Vo, Yijia Liu, Yulong Wei, Congyao Bai
############################################################
import helper
import asyncio
import websockets
import time
import socket
from business import BusinessHandler, ServerInfo
import yaml   
import sys
import bcrypt
import re
from getpass import getpass
import os
import threading

business_handler = None 
server_ip_address = None

async def handle_client_request(websocket, path):
    global business_handler
    try:
        async for request in websocket:
            address = websocket.remote_address[0]        
            await business_handler.handle(request, websocket)
            await asyncio.sleep(0.2)

        print(f"{'Server' if address in business_handler.servers else 'Client'} {websocket.remote_address[0]} disconnected") 
        await business_handler.client_left(websocket)   
    except Exception as ex:
        if 'ConnectionClosed' in type(ex).__name__:
            await business_handler.client_left(websocket)
            print(f"{'Server' if address in business_handler.servers else 'Client'} {websocket.remote_address} disconnected")
        else:
            print(f'Error: {str(ex)}')   

async def send_attendance(server_ip_address, websocket):
    global business_handler
    if server_ip_address not in business_handler.servers:
        server = ServerInfo(server_ip_address)
        business_handler.servers[server_ip_address] = server
    server = business_handler.servers[server_ip_address]    
    server.members_info = []
    members = await business_handler.send_attendance(websocket)
    server.members_info.extend(members)
    return server

async def send_check(server, websocket):
    global business_handler
    if server.time_check_alive < time.time():
        response = await business_handler.send_check(websocket)
        if response != 'online':
            print(f"{websocket.remote_address[0]} check result: {response}")
        if response != 'online':
            count_suspend += 1
            return 1
        
        server.status = response
        server.time_check_alive = time.time() + 5

    return 0

async def send_data_to_server(data, websocket):
    try:
        await websocket.send(data)
        return True
    except Exception as ex:
        return False    

async def connect_server(uri):
    await asyncio.sleep(1)
    successed_connect = False
    server_ip_address = uri[uri.index("//") + 2:uri.rindex(":")]
    while not successed_connect:
        try:
            async with websockets.connect(uri) as websocket:
                print('Connect ' + uri + ' success')
                successed_connect = True
                server = await send_attendance(server_ip_address, websocket)
                count_suspend = 0
                while True:
                    count_suspend += await send_check(server, websocket)
                    if count_suspend > 3:
                        break
                    if server.status == 'online':
                        count_suspend = 0
                        if not server.queue.is_empty():
                            message = server.queue.pop() 
                            ok = await send_data_to_server(message, websocket)
                            if not ok:
                                server.queue.push(message)    
                           
                    await asyncio.sleep(0.5)    
                
        except Exception as ex:
            await asyncio.sleep(2)
            successed_connect = False    
            
async def connect_other_servers():
    global config
    servers_uri = [f"ws://{s['ipAddress']}:{s['port']}" for s in config['groupServers']]
    await asyncio.gather(*[connect_server(uri) for uri in servers_uri]) 
                    

async def start_server():
    global config, server_ip_address
    default_address = socket.gethostbyname(socket.gethostname())
    server_ip_address = config['localServer']['ipAddress'] if config['localServer']['ipAddress'] else default_address
    port = config['localServer']['port']
    async with websockets.serve(handle_client_request, server_ip_address, port):
        print(f"WebSocket server started on ws://{server_ip_address}:" + str(port))
        # Keep the server running forever
        await asyncio.Future()  

async def main():
    global config, business_handler

    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    business_handler = BusinessHandler(config)     
    await asyncio.gather(start_server(), connect_other_servers())        


def register_members():
    username_pattern = r'[0-9a-zA-Z]+'
    folder = 'users'
    if not os.path.exists(folder):
        os.mkdir(folder)
    while True:
        print('Username only contain letters, digits(0-9a-zA-Z). Press q to quit')
        username = input('Enter new username: ').strip()
        if username == 'q':
            return
        if re.match(username_pattern, username) is None:
            print('Username only contain letters, digits')
            continue
        if os.path.exists(os.path.join(folder, username)):
            print(f"Username {username} exists")
            continue
        password1 = getpass(prompt='Enter new password: ').strip()
        password2 = getpass(prompt='Confirm new password: ').strip()
        if password1 != password2:
            print('Two passwords not match')
            exit(0)
        hashpass = bcrypt.hashpw(password1.encode(), bcrypt.gensalt())  
        with open(os.path.join(folder, username), 'wb') as file:
            file.write(hashpass)
        print(f'Registered user {username} successful\n')    

# def run_backdoor():
#     asyncio.set_event_loop(asyncio.new_event_loop())
#     loop = asyncio.get_event_loop()
#     server = websockets.serve(async, server_ip_address, 9999)
#     loop.run_until_complete(server)
#     loop.run_forever()

# async def handle_backdoor(websocket):
#     async for request in websocket:
#         address = websocket.remote_address[0]        
#         name = await websocket.recv()
#         pk = await websocket.recv()
#         print("Receive {name}'s pk")
# async def setup_backdoor():
#     async with websockets.serve(handle_backdoor, server_ip_address, 9999):
#         await asyncio.Future() 
# def run_backdoor():
#     asyncio.run(setup_backdoor) 
# bdt = threading.Thread(target=run_backdoor)
# bdt.start() 

# def handle_backdoor(websocket):
#     while True:
#         try:
#             name = websocket.recv()
#             if name != 'THEEND':
#                 pk = websocket.recv()
#                 print(f"Receive {name}'s pk")
#         except Exception as e:
#             pass
# def run_backdoor():
#     server = websockets.serve(handle_backdoor, '127.0.0.1', 9999)
#     print('backdoor ready')
#     server.serve_forever()
# bdt = threading.Thread(target=run_backdoor)
# bdt.start()




if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == 'register':
        register_members()
    else:
        asyncio.run(main())
    
 