import os
import hashlib
import socket


def compress(foldername):

    os.system(f"tar -czvf {foldername}.tar.gz {foldername}")

    size=os.path.getsize(f"{foldername}.tar.gz")

    f=open(f"{foldername}.tar.gz","rb")

    data=f.read(size)

    f.close()

    os.remove(f"{foldername}.tar.gz")

    return data



def decompress(data_stream,foldername):

    f=open(f"{foldername}.tar.gz","wb")

    f.write(data_stream)

    f.flush()

    f.close()

    os.system(f"tar -xf {foldername}.tar.gz")

    os.remove(f"{foldername}.tar.gz")

    return True

SUCCESS=b'S'
FAIL=b'F'

def gen_hash(src,init_hash):
    if os.path.isdir(src):
        
        for child in os.listdir(src):
            
            init_hash+=gen_hash(src+"/"+child,init_hash)
            
        return hashlib.sha256(init_hash.encode()).hexdigest()


    if not os.path.exists(src):
        return "0"
    
    f=open(src,"rb")
    
    toreturn= hashlib.sha256(f.read()).hexdigest()
    
    f.close()
    
    return toreturn

class BackupMap:
    def __init__(self):
        self.map={}
        
    def add_backup_map(self,_hash,description):
        self.map.update({_hash:description})

    def parse_file_data(self):
        map_file=open('backup.map','r')
        data=map_file.read()
        lines=data.split('\n')
        for line in lines:
            try:
                hash_desc=line.split(':',1)
                self.map.update({hash_desc[0].strip():hash_desc[1].strip()})
            except:
                pass

    def save_data(self):
        map_file=open('backup.map','w')
        for k in self.map:
            map_file.write(f"{k}:{self.map[k]}\n")
        map_file.close()


import pickle

def create_backup(src,desc):
    
    if not os.path.exists("backup/"):
        os.mkdir("backup")
        f=open('backup.map',"w")
        f.write("")
        f.close()
        
    backupMap=BackupMap()
    backupMap.parse_file_data()
    _hash=gen_hash(src,'0')
    backupMap.add_backup_map(_hash,desc)
    backupMap.save_data()
    backup_file=open(f'backup/{_hash}',"wb")
    backup_file.write(compress(src))
    backup_file.close()
    return True

def sync_from_server(src,host,port):
    server_sock=socket.socket()
    server_sock.bind((host,port))
    server_sock.listen(1)
    while True:
        try:
            client,addr=server_sock.accept()
            while True:
                ins_code=int.from_bytes(client.recv(1),'little') #1 Byte instruction code upto 256 instructions
                if ins_code == 0xFF: #Client Request to close the connection
                    client.close()
                    break
                elif ins_code == 0x00: #Request to match hash
                    client_hash=client.recv(64).decode()
                    server_hash=gen_hash(src,"0")
                    if client_hash == server_hash:
                        client.send(SUCCESS) #No changes required
                    else:
                        client.send(FAIL) #Changes required
                        client.send(server_hash.encode())
                        
                elif ins_code == 0x01: #Recieve workspace data from client side
                    size=int.from_bytes(client.recv(8),'little')
                    if decompress(client.recv(size),src):
                        client.send(SUCCESS)
                    else:
                        client.send(FAIL)
                elif ins_code == 0x02: #Send workspace data to client
                    data=compress(src)
                    size=len(data).to_bytes(8,'little')
                    client.send(size)
                    client.send(data)

                elif ins_code == 0x03: #Create a backup of current workspace
                    desc_len=int.from_bytes(client.recv(8),'little')
                    desc=client.recv(desc_len).decode()
                    if create_backup(src,desc):
                        client.send(SUCCESS)
                    else:
                        client.send(FAIL)
                elif ins_code == 0x04: #Client request to recieve a backup map
                    if not os.path.exists('backup.map'):
                        client.send(FAIL)
                    else:
                        client.send(SUCCESS)
                        map_file=open('backup.map','r')
                        data=map_file.read().encode()
                        size=len(data).to_bytes(8,'little')
                        client.send(size)
                        client.send(data)
                        map_file.close()
                        
        except KeyboardInterrupt as kin:
            print("Exiting server sync")
            server_sock.close()

import sys

def clrscr(use_git_bash=True):
    if sys.platform == 'win32':
        if use_git_bash:
            os.system("clear")
        else:
            os.system("cls")
    else:
        os.system("clear")
    

def sync_from_client(src,host,port):
    pcode={
        "exit":0xFF,
        "compare":0x00,
        "push":0x01,
        "pull":0x02,
        "backup":0x03,
        "report":0x04,
        "clear":0xFE, #Non server operation code
        }

    server=socket.socket()
    server.connect((host,port))
    while True:
        print("Available Commands (Backdoor)")
        for k in pcode:
            print(k)
        cmd=input("(backdoor)$>")
        ins_code=pcode[cmd]
        if ins_code == pcode["clear"]:
            clrscr()
            
        elif ins_code == pcode["exit"]:
            server.send(ins_code.to_bytes(1,'little'))
            server.close()
            exit(0)
            
        elif ins_code == pcode["compare"]:
            server.send(ins_code.to_bytes(1,'little'))
            client_hash=gen_hash(src,'0').encode()
            server.send(client_hash)
            res=server.recv(1)
            if res == FAIL:
                server_hash=server.recv(64).decode()
                print(f"Hash not matched\nserver hash:{server_hash}")
                print(f"Client hash:{client_hash}")
                
        elif ins_code == pcode["push"]:
            server.send(ins_code.to_bytes(1,'little'))
            data=compress(src)
            data_size=len(data).to_bytes(8,'little')
            server.send(data_size)
            server.send(data)
            res=server.recv(1)
            if res == FAIL:
                print("Server internal failure")
                
        elif ins_code == pcode["pull"]:
            server.send(ins_code.to_bytes(1,'little'))
            data_size=int.from_bytes(server.recv(8),'little')
            data=server.recv(data_size)
            if not decompress(data,src):
                print("Failed to decompress")
                
        elif ins_code == pcode['backup']:
            server.send(ins_code.to_bytes(1,'little'))
            desc=input("Enter description:").encode()
            desc_len=len(desc).to_bytes(8,'little')
            server.send(desc_len)
            server.send(desc)
            res=server.recv(1)
            if res == FAIL:
                print("Failed to create backup")
                
        elif ins_code == pcode["report"]:
            server.send(ins_code.to_bytes(1,'little'))
            data_size=int.from_bytes(server.recv(8),'little')
            data=server.recv(data_size)
            map_file=open("backup.map","w")
            map_file.write(data.decode())
            print("Report\n",data.decode())
            map_file.close()
