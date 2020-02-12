import socket
import os
import subprocess
import configparser
from conf import settings
from libs import common


class MYTCPServer:
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM            # socket类型
    reuse_address = settings.reuse_address      # 地址是否重用
    packet_size = settings.max_packet_size      # 最大传输字节
    coding = settings.coding                    # 编码方式
    queue = settings.request_queue_size         # 请求的最大链接数
    coding_dir = settings.coding_dir

    def __init__(self, server_address, bind_and_activate=True):
        self.server_address = server_address
        self.socket = socket.socket(self.address_family, self.socket_type)
        self.username = None                # 登陆用户记录
        self.home_size = 0
        self.cd_path = None             # 切换目录
        self.conn = None
        self.client_addr = None

        if bind_and_activate:
            try:
                self.server_bind()
                self.server_activate()

            except Exception:
                self.server_close()
                raise

    def server_bind(self):
        if self.reuse_address:
            self.socket.setsockopt(socket.SOCK_STREAM, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

    def server_activate(self):
        self.socket.listen(self.queue)

    def server_close(self):
        self.socket.close()

    def get_request(self):
        return self.socket.accept()

    def close_request(self, request):
        request.close()

    def run(self):
        while True:
            self.conn, self.client_addr = self.get_request()

            while True:                             # 循环接收命令
                try:
                    re_head = common.Head.unpack(self.conn)
                    if not re_head: break
                    cmd = re_head['cmd']
                    if hasattr(self, cmd):
                        func = getattr(self, cmd)
                        func(re_head)
                    else:
                        self.all_func(re_head)

                except Exception as e:
                    print(e)
                    break

    def login(self, info):
        self.username = info['user'][0]
        password = info['user'][1]
        conf = configparser.ConfigParser()
        conf.read(settings.user_path)
        for dic in conf.sections():
            if self.username == dic and password == conf[dic]['password']:      # 验证用户名及密码
                self.home_size = eval(conf[dic]['disk_limit'])
                head_dic = {'message': True}
                common.Head(self.conn, head_dic).pack()                         # 返回验证信息
                return
        else:
            head_dic = {'message': False}
            common.Head(self.conn, head_dic).pack()

    def put(self, args):
        '''
        上传
        :param args: 分割的命令列表
        :return:
        '''
        filesize = args['filesize']
        file_path = os.path.join(settings.home_path, self.username, args['filename'])
        disk_size = os.path.getsize(os.path.dirname(file_path))

        if filesize > self.home_size or filesize > self.home_size-disk_size:        # 判断磁盘额度是否够用
            head_dic = {'message': False}
            common.Head(self.conn, head_dic).pack()
            return
        else:
            head_dic = {'message': True}
            common.Head(self.conn, head_dic).pack()

        if os.path.exists(file_path):           # 判断文件是否存在
            file_path_size = os.path.getsize(file_path)
            if file_path_size < filesize:       # 是否需要续传
                common.Head(self.conn, {'message': file_path_size}).pack()
                self.re_put(file_path, file_path_size, filesize)
                return
            else:
                common.Head(self.conn, {'message': '文件已存在'}).pack()
                return
        else:
            common.Head(self.conn, {'message': False}).pack()

        recv_size = 0
        hasa_value = 0
        with open(file_path, 'wb') as f:
            while recv_size < filesize:
                if filesize-recv_size < self.packet_size:           # 防止粘包
                    self.packet_size = filesize-recv_size
                recv_data = self.conn.recv(self.packet_size)
                f.write(recv_data)
                hasa_value = common.hs(recv_data)                   # 哈希模块
                hasa_value += hasa_value
                recv_size += len(recv_data)
                common.progress_bar(recv_size, filesize)            # 调用进度条模块

        hs_value = common.Head.unpack(self.conn)
        if hs_value['hs_value'] == common.hs(hasa_value):       # 哈希校验文件
            common.Head(self.conn, {'message': True}).pack()
        else:
            common.Head(self.conn, {'message': False}).pack()

    def get(self, args):
        '''
        下载
        :param args:
        :return:
        '''
        if not args['msg'].index(args['msg'][-1]):              # 判断是否只输入了一个命令
            user_home_path = os.path.join(settings.home_path, self.username)
            msg_dic = {'msg': ['dir', user_home_path]}
            self.all_func(msg_dic)                  # 返回用户家目录
        else:                           # 否则开始下载文件
            filename = args['msg'][1]
            file_path = os.path.join(settings.home_path, self.username, filename)
            filesize = os.path.getsize(file_path)
            head_dic ={
                'filename': filename,
                'filesize': filesize
            }
            common.Head(self.conn, head_dic).pack()
            send_size = 0
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(self.packet_size)
                    if not data: break
                    self.conn.send(data)
                    send_size += len(data)
                    common.progress_bar(send_size, filesize)
            common.Head(self.conn, {'msg': True}).pack()

    def all_func(self, args):
        '''
        查看目录文件
        :param args:
        :return:
        '''
        cmd = args['msg']
        if self.cd_path and args['msg'][-1] == 'dir':           # 切换目录后，使用dir命令查看
            cmd = ['dir', self.cd_path]
        res = subprocess.Popen(cmd,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        out_res = res.stdout.read()
        err_res = res.stderr.read()
        data_size = len(out_res) + len(err_res)
        head_dic = {'data_size': data_size}
        common.Head(self.conn, head_dic).pack()
        self.conn.send(out_res)
        self.conn.send(err_res)

    def cd(self, args):
        '''
        切换目录
        :param args:
        :return:
        '''
        info = args['msg']
        common.Head(self.conn, {'msg': '已切换到%s目录，使用dir命令查看' % info[1]}).pack()
        self.cd_path = info[1]                  # 记录切换的目录

    def re_put(self, file_path, recv_size, filesize):
        '''
        断点续传
        :param file_path: 文件路径
        :param filesize: 文件大小
        :return:
        '''
        with open(file_path, 'ab') as f:
            while recv_size < filesize:
                if filesize-recv_size < self.packet_size:           # 防止粘包
                    self.packet_size = filesize-recv_size
                recv_data = self.conn.recv(self.packet_size)
                f.write(recv_data)
                recv_size += len(recv_data)
                common.progress_bar(recv_size, filesize)




