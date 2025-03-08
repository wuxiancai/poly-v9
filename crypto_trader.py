# -*- coding: utf-8 -*-
# polymarket_v1.0.0
import platform
import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import json
import threading
import time
import os
import logging
import pytesseract
from datetime import datetime, timezone, timedelta
import re
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import pyautogui
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import socket
import sys
import logging
from xpath_config import XPathConfig
from threading import Thread

class Logger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 创建logs目录（如果不存在）
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # 设置日志文件名（使用当前日期）
        log_filename = f"logs/{datetime.now().strftime('%Y%m%d')}.log"
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        
        # 创建格式器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器到logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message):
        self.logger.debug(message)
    
    def info(self, message):
        self.logger.info(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def critical(self, message):
        self.logger.critical(message)
    

class CryptoTrader:
    def __init__(self):
        super().__init__()
        self.logger = Logger('Poly')
        self.driver = None
        self.running = False
        self.trading = False
        self.url_check_timer = None
        self.is_checking_prices = False
        # 添加以下属性用于管理auto_find_54_coin线程
        self.auto_find_thread = None  # 存储auto_find_54_coin线程对象
        self.stop_auto_find = False   # 控制auto_find_54_coin线程停止的标志
        self.driver_lock = threading.Lock()  # 添加浏览器操作锁
        self.url_monitoring_lock = threading.Lock()  # 新增线程锁
        self.retry_count = 3
        self.retry_interval = 5
        # 添加交易次数计数器
        self.trade_count = 0
        self.sell_count = 0  # 添加卖出计数器
        self.refresh_interval = 600000  # 10分钟
        self.refresh_timer = None  # 用于存储定时器ID
        self.default_target_price = 0.54
        self._amounts_logged = False
        # 在初始化部分添加
        self.stop_event = threading.Event()
        # 添加性能监控标志
        self.enable_performance_monitor = True
        # 初始化金额属性
        for i in range(1, 4):  # 1到3
            setattr(self, f'yes{i}_amount', 0.0)
            setattr(self, f'no{i}_amount', 0.0)

        try:
            self.config = self.load_config()
            self.setup_gui()
            
            # 获取屏幕尺寸并设置窗口位置
            self.root.update_idletasks()  # 确保窗口尺寸已计算
            window_width = self.root.winfo_width()
            screen_height = self.root.winfo_screenheight()
            
            # 设置窗口位置在屏幕最左边
            self.root.geometry(f"{window_width}x{screen_height}+0+0")
        except Exception as e:
            self.logger.error(f"初始化失败: {str(e)}")
            messagebox.showerror("错误", "程序初始化失败，请检查日志文件")
            sys.exit(1)

        # 打印启动参数
        self.logger.info(f"程序初始化,启动参数: {sys.argv}")
    
        # 检查是否是重启
        self.is_restart = '--restart' in sys.argv
        
        # 如果是重启,延迟2秒后自动点击开始监控
        if self.is_restart:
            self.logger.info("检测到重启模式,安排自动点击开始按钮！")
            self.root.after(10000, self.auto_start_monitor)
      
        # 添加登录状态监控定时器
        self.login_check_timer = None
        self.driver_lock = threading.Lock()  # 添加浏览器操作锁

    def load_config(self):
        """加载配置文件，保持默认格式"""
        try:
            # 默认配置
            default_config = {
                'website': {'url': ''},
                'trading': {
                    'Yes1': {'target_price': 0.0, 'amount': 0.0},
                    'Yes2': {'target_price': 0.0, 'amount': 0.0},
                    'Yes3': {'target_price': 0.0, 'amount': 0.0},
                    'Yes4': {'target_price': 0.0, 'amount': 0.0},
                    'Yes5': {'target_price': 0.0, 'amount': 0.0},

                    'No1': {'target_price': 0.0, 'amount': 0.0},
                    'No2': {'target_price': 0.0, 'amount': 0.0},
                    'No3': {'target_price': 0.0, 'amount': 0.0},
                    'No4': {'target_price': 0.0, 'amount': 0.0},
                    'No5': {'target_price': 0.0, 'amount': 0.0}
                },
                'url_history': []
            }
            
            try:
                # 尝试读取现有配置
                with open('config.json', 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.logger.info("成功加载配置文件")
                    
                    # 合并配置
                    for key in default_config:
                        if key not in saved_config:
                            saved_config[key] = default_config[key]
                        elif isinstance(default_config[key], dict):
                            for sub_key in default_config[key]:
                                if sub_key not in saved_config[key]:
                                    saved_config[key][sub_key] = default_config[key][sub_key]
                    return saved_config
            except FileNotFoundError:
                self.logger.warning("配置文件不存在，创建默认配置")
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                return default_config
            except json.JSONDecodeError:
                self.logger.error("配置文件格式错误，使用默认配置")
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                return default_config
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            raise
    
    def save_config(self):
        """保存配置到文件,保持JSON格式化"""
        try:
            for position, frame in [('Yes', self.yes_frame), ('No', self.no_frame)]:
                # 精确获取目标价格和金额的输入框
                entries = [
                    w for w in frame.winfo_children() 
                    if isinstance(w, ttk.Entry) and "price" in str(w).lower()
                ]
                amount_entries = [
                    w for w in frame.winfo_children()
                    if isinstance(w, ttk.Entry) and "amount" in str(w).lower()
                ]

                # 添加类型转换保护
                try:
                    target_price = float(entries[0].get().strip() or '0.0') if entries else 0.0
                except ValueError as e:
                    self.logger.error(f"价格转换失败: {e}, 使用默认值0.0")
                    target_price = 0.0

                try:
                    amount = float(amount_entries[0].get().strip() or '0.0') if amount_entries else 0.0
                except ValueError as e:
                    self.logger.error(f"金额转换失败: {e}, 使用默认值0.0")
                    amount = 0.0

                # 使用正确的配置键格式
                config_key = f"{position}0"  # 改为Yes1/No1
                self.config['trading'][config_key]['target_price'] = target_price
                self.config['trading'][config_key]['amount'] = amount

            # 处理网站地址历史记录
            current_url = self.url_entry.get().strip()
            if current_url:
                if 'url_history' not in self.config:
                    self.config['url_history'] = []
                
                # 清空历史记录
                self.config['url_history'].clear()
                # 只保留当前URL
                self.config['url_history'].insert(0, current_url)
                # 确保最多保留1条
                self.config['url_history'] = self.config['url_history'][:1]
                self.url_entry['values'] = self.config['url_history']
            
            # 保存配置到文件，使用indent=4确保格式化
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f)
                
        except Exception as e:
            self.logger.error(f"保存配置失败: {str(e)}")
            raise

    """从这里开始设置 GUI 直到 790 行"""
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Polymarket 4 次重启无线循环完全自动化交易,6%利润率！")

        # 创建主滚动框架
        main_canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)

        # 配置滚动区域
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        # 在 Canvas 中创建窗口
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        # 简化的滚动事件处理
        def _on_mousewheel(event):
            try:
                if platform.system() == 'Linux':
                    if event.num == 4:
                        main_canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        main_canvas.yview_scroll(1, "units")
                elif platform.system() == 'Darwin':
                    main_canvas.yview_scroll(-int(event.delta), "units")
                else:  # Windows
                    main_canvas.yview_scroll(-int(event.delta/120), "units")
            except Exception as e:
                self.logger.error(f"滚动事件处理错误: {str(e)}")

        # 绑定滚动事件
        if platform.system() == 'Linux':
            main_canvas.bind_all("<Button-4>", _on_mousewheel)
            main_canvas.bind_all("<Button-5>", _on_mousewheel)
        else:
            main_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 添加简化的键盘滚动支持
        def _on_arrow_key(event):
            try:
                if event.keysym == 'Up':
                    main_canvas.yview_scroll(-1, "units")
                elif event.keysym == 'Down':
                    main_canvas.yview_scroll(1, "units")
            except Exception as e:
                self.logger.error(f"键盘滚动事件处理错误: {str(e)}")

        # 绑定方向键
        main_canvas.bind_all("<Up>", _on_arrow_key)
        main_canvas.bind_all("<Down>", _on_arrow_key)
        
        # 放置滚动组件
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        """创建按钮和输入框样式"""
        style = ttk.Style()
        style.configure('Red.TButton', foreground='red', font=('TkDefaultFont', 13, 'bold'))
        style.configure('Black.TButton', foreground='black', font=('TkDefaultFont', 13, 'normal'))
        style.configure('Red.TEntry', foreground='red', font=('TkDefaultFont', 13, 'normal'))
        style.configure('Blue.TButton', foreground='blue', font=('TkDefaultFont', 13, 'normal'))
        style.configure('Blue.TLabel', foreground='blue', font=('TkDefaultFont', 13, 'normal'))
        style.configure('Red.TLabel', foreground='red', font=('TkDefaultFont', 13, 'normal'))
        style.configure('Red.TLabelframe.Label', foreground='red')  # 设置标签文本颜色为红色
        style.configure('Black.TLabel', foreground='black', font=('TkDefaultFont', 13, 'normal'))
        style.configure('Warning.TLabelframe.Label', font=('TkDefaultFont', 18, 'bold'),foreground='red', anchor='center', justify='center')
        
        # 金额设置框架
        amount_settings_frame = ttk.LabelFrame(scrollable_frame, 
                                               text="以时间换利润，不可贪心，否则一定亏钱!", padding=(2, 5), style='Warning.TLabelframe')
        amount_settings_frame.pack(fill="x", padx=5, pady=5)

        # 创建一个Frame来水平排列标题和警告
        title_frame = ttk.Frame(amount_settings_frame)
        title_frame.pack(fill="x", padx=5, pady=5)

        # 添加标题和红色警告文本在同一行
        ttk.Label(title_frame, 
                text="完全自动化交易!不得人为干预程序!",
                foreground='red',
                font=('TkDefaultFont', 18, 'bold')).pack(side=tk.RIGHT, expand=True)

        # 创建金额设置容器的内部框架
        settings_container = ttk.Frame(amount_settings_frame)
        settings_container.pack(fill=tk.X, anchor='w')
        
        # 创建两个独立的Frame
        amount_frame = ttk.Frame(settings_container)
        amount_frame.grid(row=0, column=0, sticky='w')
        trades_frame = ttk.Frame(settings_container)
        trades_frame.grid(row=1, column=0, sticky='w')

        # 初始金额等输入框放在amount_frame中
        initial_frame = ttk.Frame(amount_frame)
        initial_frame.pack(side=tk.LEFT, padx=2)
        ttk.Label(initial_frame, text="初始金额(%):").pack(side=tk.LEFT)
        self.initial_amount_entry = ttk.Entry(initial_frame, width=3)
        self.initial_amount_entry.pack(side=tk.LEFT)
        self.initial_amount_entry.insert(0, "6")
        
        # 反水一次设置
        first_frame = ttk.Frame(amount_frame)
        first_frame.pack(side=tk.LEFT, padx=2)
        ttk.Label(first_frame, text="反水一(%):").pack(side=tk.LEFT)
        self.first_rebound_entry = ttk.Entry(first_frame, width=3)
        self.first_rebound_entry.pack(side=tk.LEFT)
        self.first_rebound_entry.insert(0, "300")
        
        # 反水N次设置
        n_frame = ttk.Frame(amount_frame)
        n_frame.pack(side=tk.LEFT, padx=2)
        ttk.Label(n_frame, text="反水N(%):").pack(side=tk.LEFT)
        self.n_rebound_entry = ttk.Entry(n_frame, width=3)
        self.n_rebound_entry.pack(side=tk.LEFT)
        self.n_rebound_entry.insert(0, "160")

        # 利润率设置
        profit_frame = ttk.Frame(amount_frame)
        profit_frame.pack(side=tk.LEFT, padx=2)
        ttk.Label(profit_frame, text="利率(%):").pack(side=tk.LEFT)
        self.profit_rate_entry = ttk.Entry(profit_frame, width=2)
        self.profit_rate_entry.pack(side=tk.LEFT)
        self.profit_rate_entry.insert(0, "6")

        # 翻倍周数
        weeks_frame = ttk.Frame(amount_frame)
        weeks_frame.pack(side=tk.LEFT, padx=2)
        self.doubling_weeks_entry = ttk.Entry(weeks_frame, width=2, style='Red.TEntry')
        self.doubling_weeks_entry.pack(side=tk.LEFT)
        self.doubling_weeks_entry.insert(0, "15")
        ttk.Label(weeks_frame, text="周翻倍", style='Red.TLabel').pack(side=tk.LEFT)

        # 交易次数按钮放在trades_frame中
        ttk.Label(trades_frame, text="交易次数:", style='Black.TLabel').pack(side=tk.LEFT, padx=(2,2))
        buttons_frame = ttk.Frame(trades_frame)
        buttons_frame.pack(side=tk.LEFT, padx=(0,0))

        # 次数按钮
        self.trade_buttons = {}  # 保存按钮引用
        
        # 4按钮
        self.trade_buttons["4"] = ttk.Button(buttons_frame, text="4", width=3, style='Blue.TButton')
        self.trade_buttons["4"].grid(row=1, column=1, padx=2, pady=3)

        # 添加搜索BTC周链接按钮
        self.btc_button = ttk.Button(buttons_frame, text="BTC", 
                                         command=lambda: self.find_new_weekly_url('BTC'), width=3,
                                         style='Blue.TButton')
        self.btc_button.grid(row=1, column=3, padx=2, pady=3)

        # 添加搜索ETH周链接按钮
        self.eth_button = ttk.Button(buttons_frame, text="ETH", 
                                         command=lambda: self.find_new_weekly_url('ETH'), width=3,
                                         style='Blue.TButton')
        self.eth_button.grid(row=1, column=4, padx=2, pady=3)

        # 添加搜索SOLANA周链接按钮
        self.solana_button = ttk.Button(buttons_frame, text="SOL", 
                                         command=lambda: self.find_new_weekly_url('SOLANA'), width=3,
                                         style='Blue.TButton')
        self.solana_button.grid(row=1, column=5, padx=2, pady=3)

        # 添加搜索XRP周链接按钮
        self.xrp_button = ttk.Button(buttons_frame, text="XRP", 
                                         command=lambda: self.find_new_weekly_url('XRP'), width=3,
                                         style='Blue.TButton')
        self.xrp_button.grid(row=1, column=6, padx=2, pady=3)

        # 添加搜索DOGE周链接按钮
        self.doge_button = ttk.Button(buttons_frame, text="DOGE", 
                                         command=lambda: self.find_new_weekly_url('DOGE'), width=5,
                                         style='Blue.TButton')
        self.doge_button.grid(row=1, column=7, padx=2, pady=3)

        # 配置列权重使输入框均匀分布
        for i in range(8):
            settings_container.grid_columnconfigure(i, weight=1)

        # 设置窗口大小和位置
        window_width = 540
        window_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
        # 监控网站配置
        url_frame = ttk.LabelFrame(scrollable_frame, text="监控网站配置", padding=(2, 2))
        url_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(url_frame, text="地址:", font=('Arial', 10)).grid(row=0, column=0, padx=5, pady=5)
        
        # 创建下拉列和输入框组合控件
        self.url_entry = ttk.Combobox(url_frame, width=49)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # 从配置文件加载历史记录
        if 'url_history' not in self.config:
            self.config['url_history'] = []
        self.url_entry['values'] = self.config['url_history']
        
        # 如果有当前URL，设置为默认值
        current_url = self.config.get('website', {}).get('url', '')
        if current_url:
            self.url_entry.set(current_url)
        
        # 控制按钮区域
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        # 开始和停止按钮
        self.start_button = ttk.Button(button_frame, text="开始监控", 
                                          command=self.start_monitoring, width=8,
                                          style='Black.TButton')  # 默认使用黑色文字
        self.start_button.pack(side=tk.LEFT, padx=2)
        
        
        self.stop_button = ttk.Button(button_frame, text="停止监控", 
                                     command=self.stop_monitoring, width=8,
                                     style='Black.TButton')  # 默认使用黑色文字
        self.stop_button.pack(side=tk.LEFT, padx=2)
        self.stop_button['state'] = 'disabled'
        
        # 更新下单金额按钮
        self.update_amount_button = ttk.Button(button_frame, text="更新下单金额", 
                                             command=self.set_yes_no_cash, width=10,
                                             style='Black.TButton')  # 默认使用黑色文字
        self.update_amount_button.pack(side=tk.LEFT, padx=2)
        self.update_amount_button['state'] = 'disabled'  # 初始禁用

        # 添加价格按钮
        prices = ['0.54', '0.55']
        for price in prices:
            btn = ttk.Button(
                button_frame, 
                text=price,
                width=3.5,
                command=lambda p=price: self.set_default_price(p),
                style='Red.TButton' if price == '0.54' else 'Black.TButton'
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # 交易币对显示区域
        pair_frame = ttk.Frame(scrollable_frame)
        pair_frame.pack(fill="x", padx=2, pady=5)
        
        # 添加交易币对显示区域
        pair_container = ttk.Frame(pair_frame)
        pair_container.pack(anchor="center")
        
        # 交易币种及日期，颜色为蓝色
        ttk.Label(pair_container, text="交易币种及日期:", 
                 font=('Arial', 14), foreground='blue').pack(side=tk.LEFT, padx=5)
        self.trading_pair_label = ttk.Label(pair_container, text="--", 
                                        font=('Arial', 16, 'bold'), foreground='blue')
        self.trading_pair_label.pack(side=tk.LEFT, padx=5)
        
        # 修改实时价格显示区域
        price_frame = ttk.LabelFrame(scrollable_frame, text="实时价格", padding=(5, 5))
        price_frame.pack(padx=5, pady=5, fill="x")
        
        # 创建一个框架来水平排列所有价格信息
        prices_container = ttk.Frame(price_frame)
        prices_container.pack(expand=True)  # 添加expand=True使容器居中
        
        # Yes实时价格显示
        self.yes_price_label = ttk.Label(prices_container, text="Yes: 等待数据...", 
                                        font=('Arial', 20), foreground='#9370DB')
        self.yes_price_label.pack(side=tk.LEFT, padx=20)
        
        # No实时价格显示
        self.no_price_label = ttk.Label(prices_container, text="No: 等待数据...", 
                                       font=('Arial', 20), foreground='#9370DB')
        self.no_price_label.pack(side=tk.LEFT, padx=20)
        
        # 最后更新时间 - 靠右下对齐
        self.last_update_label = ttk.Label(price_frame, text="最后更新: --", 
                                          font=('Arial', 2))
        self.last_update_label.pack(side=tk.LEFT, anchor='se', padx=5)
        
        # 修改实时资金显示区域
        balance_frame = ttk.LabelFrame(scrollable_frame, text="实时资金", padding=(5, 5))
        balance_frame.pack(padx=5, pady=5, fill="x")
        
        # 创建一个框架来水平排列所有资金信息
        balance_container = ttk.Frame(balance_frame)
        balance_container.pack(expand=True)  # 添加expand=True使容器居中
        
        # Portfolio显示
        self.portfolio_label = ttk.Label(balance_container, text="Portfolio: 等待数据...", 
                                        font=('Arial', 20), foreground='#9370DB') # 修改为绿色
        self.portfolio_label.pack(side=tk.LEFT, padx=20)
        
        # Cash显示
        self.cash_label = ttk.Label(balance_container, text="Cash: 等待数据...", 
                                   font=('Arial', 20), foreground='#9370DB') # 修改为绿色
        self.cash_label.pack(side=tk.LEFT, padx=20)
        
        # 最后更新时间 - 靠右下对齐
        self.balance_update_label = ttk.Label(balance_frame, text="最后更新: --", 
                                           font=('Arial', 2))
        self.balance_update_label.pack(side=tk.LEFT, anchor='se', padx=5)
        
        # 创建Yes/No
        config_frame = ttk.Frame(scrollable_frame)
        config_frame.pack(fill="x", padx=2, pady=5)
        
        # 左右分栏显示Yes/No配置
        # YES 区域配置
        self.yes_frame = ttk.LabelFrame(config_frame, text="Yes配置", padding=(2, 3))
        self.yes_frame.grid(row=0, column=0, padx=2, sticky="ew")
        config_frame.grid_columnconfigure(0, weight=1)
        
        # YES1 价格
        ttk.Label(self.yes_frame, text="Yes 1 价格($):", font=('Arial', 12)).grid(row=0, column=0, padx=2, pady=5)
        self.yes1_price_entry = ttk.Entry(self.yes_frame,width=15)
        self.yes1_price_entry.insert(0, str(self.config['trading']['Yes1']['target_price']))
        self.yes1_price_entry.grid(row=0, column=1, padx=2, pady=5, sticky="ew")

        # yes2 价格
        ttk.Label(self.yes_frame, text="Yes 2 价格($):", font=('Arial', 12)).grid(row=2, column=0, padx=2, pady=5)
        self.yes2_price_entry = ttk.Entry(self.yes_frame,width=15)  # 添加self
        self.yes2_price_entry.delete(0, tk.END)
        self.yes2_price_entry.insert(0, "0.00")
        self.yes2_price_entry.grid(row=2, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes3 价格
        ttk.Label(self.yes_frame, text="Yes 3 价格($):", font=('Arial', 12)).grid(row=4, column=0, padx=2, pady=5)
        self.yes3_price_entry = ttk.Entry(self.yes_frame,width=15)  # 添加self
        self.yes3_price_entry.delete(0, tk.END)
        self.yes3_price_entry.insert(0, "0.00")
        self.yes3_price_entry.grid(row=4, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes4 价格
        ttk.Label(self.yes_frame, text="Yes 4 价格($):", font=('Arial', 12)).grid(row=6, column=0, padx=2, pady=5)
        self.yes4_price_entry = ttk.Entry(self.yes_frame,width=15)  # 添加self
        self.yes4_price_entry.delete(0, tk.END)
        self.yes4_price_entry.insert(0, "0.00")
        self.yes4_price_entry.grid(row=6, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes5 价格
        ttk.Label(self.yes_frame, text="Yes 5 价格($):", font=('Arial', 12)).grid(row=8, column=0, padx=2, pady=5)
        self.yes5_price_entry = ttk.Entry(self.yes_frame,width=15)  # 添加self
        self.yes5_price_entry.delete(0, tk.END)
        self.yes5_price_entry.insert(0, "0.00")
        self.yes5_price_entry.grid(row=8, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes1 金额
        ttk.Label(self.yes_frame, text="Yes 1 金额:", font=('Arial', 12)).grid(row=1, column=0, padx=2, pady=5)
        self.yes1_amount_entry = ttk.Entry(self.yes_frame,width=15)
        self.yes1_amount_entry.insert(0, str(self.config['trading']['Yes1']['amount']))
        self.yes1_amount_entry.grid(row=1, column=1, padx=2, pady=5, sticky="ew")

        # yes2 金额
        ttk.Label(self.yes_frame, text="Yes 2 金额:", font=('Arial', 12)).grid(row=3, column=0, padx=2, pady=5)
        self.yes2_amount_entry = ttk.Entry(self.yes_frame,width=15)  # 添加self
        self.yes2_amount_entry.insert(0, "0.0")
        self.yes2_amount_entry.grid(row=3, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes3 金额
        ttk.Label(self.yes_frame, text="Yes 3 金额:", font=('Arial', 12)).grid(row=5, column=0, padx=2, pady=5)
        self.yes3_amount_entry = ttk.Entry(self.yes_frame,width=15)  # 添加self
        self.yes3_amount_entry.insert(0, "0.0")
        self.yes3_amount_entry.grid(row=5, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # yes4 金额
        ttk.Label(self.yes_frame, text="Yes 4 金额:", font=('Arial', 12)).grid(row=7, column=0, padx=2, pady=5)
        self.yes4_amount_entry = ttk.Entry(self.yes_frame,width=15)  # 添加self
        self.yes4_amount_entry.insert(0, "0.0")
        self.yes4_amount_entry.grid(row=7, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No 配置区域
        self.no_frame = ttk.LabelFrame(config_frame, text="No配置", padding=(10, 5))
        self.no_frame.grid(row=0, column=1, padx=2, sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)

        # No1 价格
        ttk.Label(self.no_frame, text="No 1 价格($):", font=('Arial', 12)).grid(row=0, column=0, padx=2, pady=5)
        self.no1_price_entry = ttk.Entry(self.no_frame,width=15)
        self.no1_price_entry.insert(0, str(self.config['trading']['No1']['target_price']))
        self.no1_price_entry.grid(row=0, column=1, padx=2, pady=5, sticky="ew")

        # No2 价格
        ttk.Label(self.no_frame, text="No 2 价格($):", font=('Arial', 12)).grid(row=2, column=0, padx=2, pady=5)
        self.no2_price_entry = ttk.Entry(self.no_frame,width=15)  # 添加self
        self.no2_price_entry.delete(0, tk.END)
        self.no2_price_entry.insert(0, "0.00")
        self.no2_price_entry.grid(row=2, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No3 价格
        ttk.Label(self.no_frame, text="No 3 价格($):", font=('Arial', 12)).grid(row=4, column=0, padx=2, pady=5)
        self.no3_price_entry = ttk.Entry(self.no_frame,width=15)  # 添加self
        self.no3_price_entry.delete(0, tk.END)
        self.no3_price_entry.insert(0, "0.00")
        self.no3_price_entry.grid(row=4, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No4 价格
        ttk.Label(self.no_frame, text="No 4 价格($):", font=('Arial', 12)).grid(row=6, column=0, padx=2, pady=5)
        self.no4_price_entry = ttk.Entry(self.no_frame,width=15)  # 添加self
        self.no4_price_entry.delete(0, tk.END)
        self.no4_price_entry.insert(0, "0.00")
        self.no4_price_entry.grid(row=6, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No5 价格
        ttk.Label(self.no_frame, text="No 5 价格($):", font=('Arial', 12)).grid(row=8, column=0, padx=2, pady=5)
        self.no5_price_entry = ttk.Entry(self.no_frame,width=15)  # 添加self
        self.no5_price_entry.delete(0, tk.END)
        self.no5_price_entry.insert(0, "0.00")
        self.no5_price_entry.grid(row=8, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # NO1 金额
        ttk.Label(self.no_frame, text="No 1 金额:", font=('Arial', 12)).grid(row=1, column=0, padx=2, pady=5)
        self.no1_amount_entry = ttk.Entry(self.no_frame,width=15)
        self.no1_amount_entry.insert(0, str(self.config['trading']['No1']['amount']))
        self.no1_amount_entry.grid(row=1, column=1, padx=2, pady=5, sticky="ew")

        # No2 金额
        ttk.Label(self.no_frame, text="No 2 金额:", font=('Arial', 12)).grid(row=3, column=0, padx=2, pady=5)
        self.no2_amount_entry = ttk.Entry(self.no_frame,width=15)  # 添加self
        self.no2_amount_entry.insert(0, "0.0")
        self.no2_amount_entry.grid(row=3, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No3 金额
        ttk.Label(self.no_frame, text="No 3 金额:", font=('Arial', 12)).grid(row=5, column=0, padx=2, pady=5)
        self.no3_amount_entry = ttk.Entry(self.no_frame,width=15)  # 添加self
        self.no3_amount_entry.insert(0, "0.0")
        self.no3_amount_entry.grid(row=5, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # No4 金额
        ttk.Label(self.no_frame, text="No 4 金额:", font=('Arial', 12)).grid(row=7, column=0, padx=2, pady=5)
        self.no4_amount_entry = ttk.Entry(self.no_frame,width=15)  # 添加self
        self.no4_amount_entry.insert(0, "0.0")
        self.no4_amount_entry.grid(row=7, column=1, padx=2, pady=5, sticky="ew")  # 修正grid位置

        # 创建买入按钮区域
        buy_frame = ttk.LabelFrame(scrollable_frame, text="买入按钮", padding=(2, 0))
        buy_frame.pack(fill="x", padx=(0,0), pady=5)

        # 创建按钮框架
        buy_button_frame = ttk.Frame(buy_frame)
        buy_button_frame.pack(side=tk.LEFT, padx=2)  # 添加expand=True使容器居中

        # 第一行按钮
        self.buy_button = ttk.Button(buy_button_frame, text="Buy", width=9,
                                    command=self.click_buy)
        self.buy_button.grid(row=0, column=0, padx=5, pady=5)

        self.buy_yes_button = ttk.Button(buy_button_frame, text="Buy.Yes", width=9,
                                        command=self.click_buy_yes)
        self.buy_yes_button.grid(row=0, column=1, padx=5, pady=5)

        self.buy_no_button = ttk.Button(buy_button_frame, text="Buy.No", width=9,
                                       command=self.click_buy_no)
        self.buy_no_button.grid(row=0, column=2, padx=5, pady=5)

        self.buy_confirm_button = ttk.Button(buy_button_frame, text="Buy.confirm", width=9,
                                            command=self.click_buy_confirm_button)
        self.buy_confirm_button.grid(row=0, column=3, padx=5, pady=5)

        # 第二行按钮
        self.amount_yes1_button = ttk.Button(buy_button_frame, text="Amount.Yes1", width=9)
        self.amount_yes1_button.bind('<Button-1>', self.click_amount)
        self.amount_yes1_button.grid(row=1, column=0, padx=5, pady=5)

        self.amount_yes2_button = ttk.Button(buy_button_frame, text="Amount.Yes2", width=9)
        self.amount_yes2_button.bind('<Button-1>', self.click_amount)
        self.amount_yes2_button.grid(row=1, column=1, padx=5, pady=5)

        self.amount_yes3_button = ttk.Button(buy_button_frame, text="Amount.Yes3", width=9)
        self.amount_yes3_button.bind('<Button-1>', self.click_amount)
        self.amount_yes3_button.grid(row=1, column=2, padx=5, pady=5)

        self.amount_yes4_button = ttk.Button(buy_button_frame, text="Amount.Yes4", width=9)
        self.amount_yes4_button.bind('<Button-1>', self.click_amount)
        self.amount_yes4_button.grid(row=1, column=3, padx=5, pady=5)

        # 第三行
        self.amount_no1_button = ttk.Button(buy_button_frame, text="Amount.No1", width=9)
        self.amount_no1_button.bind('<Button-1>', self.click_amount)
        self.amount_no1_button.grid(row=9, column=0, padx=5, pady=5)
        
        self.amount_no2_button = ttk.Button(buy_button_frame, text="Amount.No2", width=9)
        self.amount_no2_button.bind('<Button-1>', self.click_amount)
        self.amount_no2_button.grid(row=9, column=1, padx=5, pady=5)

        self.amount_no3_button = ttk.Button(buy_button_frame, text="Amount.No3", width=9)
        self.amount_no3_button.bind('<Button-1>', self.click_amount)
        self.amount_no3_button.grid(row=9, column=2, padx=5, pady=5)

        self.amount_no4_button = ttk.Button(buy_button_frame, text="Amount.No4", width=9)
        self.amount_no4_button.bind('<Button-1>', self.click_amount)
        self.amount_no4_button.grid(row=9, column=3, padx=5, pady=5)
 
        # 配置列权重使按钮均匀分布
        for i in range(4):
            buy_button_frame.grid_columnconfigure(i, weight=1)

        # 修改卖出按钮区域
        sell_frame = ttk.LabelFrame(scrollable_frame, text="卖出按钮", padding=(10, 5))
        sell_frame.pack(fill="x", padx=2, pady=5)

        # 创建按钮框架
        button_frame = ttk.Frame(sell_frame)
        button_frame.pack(side=tk.LEFT, padx=2)     

        # 第一行按钮
        self.position_sell_yes_button = ttk.Button(button_frame, text="Positions-Sell-Yes", width=13,
                                                 command=self.click_position_sell_yes)
        self.position_sell_yes_button.grid(row=0, column=0, padx=2, pady=5)

        self.position_sell_no_button = ttk.Button(button_frame, text="Positions-Sell-No", width=13,
                                                command=self.click_position_sell_no)
        self.position_sell_no_button.grid(row=0, column=1, padx=2, pady=5)

        self.sell_profit_button = ttk.Button(button_frame, text="Sell-profit", width=10,
                                           command=self.click_profit_sell)
        self.sell_profit_button.grid(row=0, column=2, padx=2, pady=5)

        # 第二行按钮
        self.sell_yes_button = ttk.Button(button_frame, text="Sell-Yes", width=8,
                                        command=self.click_sell_yes)
        self.sell_yes_button.grid(row=1, column=0, padx=2, pady=5)

        self.sell_no_button = ttk.Button(button_frame, text="Sell-No", width=8,
                                       command=self.click_sell_no)
        self.sell_no_button.grid(row=1, column=1, padx=2, pady=5)

        self.restart_button = ttk.Button(button_frame, text="重启", width=4,
                                    command=self.restart_program)
        self.restart_button.grid(row=1, column=2, padx=2, pady=5)

        # 配置列权重使按钮均匀分布
        for i in range(4):
            button_frame.grid_columnconfigure(i, weight=1)

        # 添加状态标签 (在卖出按钮区域之后)
        self.status_label = ttk.Label(scrollable_frame, text="状态: 未运行", 
                                     font=('Arial', 10, 'bold'))
        self.status_label.pack(pady=5)
        
        # 添加版权信息标签
        copyright_label = ttk.Label(scrollable_frame, text="Powered by 无为 Copyright 2024",
                                   font=('Arial', 12), foreground='gray')
        copyright_label.pack(pady=(0, 5))  # 上边距0，下距5


    """以上代码从240行到 790 行是设置 GUI 界面的"""

    """以下代码从 795 行到行是程序执行顺序逻辑"""
    def start_monitoring(self):
        
        # 启用价格和资金监控
        self.price_monitoring = True  
        self.balance_monitoring = True  

        # 重置交易次数计数器
        self.trade_count = 0
        
        # 直接使用当前网址
        self.target_url = self.url_entry.get()
        self.logger.info(f"开始监控网址: {self.target_url}")

        
        # 启用更金额按钮
        self.update_amount_button['state'] = 'normal'
        self.update_status("监控运行中...")

        # 启用开始按钮，启用停止按钮
        self.start_button['state'] = 'disabled'
        self.stop_button['state'] = 'normal'
            
        # 将"开始监控"文字变为红色
        self.start_button.configure(style='Red.TButton')

        # 恢复"停止监控"文字为黑色
        self.stop_button.configure(style='Black.TButton')

        # 启动浏览器作线程
        threading.Thread(target=self._start_browser_monitoring, args=(self.target_url,), daemon=True).start()
        self.running = True

        # 使用延时启动带错误处理
        def safe_start(target):
            try:
                target()
            except Exception as e:
                self.logger.error(f"线程启动失败: {str(e)}")
        # 启动登录状态监控
        self.login_timer = threading.Timer(10, safe_start, args=(self.start_login_monitoring,))
        self.login_timer.daemon = True
        self.login_timer.start()

        # 启动URL监控
        self.url_timer = threading.Timer(30, safe_start, args=(self.start_url_monitoring,))
        self.url_timer.daemon = True
        self.url_timer.start()

        # 启动自动找币
        self.find_coin_timer = threading.Timer(180, safe_start, args=(self.auto_find_54_coin,))
        self.find_coin_timer.daemon = True
        self.find_coin_timer.start()

        # 启动刷新页面
        self.first_refresh = True
        self.refresh_timer = threading.Timer(100, safe_start, args=(self.refresh_page,))
        self.refresh_timer.daemon = True
        self.refresh_timer.start()

        # 启动周六重启
        self.saturday_reboot_timer = threading.Timer(10, safe_start, args=(self.is_saturday_reboot_time,))
        self.saturday_reboot_timer.daemon = True
        self.saturday_reboot_timer.start()
   
    def _start_browser_monitoring(self, new_url):
        """在新线程中执行浏览器操作"""
        try:
            self.update_status(f"正在尝试访问: {new_url}")
            start_time = time.time()
            
            # 复用已有浏览器实例
            if self.driver and self.driver.service.process:
                try:
                    # 快速检查浏览器连接状态
                    _ = self.driver.current_url
                    self.logger.debug("复用现有浏览器实例")
                except:
                    self.driver.quit()
                    self.driver = None
            
            if not self.driver:
                chrome_options = Options()
                chrome_options.debugger_address = "127.0.0.1:9222"
                chrome_options.add_argument('--disable-dev-shm-usage')
                
                def init_browser():
                    try:
                        self.driver = webdriver.Chrome(options=chrome_options)
                        # 立即设置初始化标记
                        self.driver.execute_script("console.log('Browser Ready')")
                        self._browser_ready = True  
                        self.logger.info(f"浏览器初始化完成(耗时：{time.time()-start_time:.2f}s)")

                    except Exception as e:
                        self.logger.error(f"浏览器初始化失败: {str(e)}")
                        self._browser_ready = False

                # 启动初始化线程
                self._browser_ready = False
                init_thread = threading.Thread(target=init_browser, daemon=True)
                init_thread.start()
 
                # 等待浏览器基本就绪（非阻塞式检查）
                for _ in range(50):  # 最大等待5秒
                    if getattr(self, '_browser_ready', False):
                        break
                    time.sleep(0.1)
                else:
                    self.logger.warning("浏览器初始化超时，继续尝试操作")
                    
            try:
                # 在当前标签页打开URL
                self.driver.get(new_url)
                
                # 等待页面加载
                self.update_status("等待页面加载完成...")
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                # 验证页面加载成功
                current_url = self.driver.current_url
                self.update_status(f"成功加载网: {current_url}")
                
                # 保存配置
                if 'website' not in self.config:
                    self.config['website'] = {}
                self.config['website']['url'] = new_url
                self.save_config()
                
                # 更新交易币对显示
                try:
                    pair = re.search(r'event/([^?]+)', new_url)
                    if pair:
                        self.trading_pair_label.config(text=pair.group(1))
                    else:
                        self.trading_pair_label.config(text="无识别事件名称")
                except Exception:
                    self.trading_pair_label.config(text="解析失败")

                #  开启监控
                self.running = True
                
                # 启动监控线程
                threading.Thread(target=self.monitor_prices, daemon=True).start()
                
            except Exception as e:
                error_msg = f"加载网站失败: {str(e)}"
                self.logger.error(error_msg)
                self._show_error_and_reset(error_msg)  

        except Exception as e:
            error_msg = f"启动监控失败: {str(e)}"
            self.logger.error(error_msg)
            self._show_error_and_reset(error_msg)

    def _show_error_and_reset(self, error_msg):
        """显示错误并重置按钮状态"""
        self.update_status(error_msg)

        # 用after方法确保在线程中执行GUI操作
        self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        self.root.after(0, lambda: self.start_button.config(state='normal'))
        self.root.after(0, lambda: self.stop_button.config(state='disabled'))
        self.running = False

    def monitor_prices(self):
        """检查价格变化"""
        try:
            # 确保浏览器连接
            if not self.driver:
                chrome_options = Options()
                chrome_options.debugger_address = "127.0.0.1:9222"
                
                chrome_options.add_argument('--disable-dev-shm-usage')
                 # 添加以下选项以解决SSL错误
                
                
                self.driver = webdriver.Chrome(options=chrome_options)
                self.update_status("成功连接到浏览器")

            target_url = self.url_entry.get()
            
            # 使用JavaScript创建并点击链接来打开新标签页
            js_script = """
                const a = document.createElement('a');
                a.href = arguments[0];
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            """
            self.driver.execute_script(js_script, target_url)
            
            # 等待新标签页打开
            time.sleep(1)
            
            # 切换到新打开的标签页
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            
            self.update_status(f"已在新标签页打开: {target_url}")   
                
            # 开始监控价格
            check_counter = 0
            while not self.stop_event.is_set():  # 改用事件判断
                try:
                    if self.find_login_button():
                        time.sleep(15)
                        self.check_prices()
                        if check_counter % 10 == 0:
                            self.check_balance()
                        check_counter += 1
                        time.sleep(1)
                    else:
                        self.check_prices()
                        if check_counter % 10 == 0:
                            self.check_balance()
                        check_counter += 1
                        time.sleep(1)
                except Exception as e:
                    if not self.stop_event.is_set():  # 仅在未停止时记录错误
                        self.logger.error(f"监控失败: {str(e)}")
                    time.sleep(self.retry_interval)

        except Exception as e:
            if not self.stop_event.is_set():
                self.logger.error(f"加载页面失败: {str(e)}")
            self.stop_monitoring()
    
    def check_prices(self):
        """检查价格变化"""
        try:
            if not self.driver:
                raise Exception("monitor_prices浏览器连接丢失")
            
            try:
                # 使用锁保护浏览器操作
                with self.driver_lock:
                    # 使用JavaScript直接获取价格
                    prices = self.driver.execute_script("""
                        function getPrices() {
                            const prices = {yes: null, no: null};
                            const elements = document.getElementsByTagName('span');
                            
                            for (let el of elements) {
                                const text = el.textContent.trim();
                                if (text.includes('Yes') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.yes = parseFloat(match[1]);
                                }
                                if (text.includes('No') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.no = parseFloat(match[1]);
                                }
                            }
                            return prices;
                        }
                        return getPrices();
                    """)
                    
                    if prices['yes'] is not None and prices['no'] is not None:
                        yes_price = float(prices['yes']) / 100
                        no_price = float(prices['no']) / 100
                        
                        # 更新价格显示 - 使用 after 方法确保在主线程中更新 UI
                        self.root.after(0, lambda: self.yes_price_label.config(
                            text=f"Yes: {prices['yes']}¢ (${yes_price:.2f})",
                            foreground='red'))
                        
                        self.root.after(0, lambda: self.no_price_label.config(
                            text=f"No: {prices['no']}¢ (${no_price:.2f})",
                            foreground='red'))
                        # 使用线程执行交易检查
                        threading.Thread(target=self._check_trade_conditions, 
                                    args=(yes_price, no_price), 
                                    daemon=True).start()
                    else:
                        self.root.after(0, lambda: self.update_status("无法获取价格数据"))
            except Exception as e:
                self.logger.error(f"价格获取失败: {str(e)}")
                self.root.after(0, lambda: self.update_status(f"价格获取失败: {str(e)}"))
                self.root.after(0, lambda: self.yes_price_label.config(text="Yes: 获取失败", foreground='red'))
                self.root.after(0, lambda: self.no_price_label.config(text="No: 获取失败", foreground='red'))

        except Exception as e:
            
            time.sleep(2)

    # 添加新方法用于检查交易条件
    def _check_trade_conditions(self, yes_price, no_price):
        """在单独线程中检查交易条件"""
        try:
            # 执行所有交易检查函数
            self.First_trade(yes_price, no_price)
            self.Second_trade(yes_price, no_price)
            self.Third_trade(yes_price, no_price)
            self.Forth_trade(yes_price, no_price)
            self.Sell_yes(yes_price, no_price)
            self.Sell_no(yes_price, no_price)
        except Exception as e:
            self.logger.error(f"交易条件检查失败: {str(e)}")

    def check_balance(self):
        """获取Portfolio和Cash值"""
        try:
            if not self.driver:
                raise Exception("check_balance浏览器连接丢失")
            # 使用锁保护浏览器操作
            with self.driver_lock:
                # 等待页面完全加载
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                try:
                    # 获取Portfolio值
                    try:
                        portfolio_element = self.driver.find_element(By.XPATH, XPathConfig.PORTFOLIO_VALUE)
                        portfolio_value = portfolio_element.text
                    except Exception as e:
                        portfolio_element = self._find_element_with_retry(XPathConfig.PORTFOLIO_VALUE)
                        portfolio_value = portfolio_element.text
                    
                    # 获取Cash值
                    try:
                        cash_element = self.driver.find_element(By.XPATH, XPathConfig.CASH_VALUE)
                        cash_value = cash_element.text
                    except Exception as e:
                        cash_element = self._find_element_with_retry(XPathConfig.CASH_VALUE)
                        cash_value = cash_element.text
                    
                    # 更新Portfolio和Cash显示 - 使用 after 方法确保在主线程中更新 UI
                    self.root.after(0, lambda: self.portfolio_label.config(text=f"Portfolio: {portfolio_value}"))
                    self.root.after(0, lambda: self.cash_label.config(text=f"Cash: {cash_value}"))
                    
                    # 新增触发条件：首次获取到Cash值时安排设置金额
                    if not hasattr(self, 'cash_initialized'):
                        self.cash_initialized = True
                        self.root.after(1000, self.schedule_update_amount)  # 延迟1秒确保数据稳定
                except Exception as e:
                    self.logger.error(f"获取Portfolio和Cash失败: {str(e)}")
                    self.root.after(0, lambda: self.portfolio_label.config(text="Portfolio: 获取失败"))
                    self.root.after(0, lambda: self.cash_label.config(text="Cash: 获取失败"))

        except Exception as e:
            self.logger.error(f"检查资金失败: {str(e)}")
            self.root.after(0, lambda: self.update_status(f"资金检查错误: {str(e)}"))
            time.sleep(2)

    """以上代码执行了监控价格和获取 CASH 的值。从这里开始程序返回到第 810 行"""  

    """以下代码是设置 YES/NO 金额的函数,直到第 1270行"""
    def schedule_update_amount(self, retry_count=0):
        """设置金额,带重试机制"""
        try:
            if retry_count < 15:  # 最多重试15次
                # 1秒后执行
                self.root.after(1000, lambda: self.try_update_amount(retry_count))
            else:
                self.logger.warning("更新金额操作达到最大重试次数")

        except Exception as e:
            self.logger.error(f"安排更新金额操作失败: {str(e)}")

    def try_update_amount(self, current_retry=0):
        """尝试设置金额"""
        try:
            self.update_amount_button.invoke()
            self.root.after(1000, lambda: self.check_amount_and_set_price(current_retry))
        except Exception as e:
            self.logger.error(f"更新金额操作失败 (尝试 {current_retry + 1}/15): {str(e)}")
            # 如果失败，安排下一次重试
            self.schedule_update_amount(current_retry + 1)

    def check_amount_and_set_price(self, current_retry):
        """检查金额是否设置成功,成功后设置价格"""
        try:
            # 检查yes金额是否为非0值
            yes1_amount = self.yes1_amount_entry.get().strip()
            if yes1_amount and yes1_amount != '0.0':
                self.logger.info("金额设置成功,1秒后设置价格")
                # 延迟1秒设置价格
                self.root.after(2000, lambda: self.set_yes_no_default_target_price())
                time.sleep(1)
                
            else:
                if current_retry < 15:  # 最多重试15次
                    self.logger.info("金额未成功设置,2000ms后重试")
                    self.root.after(2000, lambda: self.check_amount_and_set_price(current_retry))
                else:
                    self.logger.warning("金额设置超时")
        except Exception as e:
            self.logger.error(f"检查金额设置状态失败: {str(e)}")

    def set_yes_no_default_target_price(self):
        """设置默认目标价格"""
        self.yes1_price_entry.delete(0, tk.END)
        self.yes1_price_entry.insert(0, self.default_target_price)
        self.no1_price_entry.delete(0, tk.END)
        self.no1_price_entry.insert(0, self.default_target_price)
    
    def get_portfolio_value(self):
        """获取Portfolio值"""
        #设置重试参数
        max_retry = 15
        retry_count = 0
        self.portfolio_value = None

        while retry_count < max_retry:
            try:
                # 获取 portfolio 值
                portfolio_text = self.portfolio_label.cget("text") 
                # 使用正则表达式提取数字
                portfolio_match = re.search(r'\$?([\d,]+\.?\d*)', portfolio_text)
                if not portfolio_match:
                    raise ValueError("无法从portfolio值中提取数字")
                # 移除逗号并转换为浮点数
                self.portfolio_value = float(portfolio_match.group(1).replace(',', ''))
                self.logger.info(f"提取到portfolio值: {self.portfolio_value}")
                return self.portfolio_value
                
            except Exception as e:
                retry_count += 1
                if retry_count < max_retry:
                    time.sleep(2)
                else:
                    raise ValueError("获取portfolio值失败")
        if self.portfolio_value is None:
            raise ValueError("获取portfolio值失败")
       
    def set_yes_no_cash(self):
        """设置 Yes/No 各级金额"""
        if not hasattr(self, 'cash_initialized'):
            self.logger.warning("Cash数据尚未就绪,延迟设置金额")
            self.root.after(1000, self.set_yes_no_cash)
            return
        try:
            #设置重试参数
            max_retry = 15
            retry_count = 0
            self.cash_value = None

            while retry_count < max_retry:
                try:
                    # 获取 Cash 值
                    cash_text = self.cash_label.cget("text") 
                    # 使用正则表达式提取数字
                    cash_match = re.search(r'\$?([\d,]+\.?\d*)', cash_text)
                    if not cash_match:
                        raise ValueError("无法从Cash值中提取数字")
                    # 移除逗号并转换为浮点数
                    self.cash_value = float(cash_match.group(1).replace(',', ''))
                    self.logger.info(f"提取到Cash值: {self.cash_value}")
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retry:
                        time.sleep(2)
                    else:
                        raise ValueError("获取Cash值失败")
            if self.cash_value is None:
                raise ValueError("获取Cash值失败")
            
            # 获取金额设置中的百分比值
            initial_percent = float(self.initial_amount_entry.get()) / 100  # 初始金额百分比
            first_rebound_percent = float(self.first_rebound_entry.get()) / 100  # 反水一次百分比
            n_rebound_percent = float(self.n_rebound_entry.get()) / 100  # 反水N次百分比

            # 设置 Yes1 和 No1金额
            base_amount = self.cash_value * initial_percent
            self.yes1_entry = self.yes_frame.grid_slaves(row=1, column=1)[0]
            self.yes1_amount_entry.delete(0, tk.END)
            self.yes1_amount_entry.insert(0, f"{base_amount:.2f}")
            self.no1_entry = self.no_frame.grid_slaves(row=1, column=1)[0]
            self.no1_amount_entry.delete(0, tk.END)
            self.no1_amount_entry.insert(0, f"{base_amount:.2f}")
            
            # 计算并设置 Yes2/No2金额
            self.yes2_amount = base_amount * first_rebound_percent
            self.yes2_entry = self.yes_frame.grid_slaves(row=3, column=1)[0]
            self.yes2_entry.delete(0, tk.END)
            self.yes2_entry.insert(0, f"{self.yes2_amount:.2f}")
            self.no2_entry = self.no_frame.grid_slaves(row=3, column=1)[0]
            self.no2_entry.delete(0, tk.END)
            self.no2_entry.insert(0, f"{self.yes2_amount:.2f}")
            
            # 计算并设置 YES3/NO3 金额
            self.yes3_amount = self.yes2_amount * n_rebound_percent
            self.yes3_entry = self.yes_frame.grid_slaves(row=5, column=1)[0]
            self.yes3_entry.delete(0, tk.END)
            self.yes3_entry.insert(0, f"{self.yes3_amount:.2f}")
            self.no3_entry = self.no_frame.grid_slaves(row=5, column=1)[0]
            self.no3_entry.delete(0, tk.END)
            self.no3_entry.insert(0, f"{self.yes3_amount:.2f}")

            # 计算并设置 Yes4/No4金额
            self.yes4_amount = self.yes3_amount * n_rebound_percent
            self.yes4_entry = self.yes_frame.grid_slaves(row=7, column=1)[0]
            self.yes4_entry.delete(0, tk.END)
            self.yes4_entry.insert(0, f"{self.yes4_amount:.2f}")
            self.no4_entry = self.no_frame.grid_slaves(row=7, column=1)[0]
            self.no4_entry.delete(0, tk.END)
            self.no4_entry.insert(0, f"{self.yes4_amount:.2f}")
        
            self.logger.info("金额设置完成")
            self.update_status("金额设置成功")
            
        except Exception as e:
            self.logger.error(f"设置金额失败: {str(e)}")
            self.update_status("金额设置失败,请检查Cash值是否正确")
            # 如果失败，安排重试
            self.schedule_retry_update()

    def schedule_retry_update(self):
        """安排重试更新金额"""
        if hasattr(self, 'retry_timer'):
            self.root.after_cancel(self.retry_timer)
        self.retry_timer = self.root.after(3000, self.set_yes_no_cash)

    """以上代码执行了设置 YES/NO 金额的函数,从 1020 行到 1270 行,程序执行返回到 815 行"""

    """以下代码是启动 URL 监控和登录状态监控的函数,直到第 1578 行"""
    def start_url_monitoring(self):
        """启动URL监控"""
        with self.url_monitoring_lock:
            if getattr(self, 'is_url_monitoring', False):
                self.logger.debug("URL监控已在运行中")
                return

            self.is_url_monitoring = True
            self.logger.info("✅ 启动URL监控")

            def _monitor():
                try:
                    if not getattr(self, 'is_url_monitoring', False):
                        return

                    # 使用线程执行可能耗时的浏览器操作，避免阻塞GUI
                    def check_and_restore_url():
                        try:
                            current_url = self.driver.current_url if self.driver else ""
                            target_url = self.target_url
                            
                            if current_url != target_url:
                                self.logger.warning(f"URL变更: {current_url} -> 恢复至 {target_url}")
                                # 使用线程执行耗时操作
                                with self.driver_lock:
                                    self.driver.get(target_url)
                        except Exception as e:
                            self.logger.error(f"URL恢复操作异常: {str(e)}")

                    # 使用线程执行URL检查和恢复
                    threading.Thread(target=check_and_restore_url, daemon=True).start()

                except Exception as e:
                    self.logger.error(f"监控异常: {str(e)}")
                finally:
                    if getattr(self, 'is_url_monitoring', False):
                        self.url_check_timer = self.root.after(3000, _monitor)
                    else:
                        self.url_check_timer = None

            self.url_check_timer = self.root.after(0, _monitor)

    def stop_url_monitoring(self):
        """停止URL监控"""
        with self.url_monitoring_lock:
            try:
                # 添加状态标志检查
                if not hasattr(self, 'is_url_monitoring') or not self.is_url_monitoring:
                    return
                
                if self.url_check_timer:
                    # 强制取消所有待处理定时器
                    while self.url_check_timer:
                        try:
                            self.root.after_cancel(self.url_check_timer)
                            break
                        except ValueError as e:
                            if "invalid timer id" in str(e).lower():
                                self.logger.warning("遇到无效定时器ID,可能已被触发")
                                break
                        except Exception as e:
                            self.logger.error(f"取消定时器异常: {str(e)}")
                            break
                    self.url_check_timer = None
                
                # 更新状态标志
                self.is_url_monitoring = False
                self.logger.info("❌ URL监控已完全停止")
                
            except Exception as e:
                self.logger.error(f"停止监控时发生未知错误: {str(e)}")
            finally:
                self.url_check_timer = None
                if hasattr(self, 'is_url_monitoring'):
                    self.is_url_monitoring = False

    def find_login_button(self):
        """查找登录按钮"""
        # 使用静默模式查找元素，并添加空值检查
        try:
            login_button = self.driver.find_element(By.XPATH, XPathConfig.LOGIN_BUTTON)
        except Exception as e:
            login_button = self._find_element_with_retry(
                XPathConfig.LOGIN_BUTTON,
                timeout=3,
                silent=True
            )
        
        # 添加空值检查和安全访问
        if login_button is not None and "Log In" in login_button.text:
            self.logger.warning("检查到未登录,自动登录...")
            return True
        else:
            # 正常状态无需记录日志
            pass

    def start_login_monitoring(self):
        self.logger.info("启动登录状态监控")
        def check_login():
            try:
                if self.find_login_button():
                    self.check_and_handle_login()
            except Exception as e:
                # 仅记录非预期异常
                self.logger.debug(f"登录检查遇到非预期异常: {str(e)}")
            
            # 保持定时检查
            if self.running:
                self.root.after(5000, check_login)

        # 首次启动检查
        self.root.after(1000, check_login)

    def check_and_handle_login(self):
        """执行登录操作"""
        try:
            # 记录auto_find_54_coin线程状态
            auto_find_was_running = False

            # 检查是否需要停止自动找币线程
            if hasattr(self, 'auto_find_thread') and self.auto_find_thread is not None and self.auto_find_thread.is_alive():
                self.logger.info("检测到登录,停止自动找币线程")
                self.stop_auto_find_54_coin()  # 调用停止函数确保完全停止
                
                # 增加更强的线程停止机制
                start_time = time.time()
                max_wait_time = 10  # 最多等待10秒
                
                while self.auto_find_thread.is_alive() and time.time() - start_time < max_wait_time:
                    self.logger.info("等待auto_find_54_coin线程停止...")
                    time.sleep(1)
                
                if self.auto_find_thread.is_alive():
                    self.logger.warning(f"auto_find_54_coin线程在{max_wait_time}秒内未能停止，继续执行登录")
                else:
                    self.logger.info("auto_find_54_coin线程已成功停止")

            self.logger.info("开始执行登录操作...")
            self.stop_url_monitoring()
            self.stop_refresh_page()
            time.sleep(1)

            # 点击登录按钮
            try:
                login_button = self.driver.find_element(By.XPATH, XPathConfig.LOGIN_BUTTON)
                login_button.click()
            except Exception as e:
                login_button = self._find_element_with_retry(
                    XPathConfig.LOGIN_BUTTON,
                    timeout=3,
                    silent=True
                )
                login_button.click()
            time.sleep(1)
            
            # 使用 XPath 定位并点击 MetaMask 按钮
            metamask_button = self._find_element_with_retry(XPathConfig.METAMASK_BUTTON)
            metamask_button.click()
            time.sleep(2)

            # 截取屏幕
            screen = pyautogui.screenshot()
            
            # 使用OCR识别文本
            
            text = pytesseract.image_to_string(screen, lang='chi_sim')
            
            # 检查是否包含"欢迎回来!"
            if "欢迎回来" in text:
                self.logger.info("检测到MetaMask登录窗口,显示'欢迎回来!'")
                # 输入密码
                pyautogui.write("noneboy780308")
                time.sleep(0.5)
                # 按下Enter键
                pyautogui.press('enter')
                time.sleep(1)
                 # 1. 按5次TAB
                for _ in range(5):
                    pyautogui.press('tab')
                # 按下Enter键
                pyautogui.press('enter')
                self.logger.info("MetaMask登录成功")

                # 恢复URL监控和页面刷新和自动找币
                self.root.after(10000, self.start_url_monitoring)
                self.root.after(30000, self.refresh_page)
                self.root.after(60000, self.auto_find_54_coin)
                return
            
            # 处理 MetaMask 弹窗
            # 模拟键盘操作序列
            # 1. 按5次TAB
            for _ in range(5):
                pyautogui.press('tab')
            # 2. 按1次ENTER
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(2)  # 等待2秒
            
            # 3. 按7次TAB
            for _ in range(7):
                pyautogui.press('tab')
            
            # 4. 按1次ENTER
            pyautogui.press('enter')
            
            # 等待弹窗自动关闭
            time.sleep(1)

            if self.driver:       
                # 直接执行click_accept_button
                self.logger.info("登录完成,执行click_accept_button")
                time.sleep(1)                                        

                self.driver.refresh()
                time.sleep(1)
                self.click_accept_button()
                
                # 恢复URL监控和页面刷新和自动找币
                self.root.after(10000, self.start_url_monitoring)
                self.root.after(240000, self.refresh_page)
                self.root.after(120000, self.auto_find_54_coin)
                return 
            else:
                self.logger.error("执行click_accept_button失败")
                return False
            
        except Exception as e:
            self.logger.error(f"登录操作失败: {str(e)}")
            return False

    def click_accept_button(self):
        """重新登录后,需要在amount输入框输入1并确认"""
        self.logger.info("开始执行click_accept_button")
        try:
            # 等待输入框可交互
            try:
                amount_input = self.driver.find_element(By.XPATH, XPathConfig.AMOUNT_INPUT)
            except Exception as e:
                amount_input = self._find_element_with_retry(
                    XPathConfig.AMOUNT_INPUT,
                    timeout=3,
                    silent=True
                )
            self.logger.info("找到amount_input")
            # 清空输入框
            amount_input.clear()
            # 输入新值
            amount_input.send_keys("1")
            time.sleep(0.5)
            
            # 点击确认按钮
            self.buy_confirm_button.invoke()
            time.sleep(0.5)
            
            # 按ENTER确认
            pyautogui.press('enter')
            time.sleep(1)
            
            # 刷新页面
            self.driver.refresh()
            self.logger.info("click_accept_button执行完成")
            
        except Exception as e:
            self.logger.error(f"click_accept_button执行失败: {str(e)}")
            self.click_accept_button()

    # 添加刷新方法
    def refresh_page(self):
        """定时刷新页面"""
        try:
            if not self.running:
                self.logger.info("监控已停止，取消页面刷新")
                return
                
            # 检查是否正在交易
            if hasattr(self, 'is_trading') and self.is_trading:
                self.logger.info("交易进行中，跳过本次刷新")
                # 安排下一次刷新
                self.refresh_timer = self.root.after(300000, self.refresh_page)  # 5分钟 = 300000毫秒
                return
            
            # 检查是否正在执行其他重要操作
            if hasattr(self, 'is_checking_prices') and self.is_checking_prices:
                self.logger.info("正在检查价格，延迟页面刷新")
                # 延迟30秒后再次尝试
                self.refresh_timer = self.root.after(30000, self.refresh_page)
                return
            
            # 使用线程执行刷新操作，避免阻塞主线程
            def do_refresh():
                try:
                    start_time = time.time()
                    # 使用锁保护浏览器操作
                    with self.driver_lock:
                        # 设置页面加载超时
                        self.driver.set_page_load_timeout(20)  # 减少超时时间
                        try:
                            # 使用更轻量级的方式刷新页面
                            self.driver.execute_script("location.reload(true);")
                            self.logger.info("✅ 刷新页面成功")
                        except Exception as js_e:
                            self.logger.error(f"JavaScript刷新失败: {str(js_e)}")
                            try:
                                # 如果JavaScript刷新失败，尝试使用更简单的方法
                                self.driver.get(self.driver.current_url)
                                self.logger.info("✅ 使用get方法刷新页面成功")
                            except Exception as e:
                                self.logger.error(f"页面刷新失败: {str(e)}")
                    
                    elapsed = time.time() - start_time
                    
                except Exception as e:
                    self.logger.error(f"刷新页面线程中出错: {str(e)}")
            
            # 启动刷新线程
            refresh_thread = threading.Thread(target=do_refresh, daemon=True, name="RefreshThread")
            refresh_thread.start()
            
            # 安排下一次刷新，增加间隔时间减少卡顿
            self.refresh_timer = self.root.after(600000, self.refresh_page)  # 10分钟 = 600000毫秒
        except Exception as e:
            self.logger.error(f"刷新页面调度失败: {str(e)}")
            # 即使失败也要安排下一次刷新
            self.refresh_timer = self.root.after(600000, self.refresh_page)
        
    def stop_refresh_page(self):
        """停止页面刷新"""
        try:
            # 检查定时器是否存在
            if not hasattr(self, 'refresh_timer') or self.refresh_timer is None:
                return
            # 记录当前定时器ID
            timer_id = self.refresh_timer
            
            # 尝试取消定时器
            try:
                self.root.after_cancel(self.refresh_timer)
                self.logger.info("❌ 成功停止页面刷新定时器")
            except ValueError as e:
                if "invalid timer id" in str(e).lower():
                    self.logger.warning("遇到无效定时器ID,可能已被触发或取消")
                else:
                    raise
            except Exception as e:
                self.logger.error(f"取消页面刷新定时器时发生错误: {str(e)}")
                
            # 重置定时器变量
            self.refresh_timer = None
            
        except Exception as e:
            self.logger.error(f"停止页面刷新时发生未知错误: {str(e)}")
            # 确保定时器变量被重置，即使发生错误
            if hasattr(self, 'refresh_timer'):
                self.refresh_timer = None
    """以上代码执行了登录操作的函数,直到第 1578 行,程序执行返回到 848 行"""               
    """以下代码是监控买卖条件及执行交易的函数,程序开始进入交易阶段,从 1400 行直到第 2500 行"""  
    # 修改 First_trade 方法，接收价格参数而不是重新获取
    def First_trade(self, yes_price=None, no_price=None):
        try:
            self.trading = True  # 开始交易
            
            # 如果没有传入价格参数，则获取当前价格
            if yes_price is None or no_price is None:
                with self.driver_lock:
                    prices = self.driver.execute_script("""
                        function getPrices() {
                            const prices = {yes: null, no: null};
                            const elements = document.getElementsByTagName('span');
                            
                            for (let el of elements) {
                                const text = el.textContent.trim();
                                if (text.includes('Yes') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.yes = parseFloat(match[1]);
                                }
                                if (text.includes('No') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.no = parseFloat(match[1]);
                                }
                            }
                            return prices;
                        }
                        return getPrices();
                    """)
                    
                    if prices['yes'] is not None and prices['no'] is not None:
                        yes_price = float(prices['yes']) / 100
                        no_price = float(prices['no']) / 100
                    else:
                        return
            
            # 获取Yes1和No1的目标价格
            yes1_target = float(self.yes1_price_entry.get())
            no1_target = float(self.no1_price_entry.get())
            
            # 检查Yes1价格匹配
            if 0 <= (yes_price - yes1_target) <= 0.02 and yes1_target > 0:
                self.logger.info("Yes 1价格匹配,执行自动交易")
                # 创建新线程执行交易操作
                threading.Thread(target=self._execute_yes1_trade, daemon=True).start()
                    
            # 检查No1价格匹配
            elif 0 <= (no_price - no1_target) <= 0.02 and no1_target > 0:
                self.logger.info("No 1价格匹配,执行自动交易")
                # 创建新线程执行交易操作
                threading.Thread(target=self._execute_no1_trade, daemon=True).start()

        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"First_trade执行失败: {str(e)}")
            self.root.after(0, lambda: self.update_status(f"First_trade执行失败: {str(e)}"))
        finally:
            self.trading = False

    # 添加执行Yes1交易的方法
    def _execute_yes1_trade(self):
        try:
            max_attempts = 3
            for attempt in range(max_attempts):
                with self.driver_lock:
                    # 执行现有的交易操作
                    self.amount_yes1_button.event_generate('<Button-1>')
                    time.sleep(0.5)
                    self.buy_confirm_button.invoke()
                    time.sleep(0.5)
                    self._handle_metamask_popup()
                    
                # 执行等待和刷新
                self.sleep_refresh("First_trade")
                
                if self.Verify_buy_yes():
                    # 增加交易次数
                    self.trade_count += 1
                    # 发送交易邮件
                    self.send_trade_email(
                        trade_type="Buy Yes1",
                        price=float(self.yes1_price_entry.get()),
                        amount=float(self.yes1_amount_entry.get()),
                        trade_count=self.trade_count
                    )
                    
                    # 在主线程中更新UI
                    self.root.after(0, self._update_after_yes1_trade)
                    self.logger.info("First_trade执行成功")
                    break
                else:
                    self.logger.warning(f"交易失败,尝试 {attempt+1}/{max_attempts}")
                    time.sleep(2)  # 添加延时避免过于频繁的重试
        except Exception as e:
            self.logger.error(f"执行Yes1交易失败: {str(e)}")

    # 添加Yes1交易后的UI更新方法
    def _update_after_yes1_trade(self):
        # 重置Yes1和No1价格为0.00
        self.yes1_price_entry.delete(0, tk.END)
        self.yes1_price_entry.insert(0, "0.00")
        self.no1_price_entry.delete(0, tk.END)
        self.no1_price_entry.insert(0, "0.00")
            
        # 设置No2价格为默认值
        self.no2_price_entry = self.no_frame.grid_slaves(row=2, column=1)[0]
        self.no2_price_entry.delete(0, tk.END)
        self.no2_price_entry.insert(0, str(self.default_target_price))
        self.no2_price_entry.configure(foreground='red')  # 添加红色设置

        # 设置 Yes5和No5价格为0.85
        self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
        self.yes5_price_entry.delete(0, tk.END)
        self.yes5_price_entry.insert(0, "0.85")
        self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
        self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
        self.no5_price_entry.delete(0, tk.END)
        self.no5_price_entry.insert(0, "0.85")
        self.no5_price_entry.configure(foreground='red')  # 添加红色设置

        # 添加执行No1交易的方法
    def _execute_no1_trade(self):
        try:
            max_attempts = 3
            for attempt in range(max_attempts):
                with self.driver_lock:
                    # 执行现有的交易操作
                    self.buy_no_button.invoke()
                    time.sleep(0.5)
                    self.amount_no1_button.event_generate('<Button-1>')
                    time.sleep(0.5)
                    self.buy_confirm_button.invoke()
                    time.sleep(0.5)
                    self._handle_metamask_popup()
                    
                # 执行等待和刷新
                self.sleep_refresh("First_trade")
                
                if self.Verify_buy_no():
                    # 增加交易次数
                    self.trade_count += 1
                    # 发送交易邮件
                    self.send_trade_email(
                        trade_type="Buy No1",
                        price=float(self.no1_price_entry.get()),
                        amount=float(self.no1_amount_entry.get()),
                        trade_count=self.trade_count
                    )
                    
                    # 在主线程中更新UI
                    self.root.after(0, self._update_after_no1_trade)
                    self.logger.info("First_trade执行成功")
                    break
                else:
                    self.logger.warning(f"交易失败,尝试 {attempt+1}/{max_attempts}")
                    time.sleep(2)  # 添加延时避免过于频繁的重试
        except Exception as e:
            self.logger.error(f"执行No1交易失败: {str(e)}")

    # 添加No1交易后的UI更新方法
    def _update_after_no1_trade(self):
        # 重置Yes1和No1价格为0.00
        self.yes1_price_entry.delete(0, tk.END)
        self.yes1_price_entry.insert(0, "0.00")
        self.no1_price_entry.delete(0, tk.END)
        self.no1_price_entry.insert(0, "0.00")
            
        # 设置Yes2价格为默认值
        self.yes2_price_entry = self.yes_frame.grid_slaves(row=2, column=1)[0]
        self.yes2_price_entry.delete(0, tk.END)
        self.yes2_price_entry.insert(0, str(self.default_target_price))
        self.yes2_price_entry.configure(foreground='red')  # 添加红色设置

        # 设置 Yes5和No5价格为0.85
        self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
        self.yes5_price_entry.delete(0, tk.END)
        self.yes5_price_entry.insert(0, "0.85")
        self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
        self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
        self.no5_price_entry.delete(0, tk.END)
        self.no5_price_entry.insert(0, "0.85")
        self.no5_price_entry.configure(foreground='red')  # 添加红色设置

    # 修改 Second_trade 方法，接收价格参数而不是重新获取
    def Second_trade(self, yes_price=None, no_price=None):
        try:
            self.trading = True  # 开始交易
            
            # 如果没有传入价格参数，则获取当前价格
            if yes_price is None or no_price is None:
                with self.driver_lock:
                    prices = self.driver.execute_script("""
                        function getPrices() {
                            const prices = {yes: null, no: null};
                            const elements = document.getElementsByTagName('span');
                            
                            for (let el of elements) {
                                const text = el.textContent.trim();
                                if (text.includes('Yes') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.yes = parseFloat(match[1]);
                                }
                                if (text.includes('No') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.no = parseFloat(match[1]);
                                }
                            }
                            return prices;
                        }
                        return getPrices();
                    """)
                    
                    if prices['yes'] is not None and prices['no'] is not None:
                        yes_price = float(prices['yes']) / 100
                        no_price = float(prices['no']) / 100
                    else:
                        return
            
            # 获取Yes2和No2的目标价格
            yes2_target = float(self.yes2_price_entry.get())
            no2_target = float(self.no2_price_entry.get())
            
            # 检查Yes2价格匹配
            if 0 <= (yes_price - yes2_target) <= 0.02 and yes2_target > 0:
                self.logger.info("Yes 2价格匹配,执行自动交易")
                # 创建新线程执行交易操作
                threading.Thread(target=self._execute_yes2_trade, daemon=True).start()
                    
            # 检查No2价格匹配
            elif 0 <= (no_price - no2_target) <= 0.02 and no2_target > 0:
                self.logger.info("No 2价格匹配,执行自动交易")
                # 创建新线程执行交易操作
                threading.Thread(target=self._execute_no2_trade, daemon=True).start()

        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Second_trade执行失败: {str(e)}")
            self.root.after(0, lambda: self.update_status(f"Second_trade执行失败: {str(e)}"))
        finally:
            self.trading = False

    # 添加执行Yes2交易的方法
    def _execute_yes2_trade(self):
        try:
            max_attempts = 3
            for attempt in range(max_attempts):
                with self.driver_lock:
                    # 执行现有的交易操作
                    self.amount_yes2_button.event_generate('<Button-1>')
                    time.sleep(0.5)
                    self.buy_confirm_button.invoke()
                    time.sleep(0.5)
                    self._handle_metamask_popup()
                    
                # 执行等待和刷新
                self.sleep_refresh("Second_trade")
                
                if self.Verify_buy_yes():
                    # 增加交易次数
                    self.trade_count += 1
                    # 发送交易邮件
                    self.send_trade_email(
                        trade_type="Buy Yes2",
                        price=float(self.yes2_price_entry.get()),
                        amount=float(self.yes2_amount_entry.get()),
                        trade_count=self.trade_count
                    )
                    
                    # 在主线程中更新UI
                    self.root.after(0, self._update_after_yes2_trade)
                    self.logger.info("Second_trade执行成功")
                    break
                else:
                    self.logger.warning(f"交易失败,尝试 {attempt+1}/{max_attempts}")
                    time.sleep(2)  # 添加延时避免过于频繁的重试
        except Exception as e:
            self.logger.error(f"执行Yes2交易失败: {str(e)}")

    # 添加Yes2交易后的UI更新方法
    def _update_after_yes2_trade(self):
        # 重置Yes2和No2价格为0.00
        self.yes2_price_entry.delete(0, tk.END)
        self.yes2_price_entry.insert(0, "0.00")
        self.no2_price_entry.delete(0, tk.END)
        self.no2_price_entry.insert(0, "0.00")
            
        # 设置No3价格为默认值
        self.no3_price_entry = self.no_frame.grid_slaves(row=2, column=1)[0]
        self.no3_price_entry.delete(0, tk.END)
        self.no3_price_entry.insert(0, str(self.default_target_price))
        self.no3_price_entry.configure(foreground='red')  # 添加红色设置

        # 添加执行No2交易的方法
    def _execute_no2_trade(self):
        try:
            max_attempts = 3
            for attempt in range(max_attempts):
                with self.driver_lock:
                    # 执行现有的交易操作
                    self.buy_no_button.invoke()
                    time.sleep(0.5)
                    self.amount_no2_button.event_generate('<Button-1>')
                    time.sleep(0.5)
                    self.buy_confirm_button.invoke()
                    time.sleep(0.5)
                    self._handle_metamask_popup()
                    
                # 执行等待和刷新
                self.sleep_refresh("Second_trade")
                
                if self.Verify_buy_no():
                    # 增加交易次数
                    self.trade_count += 1
                    # 发送交易邮件
                    self.send_trade_email(
                        trade_type="Buy No2",
                        price=float(self.no2_price_entry.get()),
                        amount=float(self.no2_amount_entry.get()),
                        trade_count=self.trade_count
                    )
                    
                    # 在主线程中更新UI
                    self.root.after(0, self._update_after_no2_trade)
                    self.logger.info("Second_trade执行成功")
                    break
                else:
                    self.logger.warning(f"交易失败,尝试 {attempt+1}/{max_attempts}")
                    time.sleep(2)  # 添加延时避免过于频繁的重试
        except Exception as e:
            self.logger.error(f"执行No2交易失败: {str(e)}")

    # 添加No2交易后的UI更新方法
    def _update_after_no2_trade(self):
        # 重置Yes2和No2价格为0.00
        self.yes2_price_entry.delete(0, tk.END)
        self.yes2_price_entry.insert(0, "0.00")
        self.no2_price_entry.delete(0, tk.END)
        self.no2_price_entry.insert(0, "0.00")
            
        # 设置Yes3价格为默认值
        self.yes3_price_entry = self.yes_frame.grid_slaves(row=2, column=1)[0]
        self.yes3_price_entry.delete(0, tk.END)
        self.yes3_price_entry.insert(0, str(self.default_target_price))
        self.yes3_price_entry.configure(foreground='red')  # 添加红色设置


    # 修改 Third_trade 方法，接收价格参数而不是重新获取
    def Third_trade(self, yes_price=None, no_price=None):
        try:
            self.trading = True  # 开始交易
            
            # 如果没有传入价格参数，则获取当前价格
            if yes_price is None or no_price is None:
                with self.driver_lock:
                    prices = self.driver.execute_script("""
                        function getPrices() {
                            const prices = {yes: null, no: null};
                            const elements = document.getElementsByTagName('span');
                            
                            for (let el of elements) {
                                const text = el.textContent.trim();
                                if (text.includes('Yes') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.yes = parseFloat(match[1]);
                                }
                                if (text.includes('No') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.no = parseFloat(match[1]);
                                }
                            }
                            return prices;
                        }
                        return getPrices();
                    """)
                    
                    if prices['yes'] is not None and prices['no'] is not None:
                        yes_price = float(prices['yes']) / 100
                        no_price = float(prices['no']) / 100
                    else:
                        return
            
            # 获取Yes3和No3的目标价格
            yes3_target = float(self.yes3_price_entry.get())
            no3_target = float(self.no3_price_entry.get())
            
            # 检查Yes3价格匹配
            if 0 <= (yes_price - yes3_target) <= 0.02 and yes3_target > 0:
                self.logger.info("Yes 3价格匹配,执行自动交易")
                # 创建新线程执行交易操作
                threading.Thread(target=self._execute_yes3_trade, daemon=True).start()
                    
            # 检查No3价格匹配
            elif 0 <= (no_price - no3_target) <= 0.02 and no3_target > 0:
                self.logger.info("No 3价格匹配,执行自动交易")
                # 创建新线程执行交易操作
                threading.Thread(target=self._execute_no3_trade, daemon=True).start()

        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Third_trade执行失败: {str(e)}")
            self.root.after(0, lambda: self.update_status(f"Third_trade执行失败: {str(e)}"))
        finally:
            self.trading = False

    # 添加执行Yes3交易的方法
    def _execute_yes3_trade(self):
        try:
            max_attempts = 3
            for attempt in range(max_attempts):
                with self.driver_lock:
                    # 执行现有的交易操作
                    self.amount_yes3_button.event_generate('<Button-1>')
                    time.sleep(0.5)
                    self.buy_confirm_button.invoke()
                    time.sleep(0.5)
                    self._handle_metamask_popup()
                    
                # 执行等待和刷新
                self.sleep_refresh("Third_trade")
                
                if self.Verify_buy_yes():
                    # 增加交易次数
                    self.trade_count += 1
                    # 发送交易邮件
                    self.send_trade_email(
                        trade_type="Buy Yes3",
                        price=float(self.yes3_price_entry.get()),
                        amount=float(self.yes3_amount_entry.get()),
                        trade_count=self.trade_count
                    )
                    
                    # 在主线程中更新UI
                    self.root.after(0, self._update_after_yes3_trade)
                    self.logger.info("Third_trade执行成功")
                    break
                else:
                    self.logger.warning(f"交易失败,尝试 {attempt+1}/{max_attempts}")
                    time.sleep(2)  # 添加延时避免过于频繁的重试
        except Exception as e:
            self.logger.error(f"执行Yes2交易失败: {str(e)}")

    # 添加Yes3交易后的UI更新方法
    def _update_after_yes3_trade(self):
        # 重置Yes3和No3价格为0.00
        self.yes3_price_entry.delete(0, tk.END)
        self.yes3_price_entry.insert(0, "0.00")
        self.no3_price_entry.delete(0, tk.END)
        self.no3_price_entry.insert(0, "0.00")
            
        # 设置No4价格为默认值
        self.no4_price_entry = self.no_frame.grid_slaves(row=2, column=1)[0]
        self.no4_price_entry.delete(0, tk.END)
        self.no4_price_entry.insert(0, str(self.default_target_price))
        self.no4_price_entry.configure(foreground='red')  # 添加红色设置

        # 添加执行No3交易的方法
    def _execute_no3_trade(self):
        try:
            max_attempts = 3
            for attempt in range(max_attempts):
                with self.driver_lock:
                    # 执行现有的交易操作
                    self.buy_no_button.invoke()
                    time.sleep(0.5)
                    self.amount_no3_button.event_generate('<Button-1>')
                    time.sleep(0.5)
                    self.buy_confirm_button.invoke()
                    time.sleep(0.5)
                    self._handle_metamask_popup()
                    
                # 执行等待和刷新
                self.sleep_refresh("Third_trade")
                
                if self.Verify_buy_no():
                    # 增加交易次数
                    self.trade_count += 1
                    # 发送交易邮件
                    self.send_trade_email(
                        trade_type="Buy No3",
                        price=float(self.no3_price_entry.get()),
                        amount=float(self.no3_amount_entry.get()),
                        trade_count=self.trade_count
                    )
                    
                    # 在主线程中更新UI
                    self.root.after(0, self._update_after_no3_trade)
                    self.logger.info("Third_trade执行成功")
                    break
                else:
                    self.logger.warning(f"交易失败,尝试 {attempt+1}/{max_attempts}")
                    time.sleep(2)  # 添加延时避免过于频繁的重试
        except Exception as e:
            self.logger.error(f"执行No3交易失败: {str(e)}")

    # 添加No3交易后的UI更新方法
    def _update_after_no3_trade(self):
        # 重置Yes3和No3价格为0.00
        self.yes3_price_entry.delete(0, tk.END)
        self.yes3_price_entry.insert(0, "0.00")
        self.no3_price_entry.delete(0, tk.END)
        self.no2_price_entry.insert(0, "0.00")
            
        # 设置Yes4价格为默认值
        self.yes4_price_entry = self.yes_frame.grid_slaves(row=2, column=1)[0]
        self.yes4_price_entry.delete(0, tk.END)
        self.yes4_price_entry.insert(0, str(self.default_target_price))
        self.yes4_price_entry.configure(foreground='red')  # 添加红色设置


    # 修改 Forth_trade 方法，接收价格参数而不是重新获取
    def Forth_trade(self, yes_price=None, no_price=None):
        try:
            self.trading = True  # 开始交易
            
            # 如果没有传入价格参数，则获取当前价格
            if yes_price is None or no_price is None:
                with self.driver_lock:
                    prices = self.driver.execute_script("""
                        function getPrices() {
                            const prices = {yes: null, no: null};
                            const elements = document.getElementsByTagName('span');
                            
                            for (let el of elements) {
                                const text = el.textContent.trim();
                                if (text.includes('Yes') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.yes = parseFloat(match[1]);
                                }
                                if (text.includes('No') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.no = parseFloat(match[1]);
                                }
                            }
                            return prices;
                        }
                        return getPrices();
                    """)
                    
                    if prices['yes'] is not None and prices['no'] is not None:
                        yes_price = float(prices['yes']) / 100
                        no_price = float(prices['no']) / 100
                    else:
                        return
            
            # 获取Yes4和No4的目标价格
            yes4_target = float(self.yes4_price_entry.get())
            no4_target = float(self.no4_price_entry.get())
            
            # 检查Yes4价格匹配
            if 0 <= (yes_price - yes4_target) <= 0.02 and yes4_target > 0:
                self.logger.info("Yes 4价格匹配,执行自动交易")
                # 创建新线程执行交易操作
                threading.Thread(target=self._execute_yes4_trade, daemon=True).start()
                    
            # 检查No4价格匹配
            elif 0 <= (no_price - no4_target) <= 0.02 and no4_target > 0:
                self.logger.info("No 4价格匹配,执行自动交易")
                # 创建新线程执行交易操作
                threading.Thread(target=self._execute_no4_trade, daemon=True).start()

        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Forth_trade执行失败: {str(e)}")
            self.root.after(0, lambda: self.update_status(f"Forth_trade执行失败: {str(e)}"))
        finally:
            self.trading = False

    # 添加执行Yes4交易的方法
    def _execute_yes4_trade(self):
        try:
            max_attempts = 3
            for attempt in range(max_attempts):
                with self.driver_lock:
                    # 执行现有的交易操作
                    self.amount_yes4_button.event_generate('<Button-1>')
                    time.sleep(0.5)
                    self.buy_confirm_button.invoke()
                    time.sleep(0.5)
                    self._handle_metamask_popup()
                    
                # 执行等待和刷新
                self.sleep_refresh("Forth_trade")
                
                if self.Verify_buy_yes():
                    # 增加交易次数
                    self.trade_count += 1
                    # 发送交易邮件
                    self.send_trade_email(
                        trade_type="Buy Yes4",
                        price=float(self.yes4_price_entry.get()),
                        amount=float(self.yes4_amount_entry.get()),
                        trade_count=self.trade_count
                    )
                    
                    # 在主线程中更新UI
                    self.root.after(0, self._update_after_yes4_trade)
                    self.logger.info("Forth_trade执行成功")
                    break
                else:
                    self.logger.warning(f"交易失败,尝试 {attempt+1}/{max_attempts}")
                    time.sleep(2)  # 添加延时避免过于频繁的重试
        except Exception as e:
            self.logger.error(f"执行Yes4交易失败: {str(e)}")

    # 添加Yes4交易后的UI更新方法
    def _update_after_yes4_trade(self):
        # 重置Yes4和No4价格为0.00
        self.yes4_price_entry.delete(0, tk.END)
        self.yes4_price_entry.insert(0, "0.00")
        self.no4_price_entry.delete(0, tk.END)
        self.no4_price_entry.insert(0, "0.00")
            
        """当买了 4次后预防第 5 次反水，所以价格到了 50 时就平仓，然后再自动开"""
        # 设置 Yes5和No5价格为0.85
        self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
        self.yes5_price_entry.delete(0, tk.END)
        self.yes5_price_entry.insert(0, "0.85")
        self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
        self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
        self.no5_price_entry.delete(0, tk.END)
        self.no5_price_entry.insert(0, "0.5")
        self.no5_price_entry.configure(foreground='red')  # 添加红色设置

        # 添加执行No4交易的方法
    def _execute_no4_trade(self):
        try:
            max_attempts = 3
            for attempt in range(max_attempts):
                with self.driver_lock:
                    # 执行现有的交易操作
                    self.buy_no_button.invoke()
                    time.sleep(0.5)
                    self.amount_no4_button.event_generate('<Button-1>')
                    time.sleep(0.5)
                    self.buy_confirm_button.invoke()
                    time.sleep(0.5)
                    self._handle_metamask_popup()
                    
                # 执行等待和刷新
                self.sleep_refresh("Forth_trade")
                
                if self.Verify_buy_no():
                    # 增加交易次数
                    self.trade_count += 1
                    # 发送交易邮件
                    self.send_trade_email(
                        trade_type="Buy No4",
                        price=float(self.no4_price_entry.get()),
                        amount=float(self.no4_amount_entry.get()),
                        trade_count=self.trade_count
                    )
                    
                    # 在主线程中更新UI
                    self.root.after(0, self._update_after_no4_trade)
                    self.logger.info("Forth_trade执行成功")
                    break
                else:
                    self.logger.warning(f"交易失败,尝试 {attempt+1}/{max_attempts}")
                    time.sleep(2)  # 添加延时避免过于频繁的重试
        except Exception as e:
            self.logger.error(f"执行No4交易失败: {str(e)}")

    # 添加No4交易后的UI更新方法
    def _update_after_no4_trade(self):
        # 重置Yes4和No4价格为0.00
        self.yes4_price_entry.delete(0, tk.END)
        self.yes4_price_entry.insert(0, "0.00")
        self.no4_price_entry.delete(0, tk.END)
        self.no4_price_entry.insert(0, "0.00")
            
        """当买了 4次后预防第 5 次反水，所以价格到了 50 时就平仓，然后再自动开"""
        # 设置 Yes5和No5价格为0.85
        self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
        self.yes5_price_entry.delete(0, tk.END)
        self.yes5_price_entry.insert(0, "0.5")
        self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
        self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
        self.no5_price_entry.delete(0, tk.END)
        self.no5_price_entry.insert(0, "0.85")
        self.no5_price_entry.configure(foreground='red')  # 添加红色设置

    def Sell_yes(self, yes_price=None, no_price=None):
        """当YES5价格等于实时Yes价格时自动卖出"""
        self.trading = True  # 开始交易 
        try:
            if not self.driver:
                raise Exception("Sell_yes浏览器连接丢失")

            if yes_price is None or no_price is None:
                # 获取当前Yes价格
                prices = self.driver.execute_script("""
                    function getPrices() {
                        const prices = {yes: null, no: null};
                        const elements = document.getElementsByTagName('span');
                        
                        for (let el of elements) {
                            const text = el.textContent.trim();
                            if (text.includes('Yes') && text.includes('¢')) {
                                const match = text.match(/(\\d+\\.?\\d*)¢/);
                                if (match) prices.yes = parseFloat(match[1]);
                            }
                            if (text.includes('No') && text.includes('¢')) {
                                const match = text.match(/(\\d+\\.?\\d*)¢/);
                                if (match) prices.no = parseFloat(match[1]);
                            }
                        }
                        return prices;
                    }
                    return getPrices();
                """)
                    
                if prices['yes'] is not None:
                    yes_price = float(prices['yes']) / 100
                    
                    # 获取Yes5价格
                    yes5_target = float(self.yes5_price_entry.get())
                    
                    # 检查Yes5价格匹配
                    if 0 <= (yes_price - yes5_target) <= 0.05 and yes5_target > 0:
                        self.logger.info("Yes 5价格匹配,执行自动卖出")
                        
                        # 执行卖出YES操作
                        if self.only_sell_yes():
                            self.logger.info("卖完 YES 后，检查是否需要卖出 NO")
                            
                            # 检查是否有NO持仓，最多检查3次
                            max_retries = 2
                            found_no = False
                            
                            for i in range(max_retries):
                                try:
                                    no_position = self.find_position_label_no()
                                    if no_position == "No":
                                        self.logger.info("发现NO持仓,执行卖出")
                                        self.only_sell_no()
                                        found_no = True
                                        break
                                    elif i < max_retries - 1:
                                        self.logger.info(f"第{i+1}次检查未发现NO持仓,等待1秒后重试...")
                                        time.sleep(1)
                                    else:
                                        self.logger.info("未发现NO持仓或检查完成,继续执行后续操作")
                                        pass
                                except Exception as e:
                                    self.logger.warning(f"第{i+1}次检查NO持仓时出错: {str(e)}")
                                    if i < max_retries - 1:
                                        time.sleep(1)
                                        continue
                            
                            if not found_no:
                                self.logger.info("未发现NO持仓或检查完成,继续执行后续操作")
                            
                            # 重置所有价格
                            for i in range(1,6):  # 1-5
                                yes_entry = getattr(self, f'yes{i}_price_entry', None)
                                no_entry = getattr(self, f'no{i}_price_entry', None)
                                if yes_entry:
                                    yes_entry.delete(0, tk.END)
                                    yes_entry.insert(0, "0.00")
                                if no_entry:
                                    no_entry.delete(0, tk.END)
                                    no_entry.insert(0, "0.00")

                            # 在所有操作完成后,优雅退出并重启
                            self.logger.info("准备重启程序...")
                            self.root.after(5000, self.restart_program)  # 5秒后重启                 
        except Exception as e:
            self.logger.error(f"Sell_yes执行失败: {str(e)}")
            self.update_status(f"Sell_yes执行失败: {str(e)}")
        finally:
            self.trading = False
    def Sell_no(self,yes_price=None, no_price=None):
        """当NO价格等于实时No价格时自动卖出"""
        try:
            if not self.driver:
                raise Exception("Sell_no浏览器连接丢失")   
            self.trading = True  # 开始交易

            if yes_price is None or no_price is None:
                # 获取当前No价格
                prices = self.driver.execute_script("""
                    function getPrices() {
                        const prices = {yes: null, no: null};
                        const elements = document.getElementsByTagName('span');
                        
                        for (let el of elements) {
                            const text = el.textContent.trim();
                            if (text.includes('Yes') && text.includes('¢')) {
                                const match = text.match(/(\\d+\\.?\\d*)¢/);
                                if (match) prices.yes = parseFloat(match[1]);
                            }
                            if (text.includes('No') && text.includes('¢')) {
                                const match = text.match(/(\\d+\\.?\\d*)¢/);
                                if (match) prices.no = parseFloat(match[1]);
                            }
                        }
                        return prices;
                    }
                    return getPrices();
                """)
                    
                if prices['no'] is not None:
                    no_price = float(prices['no']) / 100
                    
                    # 获取No5价格
                    no5_target = float(self.no5_price_entry.get())
                    
                    # 检查No5价格匹配
                    if 0 <= (no_price - no5_target) <= 0.05 and no5_target > 0:
                        self.logger.info("No 5价格匹配,执行自动卖出")
                        
                        # 执行卖出NO操作
                        if self.only_sell_no():
                            self.logger.info("卖完 NO 后，检查是否需要卖出 YES")
                            
                            # 检查是否有YES持仓，最多检查3次
                            max_retries = 2
                            found_yes = False
                            
                            for i in range(max_retries):
                                try:
                                    yes_position = self.find_position_label_yes()
                                    if yes_position == "Yes":
                                        self.logger.info("发现YES持仓,执行卖出")
                                        self.only_sell_yes()
                                        found_yes = True
                                        break
                                    elif i < max_retries - 1:
                                        self.logger.info(f"第{i+1}次检查未发现YES持仓,等待1秒后重试...")
                                        time.sleep(1)
                                    else:
                                        self.logger.info("未发现YES持仓或检查完成,继续执行后续操作")
                                        pass
                                except Exception as e:
                                    self.logger.warning(f"第{i+1}次检查YES持仓时出错: {str(e)}")
                                    if i < max_retries - 1:
                                        time.sleep(1)
                                        continue
                            
                            if not found_yes:
                                self.logger.info("未发现YES持仓或检查完成,继续执行后续操作")
                            
                            # 重置所有价格
                            for i in range(1,6):  # 1-5
                                yes_entry = getattr(self, f'yes{i}_price_entry', None)
                                no_entry = getattr(self, f'no{i}_price_entry', None)
                                if yes_entry:
                                    yes_entry.delete(0, tk.END)
                                    yes_entry.insert(0, "0.00")
                                if no_entry:
                                    no_entry.delete(0, tk.END)
                                    no_entry.insert(0, "0.00")

                            # 在所有操作完成后,优雅退出并重启
                            self.logger.info("准备重启程序...")
                            self.root.after(5000, self.restart_program)  # 5秒后重启              
        except Exception as e:
            self.logger.error(f"Sell_no执行失败: {str(e)}")
            self.update_status(f"Sell_no执行失败: {str(e)}")
        finally:
            self.trading = False
    """以上代码是交易主体函数 1-4,从第 1570 行到第 2283行"""

    """以下代码是交易过程中的各种方法函数，涉及到按钮的点击，从第 2285 行到第 2651 行"""
    def click_buy_confirm_button(self):
        
        try:
            buy_confirm_button = self.driver.find_element(By.XPATH, XPathConfig.BUY_CONFIRM_BUTTON)
            buy_confirm_button.click()
        except Exception as e:
            buy_confirm_button = self._find_element_with_retry(
                XPathConfig.BUY_CONFIRM_BUTTON,
                timeout=3,
                silent=True
            )
            buy_confirm_button.click()

    def find_position_label_yes(self):
        """查找Yes持仓标签"""
        max_retries = 2
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                if not self.driver:
                    self.update_status("find_position_label_yes请先连接浏览器")
                    return None
                    
                # 等待页面加载完成
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                # 尝试获取YES标签
                try:
                    
                    position_label_yes = self._find_element_with_retry(
                            XPathConfig.POSITION_YES_LABEL,
                            timeout=3,
                            silent=True
                    )
                    # 如果找到了标签，返回标签文本
                    if position_label_yes:
                        return position_label_yes.text
                    else:
                        self.logger.info("未找到Yes持仓")
                        return None
                    
                except NoSuchElementException:
                    self.logger.debug("未找到Yes持仓标签")
                    return None
                except Exception as e:
                    self.logger.error(f"查找Yes标签异常: {str(e)}")
                    return None
                    
            except TimeoutException:
                self.logger.debug(f"第{attempt + 1}次尝试未找到YES标签,正常情况!")
            except Exception as e:
                self.logger.debug(f"第{attempt + 1}次尝试发生错误: {str(e)}")
                
            if attempt < max_retries - 1:
                self.logger.info(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                self.driver.refresh()
        return None
        
    def find_position_label_no(self):
        """查找No持仓标签"""
        max_retries = 2
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                if not self.driver:
                    self.update_status("find_position_label_no请先连接浏览器")
                    return None
                    
                # 等待页面加载完成
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                # 尝试获取NO标签
                try:
                    
                    position_label_no = self._find_element_with_retry(
                            XPathConfig.POSITION_NO_LABEL,
                            timeout=3,
                            silent=True
                    )
                    # 如果找到了标签，返回标签文本
                    if position_label_no:
                        return position_label_no.text
                    else:
                        self.logger.info("未找到No持仓")
                        return None
                    
                except NoSuchElementException:
                    self.logger.debug("未找到No持仓标签")
                    return None
                except Exception as e:
                    self.logger.error(f"查找No标签异常: {str(e)}")
                    return None
                    
            except TimeoutException:
                self.logger.warning(f"第{attempt + 1}次尝试未找到NO标签")
            except Exception as e:
                self.logger.error(f"第{attempt + 1}次尝试发生错误: {str(e)}")
                
            if attempt < max_retries - 1:
                self.logger.info(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                self.driver.refresh()
        return None
        
    def click_position_sell_no(self):
        """点击 Positions-Sell-No 按钮"""
        try:
            position_yes_value = self.find_position_label_yes()
            # 根据position_yes_value的值决定点击哪个按钮
            if position_yes_value == "Yes":
                # 如果第一行是Yes，点击第二的按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_NO_BUTTON)
                except Exception as e:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_NO_BUTTON,
                        timeout=3,
                        silent=True
                    )
            else:
                # 如果第一行不存在或不是Yes，使用默认的第一行按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_BUTTON)
                except Exception as e:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_BUTTON,
                        timeout=3,
                        silent=True
                    )
            # 执行点击
            self.driver.execute_script("arguments[0].click();", button)
            self.update_status("已点击 Positions-Sell-No 按钮")  
        except Exception as e:
            error_msg = f"点击 Positions-Sell-No 按钮失败: {str(e)}"
            self.logger.error(error_msg)
            self.update_status(error_msg)

    def click_position_sell_yes(self):
        """点击 Positions-Sell-Yes 按钮，函数名漏写了一个 YES"""
        try:
            position_no_value = self.find_position_label_no()
                
            # 根据position_no_value的值决定点击哪个按钮
            if position_no_value == "No":
                # 如果第二行是No，点击第一行YES 的 SELL的按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_YES_BUTTON)
                except Exception as e:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_YES_BUTTON,
                        timeout=3,
                        silent=True
                    )
            else:
                # 如果第二行不存在或不是No，使用默认的第一行按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_BUTTON)
                except Exception as e:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_BUTTON,
                        timeout=3,
                        silent=True
                    )
            # 执行点击
            self.driver.execute_script("arguments[0].click();", button)
            self.update_status("已点击 Positions-Sell-Yes 按钮")  
        except Exception as e:
            error_msg = f"点击 Positions-Sell-Yes 按钮失败: {str(e)}"
            self.logger.error(error_msg)
            self.update_status(error_msg)

    def click_profit_sell(self):
        """点击卖出盈利按钮并处理 MetaMask 弹窗"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            # 点击Sell-卖出按钮
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.SELL_PROFIT_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.SELL_PROFIT_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击卖出盈利按钮")
            # 等待MetaMask弹窗出现
            time.sleep(1)
            # 使用统一的MetaMask弹窗处理方法
            self._handle_metamask_popup()
            """ 等待 4 秒，刷新 2 次，预防交易失败 """
            # 等待交易完成
            time.sleep(2)
            self.driver.refresh()
            self.update_status("交易完成并刷新页面")
        except Exception as e:
            error_msg = f"卖出盈利操作失败: {str(e)}"
            self.logger.error(error_msg)
            self.update_status(error_msg)

    def click_buy(self):
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.BUY_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击 Buy 按钮")
        except Exception as e:
            self.logger.error(f"点击 Buy 按钮失败: {str(e)}")
            self.update_status(f"点击 Buy 按钮失败: {str(e)}")

    def click_buy_yes(self):
        """点击 Buy.Yes 按钮"""
        try:
            if not self.driver:
                self.update_status("请先连接浏器")
                return
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_YES_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.BUY_YES_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击 Buy.Yes 按钮")
        except Exception as e:
            self.logger.error(f"点击 Buy.Yes 按钮失败: {str(e)}")
            self.update_status(f"点击 Buy.Yes 按钮失败: {str(e)}")

    def click_buy_no(self):
        """点击 Buy.No 按钮"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_NO_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.BUY_NO_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击 Buy.No 按钮")
        except Exception as e:
            self.logger.error(f"点击 Buy.No 按钮失败: {str(e)}")
            self.update_status(f"点击 Buy.No 按钮失败: {str(e)}")

    def click_sell_yes(self):
        """点击 Sell-Yes 按钮"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.SELL_YES_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.SELL_YES_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击 Sell-Yes 按钮")
        except Exception as e:
            self.logger.error(f"点击 Sell-Yes 按钮失败: {str(e)}")
            self.update_status(f"点击 Sell-Yes 按钮失败: {str(e)}")

    def click_sell_no(self):
        """点击 Sell-No 按钮"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.SELL_NO_BUTTON)
            except Exception as e:
                button = self._find_element_with_retry(
                    XPathConfig.SELL_NO_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            self.update_status("已点击 Sell-No 按钮")
        except Exception as e:
            self.logger.error(f"点击 Sell-No 按钮失败: {str(e)}")
            self.update_status(f"点击 Sell-No 按钮失败: {str(e)}")

    def click_amount(self, event=None):
        """点击 Amount 按钮并输入数量"""
        try:
            if not self.driver:
                self.update_status("请先连接浏览器")
                return         
            
            # 获取触发事件的按钮
            button = event.widget if event else self.amount_button
            button_text = button.cget("text")
            # 找到输入框
            try:
                amount_input = self.driver.find_element(By.XPATH, XPathConfig.AMOUNT_INPUT)
            except Exception as e:
                amount_input = self._find_element_with_retry(
                    XPathConfig.AMOUNT_INPUT,
                    timeout=3,
                    silent=True
                )
            # 清空输入框
            amount_input.clear()
            # 根据按钮文本获取对应的金额
            if button_text == "Amount.Yes1":
                amount = self.yes1_amount_entry.get()
            elif button_text == "Amount.Yes2":
                yes2_amount_entry = self.yes_frame.grid_slaves(row=3, column=1)[0]
                amount = yes2_amount_entry.get()
            elif button_text == "Amount.Yes3":
                yes3_amount_entry = self.yes_frame.grid_slaves(row=5, column=1)[0]
                amount = yes3_amount_entry.get()
            elif button_text == "Amount.Yes4":
                yes4_amount_entry = self.yes_frame.grid_slaves(row=7, column=1)[0]
                amount = yes4_amount_entry.get()
            
            # No 按钮
            elif button_text == "Amount.No1":
                no1_amount_entry = self.no_frame.grid_slaves(row=1, column=1)[0]
                amount = no1_amount_entry.get()
            elif button_text == "Amount.No2":
                no2_amount_entry = self.no_frame.grid_slaves(row=3, column=1)[0]
                amount = no2_amount_entry.get()
            elif button_text == "Amount.No3":
                no3_amount_entry = self.no_frame.grid_slaves(row=5, column=1)[0]
                amount = no3_amount_entry.get()
            elif button_text == "Amount.No4":
                no4_amount_entry = self.no_frame.grid_slaves(row=7, column=1)[0]
                amount = no4_amount_entry.get()
            else:
                amount = "0.0"
            # 输入金额
            amount_input.send_keys(str(amount))
            
            self.update_status(f"已在Amount输入框输入: {amount}")    
        except Exception as e:
            self.logger.error(f"Amount操作失败: {str(e)}")
            self.update_status(f"Amount操作失败: {str(e)}")

    """以下代码是交易过程中的功能性函数,买卖及确认买卖成功,从第 2651 行到第 2956行"""
    def Verify_buy_yes(self):
        """
        验证交易是否成功完成Returns:bool: 交易是否成功
        """
        max_retries = 3  # 最大重试次数
        for attempt in range(max_retries):
            try:
                # 首先验证浏览器状态
                if not self.driver:
                    self.logger.error("浏览器连接已断开")
                    return False
                # 等待并检查是否存在 Yes 标签
                try:
                    yes_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
                except Exception as e:
                    yes_element = self._find_element_with_retry(
                        XPathConfig.HISTORY,
                        timeout=3,
                        silent=True
                    )
                text = yes_element.text
                trade_type = re.search(r'\b(Bought)\b', text)  # 匹配单词 Bought
                yes_match = re.search(r'\b(Yes)\b', text)  # 匹配单词 Yes
                amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
                
                if trade_type.group(1) == "Bought" and yes_match.group(1) == "Yes":
                    self.trade_type = trade_type.group(1)  # 获取 "Bought"
                    self.buy_yes_value = yes_match.group(1)  # 获取 "Yes"
                    self.buy_yes_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                    self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_yes_value}-${self.buy_yes_amount}")
                    return True

                # 验证失败，记录日志并重试
                if attempt < max_retries - 1:
                    self.logger.warning(f"验证买入YES失败,第{attempt+1}次尝试,将在1秒后重试")
                    time.sleep(1)
                else:
                    self.logger.error(f"验证买入YES失败,已达到最大重试次数({max_retries}次)")
                    return False

            except Exception as e:
                self.logger.warning(f"Verify_buy_yes执行失败: {str(e)}")
                if attempt < max_retries - 1:
                    self.logger.warning(f"第{attempt+1}次尝试失败,将在1秒后重试")
                    time.sleep(1)
                else:
                    self.logger.error(f"验证买入YES失败,已达到最大重试次数({max_retries}次)")
                    return False

        return False
        
    def Verify_buy_no(self):
        """
        验证交易是否成功完成
        Returns:
        bool: 交易是否成功
        """
        max_retries = 3  # 最大重试次数
        
        for attempt in range(max_retries):
            try:
                # 首先验证浏览器状态
                if not self.driver:
                    self.logger.error("浏览器连接已断开")
                    return False
                # 等待并检查是否存在 No 标签
                try:
                    no_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
                except Exception as e:
                    no_element = self._find_element_with_retry(
                        XPathConfig.HISTORY,
                        timeout=3,
                        silent=True
                    )
                text = no_element.text

                trade_type = re.search(r'\b(Bought)\b', text)  # 匹配单词 Bought
                no_match = re.search(r'\b(No)\b', text)  # 匹配单词 No
                amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式

                if trade_type.group(1) == "Bought" and no_match.group(1) == "No":
                    self.trade_type = trade_type.group(1)  # 获取 "Bought"
                    self.buy_no_value = no_match.group(1)  # 获取 "No"
                    self.buy_no_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                    self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_no_value}-${self.buy_no_amount}")
                    return True

                # 验证失败，记录日志并重试
                if attempt < max_retries - 1:
                    self.logger.warning(f"验证买入NO失败,第{attempt+1}次尝试,将在1秒后重试")
                    time.sleep(1)
                else:
                    self.logger.error(f"验证买入NO失败,已达到最大重试次数({max_retries}次)")
                    return False

            except Exception as e:
                self.logger.warning(f"Verify_buy_no执行失败: {str(e)}")
                if attempt < max_retries - 1:
                    self.logger.warning(f"第{attempt+1}次尝试失败,将在1秒后重试")
                    time.sleep(1)
                else:
                    self.logger.error(f"验证买入NO失败,已达到最大重试次数({max_retries}次)")
                    return False  
        return False
        
    def position_yes_cash(self):
        """获取当前持仓YES的金额"""
        try:
            yes_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
        except Exception as e:
            yes_element = self._find_element_with_retry(
                XPathConfig.HISTORY,
                timeout=3,
                silent=True
            )
        text = yes_element.text
        amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
        yes_value = float(amount_match.group(1))
        self.logger.info(f"当前持仓YES的金额: {yes_value}")
        return yes_value
    
    def position_no_cash(self):
        """获取当前持仓NO的金额"""
        try:
            no_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
        except Exception as e:
            no_element = self._find_element_with_retry(
                XPathConfig.HISTORY,
                timeout=3,
                silent=True
            )
        text = no_element.text
        amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
        no_value = float(amount_match.group(1))
        self.logger.info(f"当前持仓NO的金额: {no_value}")
        return no_value
    
    def Verify_sold_yes(self):
        """
        验证交易是否成功完成Returns:bool: 交易是否成功
        """
        try:
            # 首先验证浏览器状态
            if not self.driver:
                self.logger.error("浏览器连接已断开")
                return False
            # 等待并检查是否存在 Yes 标签
            try:
                yes_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
            except Exception as e:
                yes_element = self._find_element_with_retry(
                    XPathConfig.HISTORY,
                    timeout=3,
                    silent=True
                )
            text = yes_element.text
            trade_type = re.search(r'\b(Sold)\b', text)  # 匹配单词 Sold
            yes_match = re.search(r'\b(Yes)\b', text)  # 匹配单词 Yes
            amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
            
            if trade_type.group(1) == "Sold" and yes_match.group(1) == "Yes":
                self.trade_type = trade_type.group(1)  # 获取 "Sold"
                self.buy_yes_value = yes_match.group(1)  # 获取 "Yes"
                self.buy_yes_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_yes_value}-${self.buy_yes_amount}")
                return True
            return False       
        except Exception as e:
            self.logger.warning(f"Verify_sold_yes执行失败: {str(e)}")
            return False
        
    def Verify_sold_no(self):
        """
        验证交易是否成功完成
        Returns:
        bool: 交易是否成功
        """
        try:
            # 首先验证浏览器状态
            if not self.driver:
                self.logger.error("浏览器连接已断开")
                return False
            # 等待并检查是否存在 No 标签
            try:
                no_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY)
            except Exception as e:
                no_element = self._find_element_with_retry(
                    XPathConfig.HISTORY,
                    timeout=3,
                    silent=True
                )
            text = no_element.text

            trade_type = re.search(r'\b(Sold)\b', text)  # 匹配单词 Sold
            no_match = re.search(r'\b(No)\b', text)  # 匹配单词 No
            amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式

            if trade_type.group(1) == "Sold" and no_match.group(1) == "No":
                self.trade_type = trade_type.group(1)  # 获取 "Sold"
                self.buy_no_value = no_match.group(1)  # 获取 "No"
                self.buy_no_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_no_value}-${self.buy_no_amount}")
                return True
            return False        
        except Exception as e:
            self.logger.warning(f"Verify_sold_no执行失败: {str(e)}")
            return False

    def only_sell_yes(self):
        """只卖出YES"""
        max_retries = 3  # 最大重试次数
        
        for attempt in range(max_retries):
            try:
                # 获取当前价格
                prices = self.driver.execute_script("""
                        function getPrices() {
                            const prices = {yes: null, no: null};
                            const elements = document.getElementsByTagName('span');
                            
                            for (let el of elements) {
                                const text = el.textContent.trim();
                                if (text.includes('Yes') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.yes = parseFloat(match[1]);
                                }
                                if (text.includes('No') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.no = parseFloat(match[1]);
                                }
                            }
                            return prices;
                        }
                        return getPrices();
                    """)
                yes_price = float(prices['yes']) / 100 if prices['yes'] else 0

                self.position_sell_yes_button.invoke()
                time.sleep(0.5)
                self.sell_profit_button.invoke()
                
                self.sleep_refresh("only_sell_yes")

                if self.Verify_sold_yes():
                    # 增加卖出计数
                    self.sell_count += 1
                        
                    # 发送交易邮件 - 卖出YES
                    self.send_trade_email(
                        trade_type="Sell Yes",
                        price=yes_price,
                        amount=self.position_yes_cash(),  # 卖出时金额为总持仓
                        trade_count=self.sell_count  # 使用卖出计数器
                    )
                    return True  # 成功卖出，返回True
                else:
                    if attempt < max_retries - 1:  # 如果还有重试机会
                        self.logger.warning(f"卖出YES验证失败,第{attempt + 1}次重试")
                        time.sleep(1)  # 等待1秒后重试
                        continue
                    else:
                        self.logger.error("卖出YES验证失败,已达到最大重试次数")
                        return False  # 达到最大重试次数，返回False
                        
            except Exception as e:
                self.logger.error(f"卖出YES操作失败: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return False
                
        return False  # 所有重试都失败后返回False
    
    def only_sell_no(self):
        """只卖出NO"""
        max_retries = 3  # 最大重试次数
        
        for attempt in range(max_retries):
            try:
                # 获取当前价格
                prices = self.driver.execute_script("""
                        function getPrices() {
                            const prices = {yes: null, no: null};
                            const elements = document.getElementsByTagName('span');
                            
                            for (let el of elements) {
                                const text = el.textContent.trim();
                                if (text.includes('Yes') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.yes = parseFloat(match[1]);
                                }
                                if (text.includes('No') && text.includes('¢')) {
                                    const match = text.match(/(\\d+\\.?\\d*)¢/);
                                    if (match) prices.no = parseFloat(match[1]);
                                }
                            }
                            return prices;
                        }
                        return getPrices();
                    """)
                no_price = float(prices['no']) / 100 if prices['no'] else 0

                self.position_sell_yes_button.invoke()
                time.sleep(0.5)
                self.sell_profit_button.invoke()
                
                self.sleep_refresh("only_sell_yes")
                
                if self.Verify_sold_no():
                    # 增加卖出计数
                    self.sell_count += 1
                        
                    # 发送交易邮件 - 卖出YES
                    self.send_trade_email(
                        trade_type="Sell NO",
                        price=no_price,
                        amount=self.position_no_cash(),  # 卖出时金额为总持仓
                        trade_count=self.sell_count  # 使用卖出计数器
                    )
                    return True  # 成功卖出，返回True
                else:
                    if attempt < max_retries - 1:  # 如果还有重试机会
                        self.logger.warning(f"卖出NO验证失败,第{attempt + 1}次重试")
                        time.sleep(1)  # 等待1秒后重试
                        continue
                    else:
                        self.logger.error("卖出NO验证失败,已达到最大重试次数")
                        return False  # 达到最大重试次数，返回False
                        
            except Exception as e:
                self.logger.error(f"卖出NO操作失败: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return False
                
        return False  # 所有重试都失败后返回False
        
    """以下代码是程序重启功能,从第 2956 行到第 2651 行"""
    def restart_program(self):
        """重启程序,保持浏览器打开"""
        try:
            self.logger.info("正在重启程序...")
            self.update_status("正在重启程序...")
            
            # 获取当前脚本的完整路径
            script_path = os.path.abspath('run_trader.sh')
        
            # 使用完整路径和正确的参数顺序
            os.execl('/bin/bash', '/bin/bash', script_path, '--restart')
            
        except Exception as e:
            self.logger.error(f"重启程序失败: {str(e)}")
            self.update_status(f"重启程序失败: {str(e)}")

    def auto_start_monitor(self):
        """自动点击开始监控按钮"""
        try:
            self.logger.info("准备阶段：重置按钮状态")
            # 强制启用开始按钮
            self.start_button['state'] = 'normal'
            self.stop_button['state'] = 'disabled'
            # 清除可能存在的锁定状态
            self.running = False

            self.logger.info("尝试自动点击开始监控按钮...")
            self.logger.info(f"当前开始按钮状态: {self.start_button['state']}")
                
            # 强制点击按钮（即使状态为disabled）
            self.start_button.invoke()
            self.logger.info("已成功触发开始按钮")

        except Exception as e:
            self.logger.error(f"自动点击失败: {str(e)}")
            self.root.after(10000, self.auto_start_monitor)

    def _handle_metamask_popup(self):
        """处理 MetaMask 扩展弹窗的键盘操作"""
        try:
            # 直接等待一段时间让MetaMask扩展弹窗出现
            time.sleep(2)
            # 模拟键盘操作序列
            # 1. 按6次TAB
            for _ in range(6):
                pyautogui.press('tab')
                time.sleep(0.1)  # 每次按键之间添加短暂延迟
            # 2. 按1次ENTER
            pyautogui.press('enter')
            time.sleep(0.1)  # 等待第一次确认响应
            # 3. 按2次TAB
            for _ in range(2):
                pyautogui.press('tab')
                time.sleep(0.1)
            # 4. 按1次ENTER
            pyautogui.press('enter')
            # 等待弹窗自动关闭
            time.sleep(0.3)
            self.logger.info("MetaMask 扩展弹窗操作完成")
        except Exception as e:
            error_msg = f"处理 MetaMask 扩展弹窗失败: {str(e)}"
            self.logger.error(error_msg)
            self.update_status(error_msg)
            raise

    def sleep_refresh(self, operation_name="未指定操作"):
        """
        执行等待3秒并刷新页面的操作,重复1次
        Args:
            operation_name (str): 操作名称,用于日志记录
        """
        try:
            for i in range(2):  # 重复次数，修改数字即可
                time.sleep(3)  # 等待3秒
                self.driver.refresh()    
        except Exception as e:
            self.logger.error(f"{operation_name} - sleep_refresh操作失败: {str(e)}")

    def set_default_price(self, price):
        """设置默认目标价格"""
        try:
            self.default_target_price = float(price)
            self.yes1_price_entry.delete(0, tk.END)
            self.yes1_price_entry.insert(0, str(self.default_target_price))
            self.no1_price_entry.delete(0, tk.END)
            self.no1_price_entry.insert(0, str(self.default_target_price))
            self.logger.info(f"默认目标价格已更新为: {price}")
        except ValueError:
            self.logger.error("价格设置无效，请输入有效数字")

    def send_trade_email(self, trade_type, price, amount, trade_count):
        """发送交易邮件"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                hostname = socket.gethostname()
                sender = 'huacaihuijin@126.com'
                receiver = 'huacaihuijin@126.com'
                app_password = 'YUwsXZ8SYSW6RcTf'  # 有效期 180 天，请及时更新，下次到期日 2025-06-29
                
                # 获取交易币对信息
                full_pair = self.trading_pair_label.cget("text")
                trading_pair = full_pair.split('-on')[0]

                if not trading_pair or trading_pair == "--":
                    trading_pair = "未知交易币对"
                
                # 根据交易类型选择显示的计数
                count_in_subject = self.sell_count if "Sell" in trade_type else trade_count
                
                msg = MIMEMultipart()
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                subject = f'{hostname}第{count_in_subject}次{trade_type}-{trading_pair}'
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = sender
                msg['To'] = receiver
                
                content = f"""
                交易价格: ${price:.2f}
                交易金额: ${amount:.2f}
                交易时间: {current_time}
                当前买入次数: {self.trade_count}
                当前卖出次数: {self.sell_count}
                """
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
                
                # 使用126.com的SMTP服务器
                server = smtplib.SMTP_SSL('smtp.126.com', 465, timeout=5)  # 使用SSL连接
                server.set_debuglevel(0)
                
                try:
                    server.login(sender, app_password)
                    server.sendmail(sender, receiver, msg.as_string())
                    self.logger.info(f"邮件发送成功: {trade_type}")
                    self.update_status(f"交易邮件发送成功: {trade_type}")
                    return  # 发送成功,退出重试循环
                except Exception as e:
                    self.logger.error(f"SMTP操作失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                finally:
                    try:
                        server.quit()
                    except Exception:
                        pass          
            except Exception as e:
                self.logger.error(f"邮件准备失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)     
        # 所有重试都失败
        error_msg = f"发送邮件失败,已重试{max_retries}次"
        self.logger.error(error_msg)
        self.update_status(error_msg)

    def stop_monitoring(self):
        """停止监控"""
        try:
            self.running = False
            self.price_monitoring = False  # 禁用价格监控
            self.balance_monitoring = False  # 禁用资金监控

            self.stop_event.set()  # 设置停止事件
            # 取消所有定时器
            for timer in [self.url_check_timer, self.login_check_timer, self.refresh_timer]:
                if timer:
                    self.root.after_cancel(timer)
            # 停止URL监控
            if self.url_check_timer:
                self.root.after_cancel(self.url_check_timer)
                self.url_check_timer = None
            # 停止登录状态监控
            if self.login_check_timer:
                self.root.after_cancel(self.login_check_timer)
                self.login_check_timer = None
            
            self.start_button['state'] = 'normal'
            self.stop_button['state'] = 'disabled'
            self.update_status("监控已停止")
            self.update_amount_button['state'] = 'disabled'  # 禁用更新金额按钮
            
            # 将"停止监控"文字变为红色
            self.stop_button.configure(style='Red.TButton')
            # 恢复"开始监控"文字为蓝色
            self.start_button.configure(style='Black.TButton')
            if self.driver:
                self.driver.quit()
                self.driver = None
            # 记录最终交易次数
            final_trade_count = self.trade_count
            self.logger.info(f"本次监控共执行 {final_trade_count} 次交易")

            # 取消页面刷新定时器
            if self.refresh_timer:
                self.root.after_cancel(self.refresh_timer)
                self.refresh_timer = None

        except Exception as e:
            self.logger.error(f"停止监控失败: {str(e)}")

    def update_status(self, message):
        # 检查是否是错误消息
        is_error = any(keyword in message for keyword in ["错误", "失败", "异常","error"])  # 更全面的关键词检测
        # 更新状态标签，如果是错误则显示红色
        self.status_label.config(
            text=f"状态: {message}",
            foreground='red' if is_error else 'black'
        )
        
        # 错误消息记录到日志文件
        if is_error:
            self.logger.error(message)

    def retry_operation(self, operation, *args, **kwargs):
        """通用重试机制"""
        for attempt in range(self.retry_count):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                self.logger.warning(f"{operation.__name__} 失败，尝试 {attempt + 1}/{self.retry_count}: {str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_interval)
                else:
                    raise
    
    def run(self):
        """启动程序"""
        try:
            self.logger.info("启动主程序...")
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"程序运行出错: {str(e)}")
            raise

    """以下代码是自动找币的函数,从第 3191 行到第 3250 行"""
    def is_position_yes_or_no(self):
        self.logger.info("检查当前是否持仓")
        try:
            # 同时检查Yes/No两种持仓标签
            yes_element = self.find_position_label_yes()
            no_element = self.find_position_label_no()

            full_pair = self.trading_pair_label.cget("text")
            trading_pair = full_pair.split('-above')[0]

            # 任一标签显示持仓状态即返回True
            if (yes_element and yes_element=="Yes") or (no_element and no_element=="No"):
                self.logger.info(f"检测到持仓状态,持仓为{trading_pair}:{yes_element}或{no_element}")
                return True
            elif yes_element is None and no_element is None:
                return False
            else:
                return False
            
        except Exception as e:
            self.logger.error(f"持仓检查异常: {str(e)}")

        return True
            
    def contrast_portfolio_cash(self):
        """对比持仓币对和现金"""
        try:
            value = self.get_portfolio_value() - self.cash_value

            if value > 2 or value < 0:
                
                return True
            else:
                return False
            
        except Exception as e:
            self.logger.error(f"持仓币对和现金对比异常: {str(e)}")
            return False

    def find_new_weekly_url(self, coin):
        """在Polymarket市场搜索指定币种的周合约地址,只返回周合约地址"""
        try:
                # 保存原始窗口句柄
                self.original_tab = self.driver.current_window_handle 

                # 重置所有按钮样式为蓝色
                for btn in [self.btc_button, self.eth_button, self.solana_button, 
                        self.xrp_button, self.doge_button]:
                    btn.configure(style='Blue.TButton')
                
                # 设置被点击的按钮为红色
                if coin == 'BTC':
                    self.btc_button.configure(style='Red.TButton')
                elif coin == 'ETH':
                    self.eth_button.configure(style='Red.TButton')
                elif coin == 'SOLANA':
                    self.solana_button.configure(style='Red.TButton')
                elif coin == 'XRP':
                    self.xrp_button.configure(style='Red.TButton')
                elif coin == 'DOGE':
                    self.doge_button.configure(style='Red.TButton')

                base_url = "https://polymarket.com/markets/crypto?_s=start_date%3Adesc"
                self.driver.switch_to.new_window('tab')
                self.driver.get(base_url)

                # 定义search_tab变量，保存搜索标签页的句柄
                search_tab = self.driver.current_window_handle
                # 等待页面加载完成
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(3)  # 等待页面渲染完成
                
                # 设置搜索关键词
                link_text_map = {
                    'BTC': 'Bitcoin above',
                    'ETH': 'Ethereum above',
                    'SOLANA': 'Solana above',
                    'XRP': 'Ripple above',
                    'DOGE': 'Dogecoin above'
                }
                search_text = link_text_map.get(coin, '')
                
                if not search_text:
                    self.logger.error(f"无效的币种: {coin}")
                    # 关闭搜索标签页
                    self.driver.close()
                    # 切换回原始窗口
                    self.driver.switch_to.window(self.original_tab)
                    return None
                try:
                    # 使用确定的XPath查找搜索框
                    try:
                        search_box = self.driver.find_element(By.XPATH, XPathConfig.SEARCH_INPUT)
                    except Exception as e:
                        search_box = self._find_element_with_retry(
                            XPathConfig.SEARCH_INPUT,
                            timeout=3,
                            silent=True
                        )
                    
                    # 创建ActionChains对象
                    actions = ActionChains(self.driver)
                    
                    # 清除搜索框并输入搜索词
                    search_box.clear()
                    search_box.send_keys(search_text)
                    time.sleep(1)  # 等待搜索词输入完成
                    
                    # 按ENTER键开始搜索
                    actions.send_keys(Keys.RETURN).perform()
                    time.sleep(1)  # 等待搜索结果加载
                    
                    # 按4次TAB键
                    for i in range(4):
                        actions.send_keys(Keys.TAB).perform()
                        time.sleep(0.3)  # 每次TAB之间等待1秒
                    
                    # 使用正确的组合键（Windows/Linux用Ctrl+Enter，Mac用Command+Enter）
                    modifier_key = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
                    
                    # 创建动作链
                    actions = ActionChains(self.driver)
                    actions.key_down(modifier_key).send_keys(Keys.ENTER).key_up(modifier_key).perform()
                    
                    # 切换到新标签页获取完整URL
                    time.sleep(1)  # 等待新标签页打开
            
                    # 获取所有窗口句柄
                    all_handles = self.driver.window_handles
                    
                    # 切换到最新打开的标签页
                    if len(all_handles) > 2:  # 原始窗口 + 搜索标签页 + coin标签页
                        time.sleep(2)  # 等待新标签页打开
                        self.driver.switch_to.window(all_handles[-1])
                        WebDriverWait(self.driver, 20).until(EC.url_contains('/event/'))
                        
                        # 获取当前URL
                        new_weekly_url = self.driver.current_url

                        # 关闭当前URL标签页
                        self.driver.close()
                        
                        # 切换回搜索标签页
                        self.driver.switch_to.window(search_tab)
                        
                        # 关闭搜索标签页
                        self.driver.close()
                        
                        # 切换回原始窗口
                        self.driver.switch_to.window(self.original_tab)
                        
                        return new_weekly_url
                    else:
                        self.logger.warning(f"未能打开{coin}的详情页")
                        # 关闭搜索标签页
                        self.driver.close()
                        # 切换回原始窗口
                        self.driver.switch_to.window(self.original_tab)
                        return None
                    
                except NoSuchElementException as e:
                    self.logger.warning(f"未找到{coin}周合约链接: {str(e)}")
                    # 关闭搜索标签页
                    self.driver.close()
                    # 切换回原始窗口
                    self.driver.switch_to.window(self.original_tab)
                    return None
        except Exception as e:
            self.logger.error(f"操作失败: {str(e)}")
            # 尝试恢复到原始窗口
            try:
                # 获取所有窗口句柄
                all_handles = self.driver.window_handles
                
                # 关闭除原始窗口外的所有标签页
                for handle in all_handles:
                    if handle != self.original_tab:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                
                # 切换回原始窗口
                self.driver.switch_to.window(self.original_tab)
            except Exception as inner_e:
                self.logger.error(f"恢复窗口时出错: {str(inner_e)}")
            
            return None

    #-----------------以下是自动找 54 币的函数-----------------
    def is_saturday_reboot_time(self):
        """判断是否处于周六重启时段(周六3到 4点)"""
        self.logger.info("检查是否处于周六重启时段")
        try:
            beijing_tz = timezone(timedelta(hours=8))
            now = datetime.now(timezone.utc).astimezone(beijing_tz)
            
            # 周六1到4点
            if now.weekday() == 5 and 3 <= now.hour <= 4:
                self.logger.info("当前处于周六重启时段")
                self.root.after(3600000, self.restart_program)

        except Exception as e:
            self.logger.error(f"找币时间判断异常: {str(e)}")
            return False
    def is_stop_mornitoring_time(self):
        """判断是否处于停止监控时段(周 6 凌晨 1 点)"""
        self.logger.info("检查是否处于停止监控时段")
        try:
            beijing_tz = timezone(timedelta(hours=8))
            now = datetime.now(timezone.utc).astimezone(beijing_tz)

            # 周6 1点
            if now.weekday() == 5 and now.hour == 1:
                self.logger.info("当前处于停止监控时段")
                self.stop_monitoring()
                
        except Exception as e:
            self.logger.error(f"找币时间判断异常: {str(e)}")
            return False

    def is_auto_find_54_coin_time(self):
        """判断是否处于自动找币时段(周六13点至周五20点)"""
        self.logger.info("检查是否处于自动找币时段")
        try:
            beijing_tz = timezone(timedelta(hours=8))
            now = datetime.now(timezone.utc).astimezone(beijing_tz)
            
            # 周六判断（weekday=5）
            if now.weekday() == 5:
                # 周六13点至23:59
                if now.hour >= 4:
                    self.logger.info("当前处于找币时段")
                    return True
            
            # 周日至周五判断（weekday=6到4）
            elif now.weekday() in (6,0,1,2,3,4):
                # 全天有效直到周五20点
                if now.hour < 20 or (now.weekday() != 4 and now.hour >= 20):
                    self.logger.info("当前处于找币时段")
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"找币时间判断异常: {str(e)}")
            return False
    
    def check_restart(self):
        """检查是否处于重启模式"""
        if '--restart' in sys.argv:
            self.logger.info("检测到重启模式")
            return True
        else:
            return False

    def extract_base_url(self, url):
        """
        将URL分隔成两部分,返回第一部分基础URL
        例如：从 https://polymarket.com/event/dogecoin-above-0pt20-on-march-14/dogecoin-above-0pt20-on-march-14?tid=1741406505993
        提取 https://polymarket.com/event/dogecoin-above-0pt20-on-march-14
        """
        try:
            # 首先按问号分隔，去除查询参数
            url_without_query = url.split('?')[0]
            
            # 然后按斜杠分隔，找到最后一个斜杠之前的部分
            parts = url_without_query.split('/')
            
            # 如果URL格式符合预期（至少有event部分）
            if len(parts) >= 5 and 'event' in parts:
                # 获取到event部分的索引
                event_index = parts.index('event')
                # 构建基础URL（包含event和event名称）
                base_url = '/'.join(parts[:event_index+2])
                self.logger.info(f"提取的基础URL: {base_url}")
                return base_url
            else:
                # 如果URL格式不符合预期，返回原始URL
                self.logger.warning(f"URL格式不符合预期,无法提取基础部分: {url}")
                return url
        except Exception as e:
            self.logger.error(f"提取基础URL时出错: {str(e)}")
            return url

    def contrast_portfolio_cash(self):
        """对比持仓币对和现金"""
        try:
            value = self.get_portfolio_value() - self.cash_value

            if value > 1.5 or value < 0:
                self.logger.info(f"{value}不等于0,有持仓")
                # 点击 Portfolio 按钮
                try:
                    # 点击 Portfolio 按钮 - 确保使用字符串类型的XPath
                    portfolio_button = self.driver.find_element(By.XPATH, XPathConfig.PORTFOLIO_BUTTON)
                    self.logger.info(f"点击Portfolio按钮: {portfolio_button}")
                    portfolio_button.click()
                    time.sleep(1)
                except Exception as e:
                    
                    # 尝试使用_find_element_with_retry方法
                    try:
                        portfolio_button = self._find_element_with_retry(
                            XPathConfig.PORTFOLIO_BUTTON,
                            timeout=3,
                            silent=True
                        )
                        if portfolio_button:
                            portfolio_button.click()
                            time.sleep(1)
                        else:
                            self.logger.error("无法找到Portfolio按钮")
                            return False
                    except Exception as retry_e:
                        self.logger.error(f"使用retry方法点击Portfolio按钮失败: {str(retry_e)}")
                        return False
                        
                # 敲击 29 下 TAB 键
                for i in range(29):
                    pyautogui.press('tab')
                    
                # 敲击 1 下 ENTER 键
                pyautogui.press('enter')
                time.sleep(1)

                # 保存当前 URL 到 config
                current_url = self.driver.current_url
                base_url = self.extract_base_url(current_url)
                self.config['website']['url'] = base_url
                self.save_config()
                self.logger.info(f"已保存当前 URL 到 config: {base_url}")
                # 监控当前 URL
                self.target_url = base_url
                self.start_url_monitoring()
                self.refresh_page()
                self.stop_auto_find_54_coin()
                return True
            else:
                return False
        except Exception as e:
            self.logger.error(f"持仓币对和现金对比异常: {str(e)}")
            return False

    def auto_find_54_coin(self):
        """自动找54币"""
        self.logger.info("进入自动找54币模式")
        # 检查是否处于持仓状态
        if self.contrast_portfolio_cash():
            return

        # 检查是否处于重启模式，如果是则延迟执行
        if self.check_restart():
            self.logger.info("检测到重启模式,等待10分钟后重试")
            # 使用after代替sleep，避免阻塞
            # 创建一个不带重启标志的函数，避免再次进入重启检查
            def continue_without_restart_check():
                # 设置一个标志表示已经处理过重启模式
                self.restart_handled = True
                self.continue_auto_find()
            
            self.root.after(600000, continue_without_restart_check)
            return  # 直接返回，不继续执行

        # 确保有停止标志
        self.stop_auto_find = False
        self.auto_find_running = True  # 添加运行状态标志
        self.logger.info("开始自动找54币")
        self.continue_auto_find()
    
    def continue_auto_find(self):
        if self.stop_auto_find or not self.running:
            self.auto_find_running = False
            self.logger.info("auto_find_54_coin已停止")
            return

        # 检查YES/NO 没有持仓
        if not self.is_position_yes_or_no():
            try:
                # 检查是否被要求停止
                if self.stop_auto_find:
                    self.logger.info("检测到停止标志,auto_find_54_coin线程退出")
                    return

                if self.is_auto_find_54_coin_time():# 判断是否处于自动找币时段
                    self.logger.info("开始循环找币!")

                    # 停止URL监控
                    self.stop_url_monitoring()
                    self.stop_refresh_page()
                    time.sleep(1)
                
                    # 启动找币线程，不使用join阻塞
                    find_thread = threading.Thread(target=self.find_54_coin, daemon=True)
                    find_thread.start()

                    # 使用定时器检查找币线程是否完成
                    def check_find_thread():
                        if not find_thread.is_alive():
                            # 找币完成，恢复监控
                            if not self.stop_auto_find and not self.is_url_monitoring:
                                self.logger.info("✅ 找币完成,已恢复URL监控")
                                self.start_url_monitoring()
                                self.refresh_page()
                            # 安排下一次找币
                            self.schedule_next_find()
                        else:
                            # 线程仍在运行，继续检查
                            self.root.after(5000, check_find_thread)
                    # 启动线程检查
                    self.root.after(5000, check_find_thread)
                else:
                    self.logger.debug("当前不在自动找币时段")
                    # 恢复监控并安排下一次找币
                    if not self.is_url_monitoring:
                        self.start_url_monitoring()
                        self.refresh_page()
                    self.schedule_next_find()

            except Exception as e:
                self.logger.error(f"自动找币异常: {str(e)}")
                # 恢复监控并安排下一次找币
                if not self.stop_auto_find and not self.is_url_monitoring:
                    self.start_url_monitoring()
                    self.refresh_page()
                self.schedule_next_find()      
        else:
            self.logger.info("当前持仓，停止找币")
            self.schedule_next_find()

    # 安排下一次找币
    def schedule_next_find(self):
        if self.stop_auto_find or not self.running:
            self.auto_find_running = False
            self.logger.info("auto_find_54_coin已停止")
            return
            
        self.logger.info("安排10分钟后再次执行找币")
        # 使用after代替sleep，避免阻塞
        if hasattr(self, 'continue_auto_find') and self.continue_auto_find:
            self.auto_find_timer = self.root.after(600000, self.continue_auto_find)  # 10分钟 = 600000毫秒
        else:
            self.logger.error("continue_auto_find未定义,无法安排下一次找币")
            # 尝试重新启动自动找币
            self.auto_find_running = False
            self.root.after(600000, self.auto_find_54_coin)

    def find_54_coin(self):
        try:
            # 保存原始窗口句柄，确保在整个过程中有一个稳定的引用
            self.original_window = self.driver.current_window_handle
            # 设置搜索关键词
            coins = [
                'BTC',
                'ETH',
                'SOLANA',
                'XRP',
                'DOGE'
            ]
            for coin in coins:
                if self.stop_auto_find:
                    self.logger.info("找币过程中检测到停止标志，中断操作")
                    break

                try:  # 为每个币种添加单独的异常处理
                    coin_new_weekly_url = self.find_new_weekly_url(coin)
                    
                    if coin_new_weekly_url:
                        # 确保我们从原始窗口开始
                        try:
                            self.driver.switch_to.window(self.original_window)
                        except Exception as e:
                            self.logger.error(f"切换到原始窗口失败: {str(e)}")
                            # 如果原始窗口不可用，可能需要重新创建一个窗口
                            self.driver.switch_to.new_window('tab')
                            self.original_window = self.driver.current_window_handle
                        
                        # 打开新标签页
                        self.driver.switch_to.new_window('tab')
                        self.driver.get(coin_new_weekly_url)

                        # 等待页面加载完成 - 使用显式等待代替time.sleep
                        try:
                            WebDriverWait(self.driver, 20).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                            # 使用短暂等待代替长时间sleep,等待 3 秒
                            for _ in range(30):  # 分成30次小等待，每次0.1秒
                                if self.stop_auto_find:
                                    break
                                time.sleep(0.1)

                        except Exception as e:
                            self.logger.error(f"等待页面加载失败: {str(e)}")

                        if self.trading == True:
                            self.logger.info("当前处于交易模式,不找币")
                            self.stop_auto_find_54_coin()
                            

                        # 获取Yes和No的价格
                        prices = self.driver.execute_script("""
                            function getPrices() {
                                const prices = {yes: null, no: null};
                                const elements = document.getElementsByTagName('span');
                                
                                for (let el of elements) {
                                    const text = el.textContent.trim();
                                    if (text.includes('Yes') && text.includes('¢')) {
                                        const match = text.match(/(\\d+\\.?\\d*)¢/);
                                        if (match) prices.yes = parseFloat(match[1]);
                                    }
                                    if (text.includes('No') && text.includes('¢')) {
                                        const match = text.match(/(\\d+\\.?\\d*)¢/);
                                        if (match) prices.no = parseFloat(match[1]);
                                    }
                                }
                                return prices;
                            }
                            return getPrices();
                        """)

                        if prices['yes'] is not None and prices['no'] is not None:
                            yes_price = float(prices['yes'])
                            no_price = float(prices['no'])

                        # 判断 YES 和 NO 价格是否在 48-56 之间
                        if (46 <= yes_price <= 56 or 46 <= no_price <= 56):
                            # 保存当前 URL 到 config
                            self.config['website']['url'] = coin_new_weekly_url
                            self.save_config()
                            self.logger.info(f"{coin}: YES{int(yes_price)}¢|NO{int(no_price)}¢✅ 符合要求,已保存到 config")
                            # 关闭当前页面
                            self.driver.close()
                            # 切换回原始窗口
                            self.driver.switch_to.window(self.original_window)
                            # 重启程序
                            self.restart_program()
                            return
                        else:
                            self.logger.info(f"{coin}: YES{int(yes_price)}¢|NO{int(no_price)}¢❌ 不符合要求")
                            # 关闭当前页面
                            self.driver.close()
                            # 切换回原始窗口
                            self.driver.switch_to.window(self.original_window)       
                    else:
                        self.logger.warning(f"未找到{coin}的周合约URL")
                except Exception as e:
                    self.logger.error(f"处理{coin}时出错: {str(e)}")
                    # 尝试恢复到原始窗口并继续下一个币种
                    try:
                        # 确保我们关闭了所有可能打开的新标签页
                        current_handles = self.driver.window_handles
                        for handle in current_handles:
                            if handle != self.original_window:
                                self.driver.switch_to.window(handle)
                                self.driver.close()
                        # 切换回原始窗口
                        self.driver.switch_to.window(self.original_window)
                    except Exception as inner_e:
                        self.logger.error(f"恢复窗口时出错: {str(inner_e)}")
                        # 如果无法恢复，可能需要重新创建浏览器会话
                        self._start_browser_monitoring(self.target_url)
                        break  # 中断循环，避免继续出错

        except Exception as e:
            self.logger.error(f"自动找币异常: {str(e)}")
            # 尝试重新初始化浏览器
            try:
                self._start_browser_monitoring(self.target_url)
            except Exception as browser_e:
                self.logger.error(f"重新初始化浏览器失败: {str(browser_e)}")
    
    def start_auto_find_54_coin(self):
        """启动自动寻找0.54币种线程"""
        if hasattr(self, 'auto_find_thread') and self.auto_find_thread is not None and self.auto_find_thread.is_alive():
            self.logger.info("auto_find_54_coin线程已在运行")
            return
            
        self.stop_auto_find = False  # 重置停止标志
        self.auto_find_thread = threading.Thread(target=self.auto_find_54_coin, daemon=True)
        self.auto_find_thread.start()
        self.logger.info("已启动auto_find_54_coin线程")

    def stop_auto_find_54_coin(self):
        """停止自动寻找0.54币种线程"""
        if hasattr(self, 'auto_find_thread') and self.auto_find_thread is not None and self.auto_find_thread.is_alive():
            self.logger.info("正在停止auto_find_54_coin线程")
            self.stop_auto_find = True
            
            # 取消所有待执行的定时器
            if hasattr(self, 'auto_find_timer') and self.auto_find_timer:
                self.root.after_cancel(self.auto_find_timer)
                self.auto_find_timer = None

            # 增加更强的线程停止机制
            start_time = time.time()
            max_wait_time = 8  # 最多等待8秒
            
            while hasattr(self, 'auto_find_running') and self.auto_find_running and time.time() - start_time < max_wait_time:
                self.logger.info("等待auto_find_54_coin停止...")
                time.sleep(0.5)  # 使用较短的等待时间
            
            if hasattr(self, 'auto_find_running') and self.auto_find_running:
                self.logger.warning("auto_find_54_coin未能在8秒内停止")
                self.auto_find_running = False  # 强制设置为已停止
            else:
                self.logger.info("auto_find_54_coin已停止")
        else:
            self.logger.info("auto_find_54_coin未运行")

    #-----------------以上是自动找 54 币的函数-----------------
    def _find_element_with_retry(self, xpaths, timeout=10, silent=False):
        """优化版XPATH元素查找(增强空值处理)"""
        try:
            for i, xpath in enumerate(xpaths, 1):
                try:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    return element
                except TimeoutException:
                    if not silent:
                        self.logger.warning(f"第{i}个XPATH定位超时: {xpath}")
                    continue
        except Exception as e:
            if not silent:
                raise
        return None

if __name__ == "__main__":
    try:
        # 打印启动参数，用于调试
        print("启动参数:", sys.argv)
        
        # 初始化日志
        logger = Logger("main")
        logger.info(f"程序启动，参数: {sys.argv}")
        
        # 检查是否是重启模式
        is_restart = '--restart' in sys.argv
        if is_restart:
            logger.info("检测到--restart参数")
            
        # 创建并运行主程序
        app = CryptoTrader()
        app.root.mainloop()
        
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        if 'logger' in locals():
            logger.error(f"程序启动失败: {str(e)}")
        sys.exit(1)
    
