import socket
import os
from conf import settings
from libs import common


class MYTCPClient:
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    max_size = settings.max_packet_size                 # 接收的最大字节
    reuse_address = settings.reuse_address
    coding = settings.coding
    coding_dir = settings.coding_dir                # 查询目录的编码方式

    def __init__(self, server_address, connect=True):
        self.server_address = server_address
        self.socket = socket.socket(self.address_family, self.socket_type)
        self.username = None
        if connect:
            try:
                self.client_connect()
            except Exception:
                self.client_close()
                raise

    def client_connect(self):
        self.socket.connect(self.server_address)

    def client_close(self):
        self.socket.close()

    def login(self):
        '''
        登陆
        :return:
        '''
        while True:
            username = input('请输入用户名：').strip()
            password = input('请输入密码：').strip()
            password = common.hs(password)          # 哈希模块
            user = [username, password]
            head_dic = {'cmd': 'login',
                        'user': user,
                        }
            for key in head_dic:
                if not all(head_dic[key]): continue
            common.Head(self.socket, head_dic).pack()               # 发送报头模块
            re_head = common.Head.unpack(self.socket)               # 接收报头模块
            if re_head['message']:
                print('登陆成功')
                self.username = username            # 记录用户名
                self.run()
            else:
                print('用户名或密码错误！！！')

    def run(self):
        while True:
            order = input('请输入命令：').strip()
            if not order: continue
            order_list = order.split()
            cmd = order_list[0]
            if hasattr(self, cmd):              # 如果没有这个方法，则交给系统执行这个命令
                func = getattr(self, cmd)
                func(order_list)
            else:
                self.all_func(order_list)        # 交给系统执行

    def put(self, args):
        '''
        上传
        :param args: 分割的命令列表
        :return:
        '''
        filesize = os.path.getsize(args[1])
        head_dic = {
            'cmd': args[0],
            'filename': args[1],
            'filesize': filesize
        }
        common.Head(self.socket, head_dic).pack()
        info = common.Head.unpack(self.socket)
        if not info['message']:
            print('磁盘额度不够')
            return

        msg = common.Head.unpack(self.socket)['message']
        if msg or msg == 0:                  # 文件是否存在
            if msg == '文件已存在':          # 判断是否需要续传
                print('文件已存在')
                return
            else:
                print('正在续传！！！')
                self.re_put(msg, filesize, args[1])
                return

        send_size = 0
        hasa_value = 0
        with open(args[1], 'rb') as f:
            while True:
                line = f.read(self.max_size)
                if not line: break
                self.socket.send(line)
                hasa_value = common.hs(line)
                hasa_value += hasa_value
                send_size += len(line)
                common.progress_bar(send_size, filesize)
        hs_value = common.hs(hasa_value)                # 文件哈希值
        common.Head(self.socket, {'hs_value': hs_value}).pack()
        if common.Head.unpack(self.socket)['message']:
            print('文件上传成功！！！')

    def get(self, *args):
        '''
        下载，查看家目录
        :param args:
        :return:
        '''
        if not args[0].index(args[0][-1]):       # 查看家目录
            self.all_func(args[0])              # 传入命令参数，调用执行系统命令的函数
        else:                                   # 下载
            head_dic = {'cmd': args[0][0], 'msg': args[0]}
            common.Head(self.socket, head_dic).pack()       # 告诉服务端，客户端要下载文件以及文件名
            info = common.Head.unpack(self.socket)
            filesize = info['filesize']
            file_path = os.path.join(settings.home_path, self.username, info['filename'])
            recv_size = 0
            with open(file_path, 'wb') as f:
                while recv_size < filesize:
                    if filesize-recv_size < self.max_size:
                        self.max_size = filesize-recv_size
                    recv_data = self.socket.recv(self.max_size)
                    f.write(recv_data)
                    recv_size += len(recv_data)
                    common.progress_bar(recv_size, filesize)
            if common.Head.unpack(self.socket)['msg']:
                print('下载成功！！！')

    def all_func(self, args):
        '''
        查看目录文件,执行系统命令
        :param args:
        :return:
        '''
        head_dic = {'cmd': args[0], 'msg': args}
        common.Head(self.socket, head_dic).pack()
        res = common.Head.unpack(self.socket)['data_size']
        recv_size = 0
        recv_data = b''
        while recv_size < res:
            if res - recv_size < self.max_size:
                self.max_size = res-recv_size
            data = self.socket.recv(self.max_size)
            recv_size += len(data)
            recv_data += data

        print(recv_data.decode(self.coding_dir))

    def cd(self, args):
        '''
        切换目录
        :param args:
        :return:
        '''
        head_dic = {'cmd': args[0], 'msg': args}
        common.Head(self.socket, head_dic).pack()
        info = common.Head.unpack(self.socket)['msg']
        print(info)

    def re_put(self, file_path_size, filesize, filename):
        '''
        断点续传
        :param file_path_size: 已上传的文件大小
        :param filesize: 文件总大小
        :param filename: 文件路径
        :return:
        '''
        with open(filename, 'rb') as f:
            while True:
                f.seek(file_path_size)
                data = f.read(self.max_size)
                if not data: break
                self.socket.send(data)
                file_path_size += len(data)
                common.progress_bar(file_path_size, filesize)
        print('上传成功')


















