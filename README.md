## Chat App  

Chat app is a simple client/server Chat application write in Python(version > 3.6) using command line interface which allow multi members in multi group chat together support end-to-end encryption. The app is in an assignment in course Secure Programming. This is source code of Group 11, include:
- Thanh Nhan Vo (a1941792)
- Yijia Liu (a1904682)
- Yulong Wei (a1811215)
- Congyao Bai (a1880824)

### Before run the application:  
#### 1. Install dependencies  
You must ensure there are four python libraries in your system:
- cryptography
- websockets
- pyyaml
- bcrypt

You can install these libraries by run:
```python
pip install websockets
pip install cryptography
pip install pyyaml
pip install bcrypt
```
  
#### 2. Register Users
To using Chat app as a member that can chat with other members in other groups, the first thing you must register as a member. Default, there is only a member admin. You can register new member by run:
```python
python server.py register
```
  
then follow instructions to create new member  
  
  
#### 3. How to run the application

To modified the server's IP address, port, domain and connect with other server groups, you can go to the config.yaml to configure. There are some mock servers in the config.yaml. You can modify to appropriate with your environment
After finishing configuration, you open a terminal and run:
```python
python server.py
```    

Then you can open another terminal to run client program:    
```python
python client <serverIP>:<port> <jid> [nickname]
```  
With:
- serverIP: IP address of the server
- port: the port which the server listen, default 5555
- jid: has the format name@domain, which *name* is the username which you registered with the server, *domain* is the domain of the server which you are connecting
- nickname: is optional you can use any name has format [a-zA-Z0-9]+  
  
Then the system require you enter the password which created when registered member, you enter the password ans start using the app.

#### 4. How to use the client program
When you start the server program, you don't have anything to do with them. In the contrast, there are some functions in the client program which you can use to chat/transfer file or view how many members are online in the system. After you login success, there is a line and a promt signed as below:  
```
Command(1 -> View members, 2 -> Chat, 3 -> Transfer file, 4 -> View messages, 5 -> Exit)  
>
```
So to view members in the system you enter 1, to view is there any incomming messages you enter 4, to exit you enter 5...  
  
To send a chat content 'Hi, How are you?' to another member user1@s2 ,for example, you enter 2:user1@s2:Hi, How are you?  
To transfer a file which in path '../folder1/file.txt' to another member user2@s5 ,for example, you enter 3:user2@s5:../folder1/file.txt.  

  
That's it  