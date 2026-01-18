#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单的GUI测试脚本"""

import sys

try:
    import tkinter as tk
    print("✓ tkinter 可用")
    
    root = tk.Tk()
    root.title("GUI测试")
    root.geometry("400x300")
    
    label = tk.Label(root, text="GUI测试成功！\n如果看到这个窗口，说明GUI可以正常工作。", 
                     font=("Arial", 14), justify="center")
    label.pack(expand=True)
    
    button = tk.Button(root, text="关闭", command=root.quit)
    button.pack(pady=20)
    
    print("✓ GUI窗口已创建")
    print("请检查是否有窗口弹出...")
    
    root.mainloop()
    print("✓ GUI测试完成")
    
except ImportError as e:
    print(f"✗ tkinter 不可用: {e}")
    print("请安装 tkinter: pip install tk")
    sys.exit(1)
except Exception as e:
    print(f"✗ GUI启动失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
