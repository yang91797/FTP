import os

host = ('127.0.0.1', 8085)
reuse_address = False
max_packet_size = 8192              # 最大传输字节
coding_dir = 'gbk'                  # 查看目录时的编码方式
coding = 'utf-8'                    # 字符编码

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
home_path = os.path.join(BASE_DIR, 'db', 'home')

