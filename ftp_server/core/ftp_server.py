#_*_coding:utf-8_*_

import socketserver
import json
import configparser
import os,sys
import hashlib
from conf import settings

STATUS_CODE = {
    250:"Invalid cmd format, e.g:{'action':'get','filename':'test.py','size':344}",
    251:"Invalid cmd",
    252:"Invalid auth data",
    253:"Wrong username or password",
    254:"Passed authentication",
    255:"filename doesn't provided",
    256:"File doesn't exist on server",
    257:"ready to send file",
    258:"md5 verification",
    259:"file has been existed",
    500:"ok",
}

'''
250：“无效的cmd格式，例如：{'action'：'get'，'filename'：'test.py'，'size'：344}”，
251：“无效的CMD”，
252：“验证数据无效”，
253：“错误的用户名或密码”，
254：“通过身份验证”，
255：“文件名不提供”，
256：“服务器上不存在文件”，
257：“准备发送文件”，
258:“md5验证”,
500: '正常'
'''

class FTPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        '''接收客户端消息（用户，密码，action）'''
        while True:
            self.data = self.request.recv(1024).strip()
            print(self.client_address[0])
            print(self.data)
            # self.request.sendall(self.data.upper())

            if not self.data:
                print("client closed...")
                break
            data = json.loads(self.data.decode())  #接收客户端消息
            if data.get('action') is not None:  #action不为空
                print("---->", hasattr(self, "_auth"))
                if hasattr(self, "_%s" % data.get('action')): #客户端action 符合服务端action
                    func = getattr(self, "_%s" % data.get('action'))
                    func(data)
                else:  #客户端action 不符合服务端action
                    print("invalid cmd")
                    self.send_response(251)  # 251：“无效的CMD”
            else:  #客户端action 不正确
                print("invalid cmd format")
                self.send_response(250) # 250：“无效的cmd格式，例如：{'action'：'get'，'filename'：'test.py'，'size'：344}”

    def send_response(self,status_code,data=None):
        '''向客户端返回数据'''
        response = {'status_code':status_code,'status_msg':STATUS_CODE[status_code]}
        if data:
            response.update(data)
        self.request.send(json.dumps(response).encode())

    def _auth(self,*args,**kwargs):
        '''核对服务端 发来的用户，密码'''
        # print("---auth",args,kwargs)
        data = args[0]
        print(data)
        if data.get("username") is None or data.get("password") is None: #客户端的用户和密码有一个为空 则返回错误
            self.send_response(252)  # 252：“验证数据无效”

        user = self.authenticate(data.get("username"),data.get("password")) #把客户端的用户密码进行验证合法性
        if user is None: #客户端的数据为空 则返回错误
            print('user is none')
            self.send_response(253)  # 253：“错误的用户名或密码”
        else:
            print("password authentication",user)
            self.user = user
            self.send_response(254)  # 254：“通过身份验证”
            self.current_path = "%s/%s" %(settings.USER_HOME,self.user["Username"])

    def authenticate(self,username,password):
        '''验证用户合法性，合法就返回数据，核对本地数据'''
        config = configparser.ConfigParser()
        config.read(settings.ACCOUNT_FILE)
        print(settings.ACCOUNT_FILE)
        if username in config.sections():  #用户匹配成功
            print('user name correct..')
            print(password)
            _password = config[username]["Password"]
            print(_password)
            if _password == password:  #密码匹配成功
                print("pass auth..",username)
                config[username]["Username"] = username
                return config[username]

    def _put(self,*args,**kwargs):
        "client send file to server"
        data = args[0]
        print(data)
        base_filename = os.path.join(self.current_path,data.get('filename'))
        file_obj = open(base_filename, 'wb')
        data = self.request.recv(4096)
        # print(data)
        file_obj.write(data)
        file_obj.close()

    def _get(self,*args,**kwargs):
        '''get 下载方法'''
        data = args[0]
        if data.get('filename') is None:
            self.send_response(255)  # 255：“文件名不提供”
        # user_home_dir = "%s/%s" %(settings.USER_HOME,self.user["Username"]) #当前连接用户的目录

        user_home_dir = self.current_path
        file_abs_path = "%s/%s" %(user_home_dir,data.get('filename'))  #客户端发送过来的目录文件
        print("file abs path",file_abs_path)

        if os.path.isfile(file_abs_path):  #客户端目录文件名 存在服务端
            file_obj = open(file_abs_path,'rb')  # 用bytes模式打开文件
            file_size = os.path.getsize(file_abs_path)  #传输文件的大小
            self.send_response(257,data={'file_size':file_size}) #返回即将传输的文件大小 和状态码

            self.request.recv(1)  #等待客户端确认

            if data.get('md5'): #有 --md5 则传输时加上加密
                md5_obj = hashlib.md5()
                for line in file_obj:
                    self.request.send(line)
                    md5_obj.update(line)
                else:
                    file_obj.close()
                    md5_val = md5_obj.hexdigest()
                    self.send_response(258,{'md5':md5_val})
                    print("send file done....")
            else:  #没有 --md5  直接传输文件
                for line in file_obj:
                    self.request.send(line)
                else:
                    file_obj.close()
                    print("send file done....")

        else:
            self.send_response(256) # 256：“服务器上不存在文件”=


    def _ls(self,*args,**kwargs):
        '''显示文件列表'''
        data = args[0]
        print(data)
        # user_home_dir = "%s/%s" %(settings.USER_HOME,self.user["Username"]) #当前连接用户的目录
        user_home_dir = self.current_path
        file_list = os.listdir(user_home_dir)
        self.send_response(500,data={'file_list':file_list})
    
    def _cd(self,*args,**kwargs):
        '''进入文件夹'''
        data = args[0]
        print(data)
        if data.get('filename') is None:
            self.send_response(255)  # 255：“文件名不提供”
        # user_home_dir = "%s/%s" %(settings.USER_HOME,self.user["Username"]) #当前连接用户的目录
        user_home_dir = self.current_path
        dir_name = data.get('filename')
        dir_path = os.path.join(user_home_dir,dir_name)
        if dir_name == '.':
            self.send_response(500)
            print(self.current_path)
        elif dir_name == '..':
            self.current_path = os.path.dirname(self.current_path)
            self.send_response(500)
            print(self.current_path)
        elif os.path.exists(dir_path):
            self.current_path = dir_path
            self.send_response(500)
            print(self.current_path)
        else:
            self.send_response(256) # 256：“服务器上不存在文件”=


        
    
    def _rm(self,*args,**kwargs):
        '''删除文件或者目录'''
        data = args[0]
        print(data)
        if data.get('filename') is None:
            self.send_response(255)  # 255：“文件名不提供”
        # user_home_dir = "%s/%s" %(settings.USER_HOME,self.user["Username"]) #当前连接用户的目录
        user_home_dir = self.current_path
        file_path = os.path.join(user_home_dir,data.get('filename')) 
        print(file_path)
        if os.path.isfile(file_path):
            os.remove(file_path)
            self.send_response(500)
        elif os.path.isdir(file_path):
            for root, dirs, files in os.walk(file_path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(file_path)
            self.send_response(500)
        else:
            self.send_response(255)
    
    def _mkdir(self,*args,**kwargs):
        '''创建文件夹'''
        data = args[0]
        print(data)
        if data.get('filename') is None:
            self.send_response(255)  # 255：“文件名不提供”
        # user_home_dir = "%s/%s" %(settings.USER_HOME,self.user["Username"]) #当前连接用户的目录
        user_home_dir = self.current_path
        file_path = os.path.join(user_home_dir,data.get('filename')) 
        print(file_path)

        folder = os.path.exists(file_path)
        if not folder:                   #判断是否存在文件夹如果不存在则创建为文件夹
            os.makedirs(file_path)            #makedirs 创建文件时如果路径不存在会创建这个路径
            self.send_response(500)
        else:
            self.send_response(259)

    def _pwd(self,*args,**kwargs):
        '''显示当前路径'''
        data = args[0]
        print(data)
        # user_home_dir = "%s/%s" %(settings.USER_HOME,self.user["Username"]) #当前连接用户的目录
        self.send_response(500,data={'current_path':self.current_path})

    def _mkfile(self,*args,**kwargs):
        '''创建文件'''
        data = args[0]
        print(data)
        if data.get('filename') is None:
            self.send_response(255)  # 255：“文件名不提供”
        # user_home_dir = "%s/%s" %(settings.USER_HOME,self.user["Username"]) #当前连接用户的目录
        user_home_dir = self.current_path
        file_path = os.path.join(user_home_dir,data.get('filename')) 
        print(file_path)
        file = open(file_path,'w')
        file.close()
        self.send_response(500)

    def _head(self,*args,**kwargs):
        '''查看文件前五行'''
        data = args[0]
        print(data)
        if data.get('filename') is None:
            self.send_response(255)  # 255：“文件名不提供”
        # user_home_dir = "%s/%s" %(settings.USER_HOME,self.user["Username"]) #当前连接用户的目录
        user_home_dir = self.current_path
        file_path = os.path.join(user_home_dir,data.get('filename')) 
        if not os.path.isfile(file_path):
            self.send_response(256) # 256：“服务器上不存在文件”=
        print('file_path')
        print(file_path)
        file = open(file_path,'r')
        content = ''
        for line in file.readlines()[:5]:
            content = content + line
        file.close()
        self.send_response(500,data={'content':content})
    

if __name__ == '__main__':
    HOST, PORT = "127.0.0.1", 9999