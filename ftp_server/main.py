#_*_coding:utf-8_*_

import optparse
from core.ftp_server import FTPHandler
import socketserver
from conf import settings
import parser

class ArvgHandler(object):
    def __init__(self):
        self.parser = optparse.OptionParser()
        # self.parser.add_option("-s","--host",dest="host",help="server binding host address")
        # self.parser.add_option("-p","--port",dest="port",help="server binding port")
        (options, args) = self.parser.parse_args()
        print("parser",options,args)
        # print(options.host,options.port)
        self.verify_args(options, args)


    def verify_args(self,options,args):
        '''校验并调用相应功能'''
        if hasattr(self,args[0]):
            func = getattr(self,args[0])
            func()
        else:
            self.parser.print_help()

    def start(self):
        print('---going to start server---')

        server = socketserver.ThreadingTCPServer((settings.HOST, settings.PORT), FTPHandler)

        server.serve_forever()