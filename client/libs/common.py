import json
import struct
import hashlib
import math
import sys
from conf import settings


class Head:
    '''
    报头
    '''
    coding = settings.coding

    def __init__(self, socket, head_dic):
        self.socket = socket
        self.head_dic = head_dic

    def pack(self):               # 制作报头

        head_json = json.dumps(self.head_dic)
        head_json_bytes = bytes(head_json, self.coding)
        head_struct = struct.pack('i', len(head_json_bytes))
        self.socket.send(head_struct)
        self.socket.send(head_json_bytes)

    @classmethod
    def unpack(cls, socket):           # 解包
        head_struct = socket.recv(4)
        if not head_struct: return
        head_len = struct.unpack('i', head_struct)[0]
        head_json = socket.recv(head_len).decode(cls.coding)
        head_dic = json.loads(head_json)

        return head_dic


def hs(args):
    '''
    哈希模块
    :param args:
    :return: 哈希值
    '''
    m = hashlib.md5()
    if type(args) == bytes:
        m.update(args)
    else:
        m.update(args.encode('utf8'))
    return m.hexdigest()


def progress_bar(recv_size,filesize):
    '''
    进度条
    :param recv_size: 已接收文件的大小
    :param filesize: 文件总大小
    :return:
    '''
    s = ('\r%d%%  %s' % (math.floor(recv_size / filesize * 100), '#' * math.floor(recv_size / filesize * 100)))
    sys.stdout.write(s)
    sys.stdout.flush()

