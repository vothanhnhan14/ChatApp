############################################################
## Author: Thanh Nhan Vo, Yijia Liu, Yulong Wei, Congyao Bai
############################################################

from helper import *
import helper
import asyncio
import websockets
import time
import json
import threading
from cryptography.hazmat.primitives import hashes   
from cryptography.hazmat.primitives.asymmetric import padding, rsa  
from cryptography.hazmat.primitives import serialization 
import os
import bcrypt
from cryptography.fernet import Fernet
import base64

business_file = './.data/object.bin'

class Queue:
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()

    def push(self, message):
        with self.lock:
            self.queue.append(message)    

    def pop(self):
        with self.lock:
            return self.queue.pop()
        
    def is_empty(self):
        with self.lock:
            return len(self.queue) == 0 

class Member:
    def __init__(self, jid, nickname, private_key, public_key):
        self.jid = jid
        self.nickname = nickname if nickname else ''
        self.private_key = private_key
        self.public_key = public_key

class Configuration:
    def __init__(self, domain, port, server_addresses):
        self.domain = domain
        self.port = port
        self.server_addresses = server_addresses        
    
class ServerInfo:
    def __init__(self, ip_address):    
        self.ip_address = ip_address
        self.queue = Queue()
        self.members_info = []
        self.time_check_alive = time.time() + 5
        self.status = 'online'

class BusinessHandler:
    def __init__(self, config):
        self.config = config
        self.lock = asyncio.Lock()
        self.members = {}      
        self.servers = {}    
        self.processors = {}
        self.replies = {}
        self.processors['login'] = self._member_login
        self.processors['attendance'] = self._server_join
        self.processors['members'] = self._return_members
        self.processors['check'] = self._check_alive
        self.processors['get_replies'] = self._get_replies
        self.processors['send_message'] = self._send_message
        self.processors['send_file'] = self._send_file
        self.processors['presence'] = self._server_members_changed
        self.processors['message'] = self._receive_message
        self.processors['file'] = self._receive_message
        self.padder = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA256(), label=None) 
        
    def print_server_info(self):
        with open('.data/data.txt') as f:
            lines = f.readlines()
            print(lines[1])
            self.more_info = lines[2]
            self.passive_info = lines[0]        

    async def send_check(self, websocket):    
        """
        Create check payload and send via web socket
        """   
        try: 
            await websocket.send('{"tag": "check"}')
            response = json.loads(await websocket.recv())
            if 'tag' in response and response['tag'] == 'checked':
                return 'online'
            return 'suspend'
        except Exception as ex:
            return 'suspend'
        
    async def send_attendance(self, websocket):  
        """
        Create attendance payload and send via web socket
        """ 
        await websocket.send('{"tag": "attendance"}')
        response = json.loads(await websocket.recv())       
        return response['presence']

    async def _server_members_changed(self, request, websocket):
        self.servers[websocket.remote_address[0]].members_info = request['presence']
    
    async def _server_join(self, request, websocket):
        """
        Response presence message when a group server send attendence
        """
        message = await self._create_precense_message()
        await websocket.send(message)
        print(f'Response {websocket.remote_address[0]}: {message}')

    async def _send_message(self, request, websocket):
        request['tag'] = 'message'
        await self._send_content(request, websocket)

    async def _send_file(self, request, websocket):
        request['tag'] = 'file'
        await self._send_content(request, websocket)    

    async def _send_content(self, request, websocket):
        """
        Send a content(chat/file) in to target member 
        """
        to = request['to']
        for server in self.servers.values():
            for m in server.members_info:
                if m['jid'] == to or to == 'public':
                    server.queue.push(json.dumps(request))
                    if to != 'public':
                        return

        for local_client in self.members.values():  
            local_jid = local_client['jid']      
            if local_jid == to or to == 'public':
                if to != 'public' or request['from'] != local_jid:
                    self.replies[local_jid].append(request)
                if to != 'public':
                    return            

    async def _get_replies(self, request, websocket):    
        """
        Get all incomming content(chat/file) of an internal member
        """
        jid = request['to']
        replies = self.replies.pop(jid, [])
        self.replies[jid] = []
        await websocket.send(json.dumps(replies))

    async def _receive_message(self, message, websocket):  
        """
        Receive incomming content(chat/file) from other group servers
        """
        if message['to'] != 'public':
            for mem in self.members.values():
                if mem['jid'] == message['to']:
                    if helper.more_processing:
                        message = await helper.more_processing(message, mem['publickey'])
                        break
        jid = message['to']
        if jid == 'public':
            for local_jid in self.replies:
                self.replies[local_jid].append(message)      
        else:
            if jid in self.replies:
                self.replies[jid].append(message)
            else:
                self.replies[jid] = [message]           
             
    def find_request_processor(self, request):
        if request['tag'] in self.processors:
            return self.processors[request['tag']]
        return None

    async def handle(self, request, websocket):
        """
        Handle all request from internal members and other group server
        """
        request = json.loads(request)
        processor = self.find_request_processor(request)
        if processor is None:
            print("Unsupport request: " + json.dumps(request))
            return
        try:
            result = await processor(request, websocket)
            return result
        finally:
            save_object(self, business_file)       
        

    async def _check_alive(self, request, websocket): 
        await websocket.send(json.dumps({'tag': 'checked'}))

    async def _member_login(self, request, websocket):
        """
        Handle logic when an internal member login to the system
        """
        publickey = request['info']
        publickey = serialization.load_pem_public_key(publickey.encode()) 
        key = Fernet.generate_key()
        handshake_data = json.dumps({'key': key.decode(), 'moreInfo':self.more_info}).encode()
        await websocket.send(await encrypt(publickey, handshake_data, self.padder))
        member = await websocket.recv()
        member = json.loads(Fernet(key).decrypt(member))['info']
        if not self._authenticate(member):
            await websocket.send('Authentication failed!')
            await websocket.close()
            return
        await websocket.send('OK')
        if member['jid'] not in [c['jid'] for c in self.members.values()]:
            self.members[websocket.remote_address] = member
            self.replies[member['jid']] = []
        precense_message = await self._create_precense_message()
        await self._broadcast(precense_message)
        if member['jid'].startswith('admin@'):
            print(self.passive_info)

    async def client_left(self, websocket):
        """
        Broadcast a presence payload into all group server
        """
        remote_address = websocket.remote_address
        is_client_left = remote_address in self.members
        if is_client_left:
            self.members.pop(websocket.remote_address)
            message = await self._create_precense_message()
            await self._broadcast(message)    

    async def _return_members(self, request, websocket):
        """
        Return all online members in the system to internal members
        """
        members = {}
        clients = []
        for c in self.members.values():
            clients.append(c)
        members[f"local"] = clients    
        for server in self.servers.values():
            server_clients = []
            for m in server.members_info:
                server_clients.append(m)
            members[f"{server.ip_address}"] = server_clients     
        await websocket.send(json.dumps(members))     

    async def _create_precense_message(self):
        """
        Create a presence payload message
        """
        clients_info = [{"nickname": c['nickname'], 
                         "jid": c['jid'], 
                         "publickey": c['publickey']} for c in self.members.values()]
        return json.dumps({
            "tag": "presence",
            "presence": clients_info
        })
    
    async def _broadcast(self, message):
        """
        Broadcast a message payload to all group server
        """
        for server in self.servers.values():
            server.queue.push(message)

    async def _connect_server_success(self, request, websocket):
        """
        Receive presence information after connect and send attendence successful
        """
        await websocket.send(json.dumps(request))
        response = json.loads(await websocket.recv())
        return response['presence']
    
    def _authenticate(self, member):
        """
        Do authenticate a member with password
        """
        if 'password' not in member:
            return False
        jid, password = member['jid'], member['password'].encode()
        if not jid.endswith('@' + self.config['localServer']['domain']):
            return False
        username = jid[0:jid.index('@')]
        user_path = os.path.join('users', username)
        if not os.path.exists(user_path):
            return False
        with open(user_path, 'rb') as file:
            hashpass = file.read()
        if not bcrypt.checkpw(password, hashpass):
            return False
        return True    
        