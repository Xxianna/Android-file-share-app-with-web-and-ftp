import os
import socket
import threading
import http.server
import socketserver
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

def ffttpp(username, password, folder_path, port):
    # 实例化虚拟用户，这是用于验证用户登录的用户名和密码
    authorizer = DummyAuthorizer()

    # 添加用户权限和路径，括号中的参数分别是用户名、密码、用户目录、权限
    authorizer.add_user(username, password,folder_path, perm='elradfmwMT')

    # e: 改变目录（CWD, CDUP commands）
    # l: 列出目录（LIST, NLST, STAT, MLSD, MLST, SIZE, MDTM commands）
    # r: 从服务器检索文件（RETR command）
    # a: 将文件存储到服务器（STOR, STOU commands）
    # d: 删除文件或目录（DELE, RMD commands）
    # f: 文件重命名（RNFR, RNTO commands）
    # m: 创建目录（MKD command）
    # w: 写权限（APPE command）
    # M: 文件传输模式（TYPE command）
    # T: 更改文件时间戳（MFMT command）

    # 初始化FTP处理器
    handler = FTPHandler
    handler.authorizer = authorizer

    # 监听IP和端口
    server = FTPServer(('0.0.0.0', port), handler)

    # 开始服务
    server.serve_forever()

class FolderShareApp(toga.App):
    server_thread = None
    httpd = None
    current_view = 'main'
    sharing = False  # 新增变量，用于跟踪分享状态

    def startup(self):
        # self.tmp_folder_path_choice = None
        #如果是Android则默认选择/sdcard文件夹，windows则默认选择/
        if os.name == 'nt':
            self.init_folder_path = '/'
        else:
            self.init_folder_path = '/sdcard'
        self.tmp_folder_path_choice = self.init_folder_path

        self.main_box = toga.Box(style=Pack(direction=COLUMN, background_color='#000000'))
        self.setup_main_view()
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = self.main_box
        self.main_window.show()


    def setup_main_view(self):
        # 清空当前视图
        self.main_box.remove(*self.main_box.children)
        
        # 文件夹选择器
        self.folder_path = toga.TextInput(style=Pack(padding=10, flex=1, color='#FFFFFF', background_color='#000000'))
        folder_select_button = toga.Button('选择文件夹', on_press=self.select_folder, style=Pack(padding=5, color='#FFFFFF', background_color='#000066'))
        folder_box = toga.Box(style=Pack(direction=ROW, padding=5, background_color='#000000'))
        folder_box.add(self.folder_path)
        folder_box.add(folder_select_button)

        # 端口输入
        self.port_input = toga.NumberInput(min_value=1024, max_value=65535, value=8000, style=Pack(flex=1, color='#FFFFFF', background_color='#221111'))
        port_label = toga.Label('端口号:', style=Pack(width=100, color='#FFFFFF', background_color='#000000'))
        port_box = toga.Box(style=Pack(direction=COLUMN, padding=5, background_color='#000000'))
        port_box.add(port_label)
        port_box.add(self.port_input)

        # 显示访问链接
        link_label = toga.Label('访问链接:', style=Pack(width=100, color='#FFFFFF', background_color='#000000'))
        self.link_input = toga.MultilineTextInput(readonly=True, style=Pack(flex=1, color='#FFFFFF', background_color='#221111'))
        link_box = toga.Box(style=Pack(direction=COLUMN, padding=5, background_color='#000000'))
        link_box.add(link_label)
        link_box.add(self.link_input)

        # 开始按钮
        # start_button = toga.Button('开始分享', on_press=self.start_sharing, style=Pack(padding=5, color='#FFFFFF', background_color='#006600'))

        # 停止按钮
        # stop_button = toga.Button('停止分享', on_press=self.stop_sharing, style=Pack(padding=5, color='#FFFFFF', background_color='#660000'))

        # 分享开关
        self.sharing_switch = toga.Switch('开始/停止分享', on_change =self.toggle_sharing, value=self.sharing, style=Pack(padding=5, color='#FFFFFF', background_color='#006600'))



        # FTP 设置
        ftp_username_label = toga.Label('FTP 用户名:', style=Pack(width=100, color='#FFFFFF', background_color='#000000'))
        self.ftp_username_input = toga.TextInput(value='user',style=Pack(flex=1, color='#FFFFFF', background_color='#221111'))
        ftp_password_label = toga.Label('FTP 密码:', style=Pack(width=100, color='#FFFFFF', background_color='#000000'))
        self.ftp_password_input = toga.TextInput(value='123456',style=Pack(flex=1, color='#FFFFFF', background_color='#221111'))
        ftp_port_label = toga.Label('FTP 端口:', style=Pack(width=100, color='#FFFFFF', background_color='#000000'))
        self.ftp_port_input = toga.NumberInput(min_value=1024, max_value=65535, value=2121, style=Pack(flex=1, color='#FFFFFF', background_color='#221111'))

        # FTP 分享开关
        self.ftp_sharing_switch = toga.Switch('FTP 开始/停止分享', on_change=self.toggle_ftp_sharing, value=False, style=Pack(padding=5, color='#FFFFFF', background_color='#006600'))


        # 添加到主窗口
        self.main_box.add(folder_box)
        self.main_box.add(port_box)
        self.main_box.add(link_box)
        # self.main_box.add(start_button)
        # self.main_box.add(stop_button)
        self.main_box.add(self.sharing_switch)  # 添加滑块开关

        self.main_box.add(ftp_username_label)
        self.main_box.add(self.ftp_username_input)
        self.main_box.add(ftp_password_label)
        self.main_box.add(self.ftp_password_input)
        self.main_box.add(ftp_port_label)
        self.main_box.add(self.ftp_port_input)
        self.main_box.add(self.ftp_sharing_switch)

        self.update_ip_addresses_and_link()
        if self.tmp_folder_path_choice is not None:
            self.folder_path.value = self.tmp_folder_path_choice

    def select_folder(self, widget):
        self.current_view = 'folder'
        self.setup_folder_select_view(self.tmp_folder_path_choice)
        

    def setup_folder_select_view(self, root_path):
        # 清空当前视图
        self.main_box.remove(*self.main_box.children)
        
        # 创建文件夹树结构
        scroll_container = toga.ScrollContainer(style=Pack(direction=COLUMN, padding=10, background_color='#000000'))
        tree_box = toga.Box(style=Pack(direction=COLUMN, padding=10, background_color='#000000'))

        # 返回初始目录按钮
        home_button = toga.Button('初始目录', on_press=lambda w, p=self.init_folder_path: self.setup_folder_select_view(p), style=Pack(color='#FFFFFF', background_color='#005555'))
        tree_box.add(home_button)

        # 添加返回上一级按钮
        back_button = toga.Button('返回上一级', on_press=lambda w, p=root_path: self.navigate_to_parent_folder(p), style=Pack(color='#FFFFFF', background_color='#000066'))
        tree_box.add(back_button)

        # 添加选择当前文件夹按钮
        select_button = toga.Button('选择此文件夹', on_press=lambda w, p=root_path: self.select_current_folder(p), style=Pack(color='#FFFFFF', background_color='#006600'))
        tree_box.add(select_button)

        for item in os.listdir(root_path):
            full_path = os.path.join(root_path, item)
            if os.path.isdir(full_path):
                button = toga.Button(item, on_press=lambda w, p=full_path: self.navigate_to_folder(p), style=Pack(color='#FFFFFF', background_color='#002222'))
                tree_box.add(button)

        scroll_container = toga.ScrollContainer(content=tree_box, vertical=True, horizontal=False, style=Pack(flex=1, background_color='#000000'))
        self.main_box.add(scroll_container)

    def navigate_to_folder(self, folder_path):
        self.setup_folder_select_view(folder_path)

    def navigate_to_parent_folder(self, folder_path):
        parent_path = os.path.dirname(folder_path)
        self.setup_folder_select_view(parent_path)

    def select_current_folder(self, folder_path):
        # self.folder_path.value = folder_path
        self.tmp_folder_path_choice = folder_path
        self.current_view = 'main'
        self.setup_main_view()

    def get_ip_addresses(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        # print(s.getsockname()[0])
        ips = []
        ips.append(s.getsockname()[0])
        ips.append('安卓只支持获取一个局域网ip')
        return ips

    def update_ip_addresses(self):
        ips = []
        #如果不是安卓系统
        if os.name != 'posix':
            hostname = socket.gethostname()
            addresses = socket.getaddrinfo(hostname, None)
            for address in addresses:
                family, _, _, _, sockaddr = address
                if family == socket.AF_INET:  # 只关心IPv4地址
                    ip = sockaddr[0]
                    if ip != '127.0.0.1':  # 排除回环地址
                        ips.append(ip)
            if not ips:
                ips.append('127.0.0.1')
        else:
            ips = self.get_ip_addresses()   #只支持获取一个局域网ip
        return ips

    def update_ip_addresses_and_link(self):
        ips = self.update_ip_addresses()

        #如果端口号为空，则将其设为8000
        if not self.port_input.value:
            self.port_input.value = 8000

        port = int(self.port_input.value)
        self.link_input.value = '\n'.join([f"http://{ip}:{port}" for ip in ips])


    def toggle_sharing(self, widget):
        if widget.value:
            self.start_sharing(widget)
        else:
            self.stop_sharing(widget)


    def start_sharing(self, widget):
        if not self.sharing:  # 防止重复启动
            share_folder = self.folder_path.value
            port = int(self.port_input.value)
            if share_folder and os.path.isdir(share_folder):
                os.chdir(share_folder)
                self.server_thread = threading.Thread(target=self.run_server, args=(port,))
                self.server_thread.daemon = True
                self.server_thread.start()
                self.update_ip_addresses_and_link()
                self.main_window.info_dialog('提示', f'文件夹正在通过端口{port}分享')
                self.sharing = True  # 更新分享状态
            else:
                self.main_window.error_dialog('错误', '请选择有效的文件夹')

    def stop_sharing(self, widget):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.server_thread.join()
            self.httpd = None
            self.server_thread = None
            self.main_window.info_dialog('提示', '文件夹分享已停止')
            self.sharing = False  # 更新分享状态
        else:
            self.main_window.error_dialog('错误', '没有正在进行的分享')

    def run_server(self, port):
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", port), handler) as httpd:
            self.httpd = httpd
            print(f"Serving on port {port}")
            httpd.serve_forever()

    def toggle_ftp_sharing(self, widget):
        if widget.value:
            self.start_ftp_sharing(widget)
        else:
            self.stop_ftp_sharing(widget)

    def start_ftp_sharing(self, widget):
        if not self.sharing:  # 防止重复启动
            share_folder = self.folder_path.value
            port = int(self.ftp_port_input.value)
            #如果用户名和密码为空，则将其设为user和123456
            if not self.ftp_username_input.value:
                self.ftp_username_input.value = 'user'
            if not self.ftp_password_input.value:
                self.ftp_password_input.value = '123456'
            username = self.ftp_username_input.value
            password = self.ftp_password_input.value
            if share_folder and os.path.isdir(share_folder):
                self.server_thread = threading.Thread(target=ffttpp, args=(username, password, share_folder, port))
                self.server_thread.daemon = True
                self.server_thread.start()
                self.main_window.info_dialog('提示', f'FTP 服务器正在通过端口{port}分享')
                self.sharing = True  # 更新分享状态
            else:
                self.main_window.error_dialog('错误', '请选择有效的文件夹')

    def stop_ftp_sharing(self, widget):
        if self.server_thread is not None and self.server_thread.is_alive():
            # 这里需要实现停止FTP服务器的方法
            # 由于pyftpdlib的FTPServer没有提供直接关闭的方法，这里可以考虑使用标志位来控制
            # 或者在另一个线程中通过调用os._exit(0)强制退出子线程
            self.server_thread = None
            self.main_window.error_dialog('警告', '重启应用程序以退出FTP服务')
            self.sharing = False  # 更新分享状态
        else:
            self.main_window.error_dialog('错误', '没有正在进行的FTP分享')

def main():
    return FolderShareApp()