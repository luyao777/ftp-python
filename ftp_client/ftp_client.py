#_*_coding:utf-8_*_

import socket
import os
import sys
import optparse
import json
import hashlib

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

class FTPClient(object):
    def __init__(self):
        parser = optparse.OptionParser()
        parser.add_option("-s","--server",dest="server",help="ftp server ip_addr")
        parser.add_option("-P","--port",type="int",dest="port",help="ftp server port")
        parser.add_option("-u","--username",dest="username",help="username")
        parser.add_option("-p","--password",dest="password",help="password")

        self.options,self.args = parser.parse_args()
        self.verify_args(self.options,self.args)
        self.make_connection()

    def make_connection(self):
        '''远程连接'''
        self.sock = socket.socket()
        self.sock.connect((self.options.server,self.options.port))

    def verify_args(self,options,args):
        '''校验参数合法性'''
        if options.username is not None and options.password is not None:  #用户和密码，两个都不为空
            pass
        elif options.username is None and options.password is None: #用户和密码，两个都为空
            pass
        else:  #用户和密码，有一个为空
            # options.username is None or options.password is None:  #用户和密码，有一个为空
            exit("Err: username and password must be provided together...")

        if options.server and options.port:
            # print(options)
            if options.port >0 and options.port <65535:
                return True
            else:
                exit("Err:host port must in 0-65535")

    def authenticate(self):
        '''用户验证，获取客户端输入信息'''
        if self.options.username:  #有输入信息 发到远程判断
            print(self.options.username,self.options.password)
            return self.get_auth_result(self.options.username,self.options.password)
        else:  #没有输入信息 进入交互式接收信息
            retry_count = 0
            while retry_count <3:
                username = input("username: ").strip()
                password = input("password: ").strip()
                return self.get_auth_result(username,password)
                # retry_count +=1

    def get_auth_result(self,user,password):
        '''远程服务器判断 用户，密码，action '''
        data = {'action':'auth',
                'username':user,
                'password':password,}

        self.sock.send(json.dumps(data).encode())  #发送 用户，密码，action 到远程服务器  等待远程服务器的返回结果
        response = self.get_response()  #获取服务器返回码
        if response.get('status_code') == 254: #通过验证的服务器返回码
            print("Passed authentication!")
            self.user = user
            return True
        else:
            print(response.get("status_msg"))

    def get_response(self):
        '''得到服务器端回复结果,公共方法'''
        data = self.sock.recv(1024)
        data = json.loads(data.decode())
        return data

    def interactive(self):
        '''交互程序'''
        if self.authenticate(): #认证成功，开始交互
            print("--start interactive iwth u...")
            while True: #循环 输入命令方法
                choice = input("[%s]:"%self.user).strip()
                if len(choice) == 0:continue
                cmd_list = choice.split()
                if hasattr(self,"_%s"%cmd_list[0]): #反射判断 方法名存在
                    func = getattr(self,"_%s"%cmd_list[0]) #反射 方法名
                    func(cmd_list)  #执行方法
                else:
                    print("Invalid cmd.")

    def _md5_required(self,cmd_list):
        '''检测命令是否需要进行MD5的验证'''
        if '--md5' in cmd_list:
            return True

    def show_progress(self,total):
        '''进度条'''
        received_size = 0
        current_percent = 0
        while received_size < total:
            if int((received_size / total) * 100) > current_percent :
                print("#",end="",flush=True)
                current_percent = (received_size / total) * 100
            new_size = yield
            received_size += new_size

    def _get(self,cmd_list):
        ''' get 下载方法'''
        print("get--",cmd_list)
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        #客户端操作信息
        data_header = {
            'action':'get',
            'filename':cmd_list[1],
        }

        if self._md5_required(cmd_list):  #命令请求里面有带 --md5
            data_header['md5'] = True  #将md5加入 客户端操作信息

        self.sock.send(json.dumps(data_header).encode()) #发送客户端的操作信息
        response = self.get_response()  #接收服务端返回的 操作信息
        print(response)

        if response["status_code"] ==257: #服务端返回的状态码是:传输中
            self.sock.send(b'1')  # send confirmation to server
            base_filename = cmd_list[1].split('/')[-1] #取出要接收的文件名
            received_size = 0  #本地接收总量
            file_obj = open(base_filename,'wb') #bytes模式写入

            if self._md5_required(cmd_list): #命令请求里有 --md5
                md5_obj = hashlib.md5()

                progress = self.show_progress(response['file_size'])
                progress.__next__()

                while received_size < response['file_size']: #当接收的量 小于 文件总量 就循环接收文件
                    data = self.sock.recv(4096) #一次接收4096
                    received_size += len(data) #本地接收总量每次递增

                    try:
                        progress.send(len(data))
                    except StopIteration as e:
                        print("100%")

                    file_obj.write(data) #把接收的数据 写入文件
                    md5_obj.update(data) #把接收的数据 md5加密
                else:
                    print("--->file rece done<---") #成功接收文件
                    file_obj.close() #关闭文件句柄
                    md5_val = md5_obj.hexdigest()
                    md5_from_server = self.get_response()  #获取服务端发送的 md5
                    if md5_from_server['status_code'] ==258:  #状态码为258
                        if md5_from_server['md5'] == md5_val:  #两端 md5值 对比
                            print("%s 文件一致性校验成功！" %base_filename)
                    # print(md5_val,md5_from_server)
            else:  #没有md5校验 直接收文件
                progress = self.show_progress(response['file_size'])
                progress.__next__()

                while received_size < response['file_size']: #当接收的量 小于 文件总量 就循环接收文件
                    data = self.sock.recv(4096) #一次接收4096
                    received_size += len(data) #本地接收总量每次递增
                    file_obj.write(data) #把接收的数据 写入文件
                    try:
                        progress.send(len(data))
                    except StopIteration as e:
                        print("100%")
                else:
                    print("--->file rece done<---") #成功接收文件
                    file_obj.close() #关闭文件句柄

    def _put(self,cmd_list):
        ''' put 下载方法'''
        print("put--", cmd_list)
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        # 客户端操作信息
        data_header = {
            'action': 'put',
            'filename': cmd_list[1],
        }
        self.sock.send(json.dumps(data_header).encode())  # 发送客户端的操作信息
        # self.sock.recv(1)
        file_obj = open(cmd_list[1],'br')
        for line in file_obj:
            self.sock.send(line)

    def _ls(self,cmd_list):
        ''' ls 显示文件列表方法 '''
        print("ls--",cmd_list)
        if len(cmd_list) > 1:
            print('ls only support 1 argument')
            return
        # 客户端操作信息
        data_header = {
            'action': 'ls',
        }
        self.sock.send(json.dumps(data_header).encode())  # 发送客户端的操作信息
        response = self.get_response()  #接收服务端返回的 操作信息
        for item in response['file_list']:
            print(item)

    def _rm(self,cmd_list):
        ''' rm 删除文件 '''
        print("rm--",cmd_list)
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        # 客户端操作信息
        data_header = {
            'action': 'rm',
            'filename': cmd_list[1],
        }
        self.sock.send(json.dumps(data_header).encode())  # 发送客户端的操作信息
        response = self.get_response()  #接收服务端返回的 操作信息
        print(response)
    
    def _mkdir(self,cmd_list):
        ''' mkdir 创建文件夹 '''
        print("mkdir--",cmd_list)
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        # 客户端操作信息
        data_header = {
            'action': 'mkdir',
            'filename': cmd_list[1],
        }
        self.sock.send(json.dumps(data_header).encode())  # 发送客户端的操作信息
        response = self.get_response()  #接收服务端返回的 操作信息
        print(response)

    def _cd(self,cmd_list):
        ''' cd 进入文件 '''
        print("cd--",cmd_list)
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        # 客户端操作信息
        data_header = {
            'action': 'cd',
            'filename': cmd_list[1],
        }
        self.sock.send(json.dumps(data_header).encode())  # 发送客户端的操作信息
        response = self.get_response()  #接收服务端返回的 操作信息
        print(response)

    def _pwd(self,cmd_list):
        ''' pwd 显示当前路径 '''
        print("pwd--",cmd_list)
        if len(cmd_list) > 1:
            print('ls only support 1 argument')
            return
        # 客户端操作信息
        data_header = {
            'action': 'pwd',
        }
        self.sock.send(json.dumps(data_header).encode())  # 发送客户端的操作信息
        response = self.get_response()  #接收服务端返回的 操作信息
        print(response['current_path'])

    def _mkfile(self,cmd_list):
        ''' mkfile 创建文件 '''
        print("mkdir--",cmd_list)
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        # 客户端操作信息
        data_header = {
            'action': 'mkfile',
            'filename': cmd_list[1],
        }
        self.sock.send(json.dumps(data_header).encode())  # 发送客户端的操作信息
        response = self.get_response()  #接收服务端返回的 操作信息
        print(response)

    def _head(self,cmd_list):
        ''' head 查看文件前五行 '''
        print("head--",cmd_list)
        if len(cmd_list) == 1:
            print("no filename follows...")
            return
        # 客户端操作信息
        data_header = {
            'action': 'head',
            'filename': cmd_list[1],
        }
        self.sock.send(json.dumps(data_header).encode())  # 发送客户端的操作信息
        response = self.get_response()  #接收服务端返回的 操作信息
        print(response)



if __name__ == '__main__':
    ftp = FTPClient()
    ftp.interactive()