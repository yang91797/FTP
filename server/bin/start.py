import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core import server
from conf import settings

if __name__ == '__main__':
    server.MYTCPServer(settings.host).run()

