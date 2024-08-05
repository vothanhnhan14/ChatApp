############################################################
## Author: Thanh Nhan Vo, Yijia Liu, Yulong Wei, Congyao Bai
############################################################

from helper import *
import asyncio
import websockets
import sys
import os
import json
import time
import threading
from business import Queue, Member
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa  
from cryptography.hazmat.primitives import serialization 
import base64
import yaml
import traceback
from getpass import getpass
from cryptography.fernet import Fernet

member = None
all_members = []
queue = Queue()
replies = []
lock = threading.Lock()   
connected = -1 # -1: connection initialize, 0: connect failed, 1: connect successful, 2: connection closed
jid = sys.argv[1]
nickname = sys.argv[2] if len(sys.argv) > 2 else ''


def to_member(m):
    """
    Create a member object
    """
    try:
        return Member(m['jid'], m['nickname'], None, serialization.load_pem_public_key(m['publickey'].encode()))
    except Exception as ex:
        return None

async def login(websocket, password):
    """
    Login to group server
    """
    global member
    public_key_pem = member.public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    await websocket.send(json.dumps({'tag': 'login', 'info': public_key_pem}))
    response = json.loads(await decrypt(member.private_key, await websocket.recv(), padder))
    message = {
        'tag': 'join',
        'info': {
            'nickname': member.nickname,
            'jid': member.jid,
            'password': password,
            'publickey': public_key_pem
        }
    }
    await websocket.send(Fernet(response['key']).encrypt(json.dumps(message).encode()))
    ok = await websocket.recv()
    print(response['moreInfo'])
    return 1 if ok == 'OK' else 0

async def get_replies(websocket):
    """
    Receive all incomming content of the current member
    """
    global member
    message = {
        'tag': 'get_replies',
        'to': member.jid
    }
    await websocket.send(json.dumps(message))
    messages = json.loads(await websocket.recv())
    for message in messages:
        if message['tag'] == 'message':
            message['info'] = message['info'] if message['to'] == 'public' else await decrypt(member.private_key, message['info'], padder)
        elif message['tag'] == 'file':
            file_name = message['filename']
            file_content = message['info'].encode() if message['to'] == 'public' else await decrypt(member.private_key, message['info'], padder, to_string=False)
            with open(file_name, 'wb') as file:
                file.write(file_content)
            message['info'] = f'You received a file {file_name}'     
          
    return messages    
    
async def get_members(websocket): 
    """
    Receive all online members information
    """   
    global all_members
    message = {'tag': 'members'}
    await websocket.send(json.dumps(message))
    members = json.loads(await websocket.recv())
    members_list = {}
    for server_members in members.values():
        for m in server_members:
            member = to_member(m)
            if member:
                members_list[m['jid']] = member
    with lock:
        all_members = members_list        

async def send_message(target, content, websocket):    
    """
    Send a chat conent into group server
    """
    global member, all_members
    message = {
        'tag': 'send_message',
        'from': member.jid,
        'to': target,
        'info': content if target == 'public' else await encrypt(all_members[target].public_key, content, padder)
    }
    await websocket.send(json.dumps(message))

async def send_file(target, file_path, websocket):
    """
    Send a file content into group server
    """
    global member, all_members
    with open(file_path, 'rb') as file:
        file_content = file.read()
    if target != 'public':    
        with lock:    
            public_key = all_members[target].public_key
    file_content = file_content.decode() if target == 'public' else await encrypt(public_key, file_content, padder)    
    message = {
        'tag': 'send_file',
        'from': member.jid,
        'to': target,
        'filename': os.path.basename(file_path),
        'info': file_content
    }
    
    await websocket.send(json.dumps(message))    

async def connect(password):
    """
    Connect to the group server
    """
    global all_members, replies, queue, connected,config

    uri = f"ws://{config['localServer']['ipAddress']}:{config['localServer']['port']}"
    # we will update members information each 1 seconds
    time_update_members = time.time() + 1
    async with websockets.connect(uri) as websocket:
        connected = await login(websocket, password)
        while connected == 1:
            password = None
            try:
                if time.time() >= time_update_members:
                    await get_members(websocket)
                    time_update_members = time.time() + 1
                message_replies = await get_replies(websocket)                
                if len(message_replies) > 0:
                    with lock:
                        replies.extend(message_replies)
                if not queue.is_empty():
                    target, content, isFile = queue.pop() 
                    if isFile:
                        await send_file(target, content, websocket)     
                    else:
                        await send_message(target, content, websocket)     
                await asyncio.sleep(0.2)
            except Exception as ex:
                if 'ConnectionClosed' in type(ex).__name__:
                    print('Server closed connection!')
                    return
                else:
                    traceback.print_exc(ex)
                    print(f'Error: {type(ex).__name__}') 
            
def connect_server(password):
    global member, jid, nickname
    private_key, public_key = generate_pair_keys(jid)
    member = Member(jid = jid, 
                    nickname = nickname,
                    private_key = private_key,
                    public_key = public_key)
    asyncio.run(connect(password))

def view_members():
    global all_members
    with lock:
        for m in all_members.values():
            print("jid: " + m.jid + ", nickname: " + m.nickname)

def chat(instruction):
    message = instruction[instruction.index(":") + 1:]
    if len(message.strip()) > 0:
        target = message[:message.index(':')]
        with lock:
            if target not in all_members and target != 'public':
                print(f'{target} is either offline or not exist!')
                return
        content = message[message.index(':') + 1:].strip()   
        queue.push((target, content, None))

def transfer_file(instruction):
    global queue
    message = instruction[instruction.index(":") + 1:]
    if len(message.strip()) > 0:
        target = message[:message.index(':')]
        with lock:
            if target not in all_members and target != 'public':
                print(f'{target} is either offline or not exist!')
                return
        content = message[message.index(':') + 1:].strip()   
        queue.push((target, content, True))

def view_incoming_messages():
    global lock, replies
    with lock:
        if len(replies) > 0:
            for reply in replies:
                print(f"Message from {reply['from']}{' to public' if reply['to'] == 'public' else ''}: {reply['info']}")
            replies = []  
        else:
            print("You don't have any message")  

def main():
    global queue, replies, connected
    while True:
        if connected == 0:
            print('Authentication failed!')
            return
        if connected == 1:
            break
        time.sleep(0.2)

    print("Command(1 -> View members, 2 -> Chat, 3 -> Transfer file, 4 -> View messages, 5 -> Exit)")
    while connected == 1:
        instruction = input('> ')
        command = int(instruction if ":" not in instruction else instruction[0:instruction.index(":")])
        if command == 1:
            view_members()
        elif command == 4:
            view_incoming_messages()        
        elif command == 2:
            chat(instruction)
        elif command == 3:
            transfer_file(instruction)   
        elif command == 5:
            connected = 2             

if __name__ == "__main__":
    t = threading.Thread(target=connect_server, kwargs={'password':getpass(prompt='Enter password: ')})
    t.start()
    main()
