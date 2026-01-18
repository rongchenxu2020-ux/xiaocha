#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单流机器人GUI监控工具
实时监控所有运行的订单流机器人及其交易信号
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import csv
import glob
import psutil
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import threading


class BotMonitor:
    """机器人监控器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / "logs"
        self.bot_processes = {}
        self.signal_files = {}
    
    def find_bot_processes(self) -> List[Dict]:
        """查找所有运行的订单流机器人进程"""
        bots = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('run_orderflow_bot' in str(cmd) or 'run_market_maker_bot' in str(cmd) or 'run_sol_orderflow_bot' in str(cmd) for cmd in cmdline):
                        # 解析命令行参数
                        ticker = 'UNKNOWN'
                        exchange = 'UNKNOWN'
                        mode = 'UNKNOWN'
                        
                        for i, arg in enumerate(cmdline):
                            if arg == '--ticker' and i + 1 < len(cmdline):
                                ticker = cmdline[i + 1]
                            elif arg == '--exchange' and i + 1 < len(cmdline):
                                exchange = cmdline[i + 1]
                            elif arg == '--simulate':
                                mode = '模拟模式'
                            elif '--ticker' not in cmdline and '--exchange' not in cmdline:
                                # 尝试从路径推断
                                if 'edgex' in str(cmdline):
                                    exchange = 'edgex'
                        
                        if '--simulate' not in cmdline:
                            mode = '真实交易'
                        
                        create_time = datetime.fromtimestamp(proc.info['create_time'])
                        runtime = datetime.now() - create_time
                        
                        bots.append({
                            'pid': proc.info['pid'],
                            'ticker': ticker,
                            'exchange': exchange,
                            'mode': mode,
                            'runtime': runtime,
                            'process': proc
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return bots
    
    def get_signals_for_ticker(self, exchange: str, ticker: str, mode: str) -> Dict:
        """获取指定交易对的信号统计"""
        # 查找信号文件（支持订单流和做市商两种格式）
        mode_text = 'simulate' if '模拟' in mode else 'live'
        
        # 先查找做市商信号文件
        pattern = f"market_maker_signals_{exchange}_{ticker}_{mode_text}_*.csv"
        signal_files = list(self.logs_dir.glob(pattern))
        
        # 如果没有找到，查找订单流信号文件
        if not signal_files:
            pattern = f"orderflow_signals_{exchange}_{ticker}_{mode_text}_*.csv"
            signal_files = list(self.logs_dir.glob(pattern))
        
        if not signal_files:
            return {
                'total': 0,
                'confirmed': 0,
                'buy': 0,
                'sell': 0,
                'latest_signals': [],
                'file_exists': False
            }
        
        # 使用最新的文件
        latest_file = max(signal_files, key=lambda f: f.stat().st_mtime)
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                signals = list(reader)
            
            total = len(signals)
            
            # 检查是订单流格式还是做市商格式
            if signals and 'Bid Price' in signals[0]:
                # 做市商格式：Bid Price, Ask Price, Mid Price, Spread, Position, Buy Order ID, Sell Order ID, Status
                confirmed = len([s for s in signals if s.get('Status', '') == 'ACTIVE'])
                buy = len([s for s in signals if s.get('Buy Order ID', '') and s.get('Buy Order ID', '') != ''])
                sell = len([s for s in signals if s.get('Sell Order ID', '') and s.get('Sell Order ID', '') != ''])
            else:
                # 订单流格式：Direction, Price, Strength, etc.
                confirmed = len([s for s in signals if s.get('Confirmed', '') == 'YES'])
                buy = len([s for s in signals if s.get('Direction', '') == 'BUY'])
                sell = len([s for s in signals if s.get('Direction', '') == 'SELL'])
            
            # 获取最新5个信号
            latest_signals = signals[-5:] if len(signals) > 5 else signals
            latest_signals.reverse()  # 最新的在前
            
            return {
                'total': total,
                'confirmed': confirmed,
                'buy': buy,
                'sell': sell,
                'latest_signals': latest_signals,
                'file_exists': True,
                'file_path': str(latest_file)
            }
        except Exception as e:
            return {
                'total': 0,
                'confirmed': 0,
                'buy': 0,
                'sell': 0,
                'latest_signals': [],
                'file_exists': True,
                'error': str(e)
            }


class BotMonitorGUI:
    """机器人监控GUI界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("做市商/订单流机器人监控中心")
        self.root.geometry("1200x800")
        
        self.monitor = BotMonitor()
        self.update_interval = 3  # 3秒更新一次
        
        self.setup_ui()
        self.start_monitoring()
    
    def setup_ui(self):
        """设置UI界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="做市商/订单流机器人监控中心", 
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # 创建Notebook（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 机器人列表标签页
        self.bots_frame = ttk.Frame(notebook, padding="10")
        notebook.add(self.bots_frame, text="机器人状态")
        self.setup_bots_tab()
        
        # 信号监控标签页
        self.signals_frame = ttk.Frame(notebook, padding="10")
        notebook.add(self.signals_frame, text="交易信号")
        self.setup_signals_tab()
        
        # 状态栏
        self.status_label = ttk.Label(
            main_frame, 
            text="准备就绪", 
            relief=tk.SUNKEN
        )
        self.status_label.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=(10, 0))
        
        ttk.Button(
            button_frame, 
            text="立即刷新", 
            command=self.update_display
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="打开日志目录", 
            command=self.open_logs_dir
        ).pack(side=tk.LEFT, padx=5)
    
    def setup_bots_tab(self):
        """设置机器人状态标签页"""
        # 机器人列表框架
        list_frame = ttk.Frame(self.bots_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview
        columns = ('PID', '交易所', '交易对', '模式', '运行时长', '信号总数', '买入', '卖出', '已确认')
        self.bots_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # 设置列标题和宽度
        column_widths = {
            'PID': 80,
            '交易所': 100,
            '交易对': 100,
            '模式': 100,
            '运行时长': 120,
            '信号总数': 100,
            '买入': 80,
            '卖出': 80,
            '已确认': 80
        }
        
        for col in columns:
            self.bots_tree.heading(col, text=col)
            self.bots_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.bots_tree.yview)
        self.bots_tree.configure(yscrollcommand=scrollbar.set)
        
        self.bots_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 双击查看详情
        self.bots_tree.bind('<Double-1>', self.show_bot_details)
    
    def setup_signals_tab(self):
        """设置交易信号标签页"""
        # 信号显示区域
        self.signals_text = scrolledtext.ScrolledText(
            self.signals_frame, 
            wrap=tk.WORD, 
            height=30,
            font=("Consolas", 10)
        )
        self.signals_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置文本颜色标签
        self.signals_text.tag_config("buy", foreground="green", font=("Consolas", 10, "bold"))
        self.signals_text.tag_config("sell", foreground="red", font=("Consolas", 10, "bold"))
        self.signals_text.tag_config("confirmed", foreground="blue", font=("Consolas", 10, "bold"))
        self.signals_text.tag_config("header", font=("Consolas", 11, "bold"))
    
    def update_display(self):
        """更新显示"""
        try:
            # 更新机器人列表
            self.update_bots_list()
            
            # 更新信号显示
            self.update_signals_display()
            
            # 更新状态栏
            self.status_label.config(
                text=f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            self.status_label.config(text=f"更新错误: {str(e)}")
    
    def update_bots_list(self):
        """更新机器人列表"""
        # 清空现有项
        for item in self.bots_tree.get_children():
            self.bots_tree.delete(item)
        
        # 获取所有机器人
        bots = self.monitor.find_bot_processes()
        
        if not bots:
            self.bots_tree.insert('', 'end', values=('', '无', '运行的机器人', '', '', '', '', '', ''))
            return
        
        # 添加每个机器人
        for bot in bots:
            signals = self.monitor.get_signals_for_ticker(
                bot['exchange'], 
                bot['ticker'], 
                bot['mode']
            )
            
            # 格式化运行时长
            runtime = bot['runtime']
            if runtime.days > 0:
                runtime_str = f"{runtime.days}天 {runtime.seconds//3600}小时"
            elif runtime.seconds >= 3600:
                runtime_str = f"{runtime.seconds//3600}小时 {runtime.seconds%3600//60}分钟"
            else:
                runtime_str = f"{runtime.seconds//60}分钟"
            
            values = (
                bot['pid'],
                bot['exchange'].upper(),
                bot['ticker'],
                bot['mode'],
                runtime_str,
                signals['total'],
                signals['buy'],
                signals['sell'],
                signals['confirmed']
            )
            
            item = self.bots_tree.insert('', 'end', values=values)
            
            # 如果有买入信号，高亮显示
            if signals['buy'] > 0:
                self.bots_tree.set(item, '买入', f"🟢 {signals['buy']}")
    
    def update_signals_display(self):
        """更新信号显示"""
        self.signals_text.delete(1.0, tk.END)
        
        bots = self.monitor.find_bot_processes()
        
        if not bots:
            self.signals_text.insert(tk.END, "暂无运行的机器人\n", "header")
            return
        
        for bot in bots:
            signals = self.monitor.get_signals_for_ticker(
                bot['exchange'], 
                bot['ticker'], 
                bot['mode']
            )
            
            # 机器人标题
            header = f"\n{'='*80}\n"
            header += f"机器人: {bot['exchange'].upper()} - {bot['ticker']} ({bot['mode']})\n"
            header += f"进程ID: {bot['pid']} | 运行时长: {bot['runtime']}\n"
            header += f"信号统计: 总数={signals['total']} | 买入={signals['buy']} | 卖出={signals['sell']} | 已确认={signals['confirmed']}\n"
            header += f"{'='*80}\n\n"
            
            self.signals_text.insert(tk.END, header, "header")
            
            # 显示最新信号
            if signals['latest_signals']:
                for signal in signals['latest_signals']:
                    # 检查是订单流格式还是做市商格式
                    if 'Bid Price' in signal:
                        # 做市商格式
                        timestamp = signal.get('Timestamp', 'N/A')
                        bid_price = signal.get('Bid Price', 'N/A')
                        ask_price = signal.get('Ask Price', 'N/A')
                        mid_price = signal.get('Mid Price', 'N/A')
                        spread = signal.get('Spread', 'N/A')
                        position = signal.get('Position', '0')
                        buy_order_id = signal.get('Buy Order ID', '')
                        sell_order_id = signal.get('Sell Order ID', '')
                        status = signal.get('Status', 'N/A')
                        
                        signal_line = f"[{timestamp}] 做市商状态\n"
                        signal_line += f"  买单: {bid_price} | 卖单: {ask_price}\n"
                        signal_line += f"  中间价: {mid_price} | 价差: {spread}\n"
                        signal_line += f"  持仓: {position} | 状态: {status}\n"
                        if buy_order_id:
                            signal_line += f"  买单ID: {buy_order_id}\n"
                        if sell_order_id:
                            signal_line += f"  卖单ID: {sell_order_id}\n"
                        signal_line += "\n"
                        
                        # 做市商信号用蓝色显示
                        self.signals_text.insert(tk.END, signal_line, "confirmed")
                    else:
                        # 订单流格式
                        direction = signal.get('Direction', '')
                        price = signal.get('Price', 'N/A')
                        strength = signal.get('Strength', '0')
                        timestamp = signal.get('Timestamp', 'N/A')
                        reason = signal.get('Reason', '')
                        status = signal.get('Status', '')
                        confirmed = signal.get('Confirmed', 'NO')
                        
                        # 格式化信号信息
                        signal_line = f"[{timestamp}] {direction} @ {price}\n"
                        signal_line += f"  强度: {float(strength)*100:.2f}% | 状态: {status}\n"
                        signal_line += f"  原因: {reason}\n"
                        signal_line += f"  确认: {'是' if confirmed == 'YES' else '否'}\n\n"
                        
                        # 根据方向设置颜色
                        tag = "buy" if direction == "BUY" else "sell"
                        if confirmed == "YES":
                            tag = "confirmed"
                        
                        self.signals_text.insert(tk.END, signal_line, tag)
            else:
                self.signals_text.insert(tk.END, "  暂无信号\n\n")
    
    def show_bot_details(self, event):
        """显示机器人详情"""
        selection = self.bots_tree.selection()
        if not selection:
            return
        
        item = self.bots_tree.item(selection[0])
        values = item['values']
        
        if not values or values[0] == '':
            return
        
        pid = int(values[0])
        ticker = values[2]
        exchange = values[1].lower()
        
        # 创建详情窗口
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"机器人详情 - {exchange.upper()} {ticker}")
        detail_window.geometry("800x600")
        
        # 显示详细信息
        detail_text = scrolledtext.ScrolledText(detail_window, wrap=tk.WORD)
        detail_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        signals = self.monitor.get_signals_for_ticker(exchange, ticker, values[3])
        
        info = f"机器人详情\n"
        info += f"{'='*60}\n\n"
        info += f"进程ID: {pid}\n"
        info += f"交易所: {exchange.upper()}\n"
        info += f"交易对: {ticker}\n"
        info += f"模式: {values[3]}\n"
        info += f"运行时长: {values[4]}\n\n"
        info += f"信号统计:\n"
        info += f"  总数: {signals['total']}\n"
        info += f"  买入: {signals['buy']}\n"
        info += f"  卖出: {signals['sell']}\n"
        info += f"  已确认: {signals['confirmed']}\n\n"
        
        if signals.get('file_path'):
            info += f"信号文件: {signals['file_path']}\n\n"
        
        detail_text.insert(1.0, info)
    
    def open_logs_dir(self):
        """打开日志目录"""
        import subprocess
        import platform
        
        logs_path = self.monitor.logs_dir
        
        if platform.system() == 'Windows':
            os.startfile(str(logs_path))
        elif platform.system() == 'Darwin':  # macOS
            subprocess.Popen(['open', str(logs_path)])
        else:  # Linux
            subprocess.Popen(['xdg-open', str(logs_path)])
    
    def start_monitoring(self):
        """开始监控"""
        self.update_display()
        # 设置定时更新
        self.root.after(self.update_interval * 1000, self.start_monitoring)


def main():
    """主函数"""
    root = tk.Tk()
    app = BotMonitorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
