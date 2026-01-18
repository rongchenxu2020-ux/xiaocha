# EDGEX WebSocket 连接错误诊断报告

## 错误现象

日志中持续出现以下错误：
```
[WS] connect error: failed to connect to WebSocket: Handshake status 400 None
```

## 可能原因分析

### 1. **SDK 包不匹配问题** ⚠️ **最可能的原因**

**发现的问题：**
- `requirements.txt` 中的 edgex SDK 安装配置：
  ```
  # (SDK installation URL removed)
  ```
- 但代码中导入的是：
  ```python
  from edgex_sdk import Client, WebSocketManager
  ```

**解决方案：**
1. 检查实际安装的包名：
   ```bash
   pip list | grep edgex
   ```
2. 如果包名是 `edgex-python-sdk`，需要修改导入语句：
   ```python
   from edgex_python_sdk import Client, WebSocketManager
   ```
   或者
   ```python
   from edgex_python_sdk.sdk import Client, WebSocketManager
   ```

### 2. **环境变量配置问题**

**检查项：**
- [ ] `EDGEX_ACCOUNT_ID` 是否设置为有效的数字ID
- [ ] `EDGEX_STARK_PRIVATE_KEY` 是否为正确的64字符十六进制私钥
- [ ] `.env` 文件是否在项目根目录
- [ ] 环境变量是否正确加载

**验证方法：**
```python
import os
from dotenv import load_dotenv
load_dotenv()

account_id = os.getenv('EDGEX_ACCOUNT_ID')
stark_key = os.getenv('EDGEX_STARK_PRIVATE_KEY')

print(f"Account ID: {account_id}")
print(f"Key length: {len(stark_key) if stark_key else 0}")
```

### 3. **API 密钥或权限问题**

HTTP 400 错误通常表示：
- API 密钥无效或已过期
- 账户没有 WebSocket 访问权限
- 账户ID与私钥不匹配

**检查方法：**
1. 登录 EDGEX 账户
2. 检查 API 管理页面
3. 确认密钥是否有效
4. 确认账户是否有足够的权限

### 4. **WebSocket URL 问题**

**当前配置：**
- `EDGEX_WS_URL=wss://quote.edgex.exchange`

**检查项：**
- [ ] URL 是否正确
- [ ] 是否需要不同的端点
- [ ] 是否需要额外的认证参数

### 5. **网络连接问题**

**检查方法：**
```python
import socket

def test_connection(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

# 测试连接
print("Base URL:", test_connection("pro.edgex.exchange", 443))
print("WS URL:", test_connection("quote.edgex.exchange", 443))
```

### 6. **SDK 版本兼容性问题**

**检查方法：**
```bash
pip show edgex-python-sdk
# 或
pip show edgex-sdk
```

**可能的问题：**
- SDK 版本过旧，不支持当前的 API
- SDK 版本过新，API 已变更
- Forked 版本与官方版本不兼容

## 诊断步骤

### 步骤 1: 检查已安装的包

```bash
pip list | grep -i edgex
```

### 步骤 2: 检查导入是否成功

创建测试文件 `test_import.py`:
```python
try:
    from edgex_sdk import Client, WebSocketManager
    print("✅ 导入成功: edgex_sdk")
except ImportError as e1:
    try:
        from edgex_python_sdk import Client, WebSocketManager
        print("✅ 导入成功: edgex_python_sdk")
    except ImportError as e2:
        print("❌ 导入失败")
        print(f"edgex_sdk 错误: {e1}")
        print(f"edgex_python_sdk 错误: {e2}")
```

### 步骤 3: 检查环境变量

运行 `check_websocket_config.py`:
```bash
python check_websocket_config.py
```

### 步骤 4: 测试 WebSocket 连接

创建测试文件 `test_websocket.py`:
```python
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# 尝试不同的导入方式
try:
    from edgex_sdk import WebSocketManager
except:
    try:
        from edgex_python_sdk import WebSocketManager
    except Exception as e:
        print(f"无法导入 WebSocketManager: {e}")
        exit(1)

account_id = os.getenv('EDGEX_ACCOUNT_ID')
stark_key = os.getenv('EDGEX_STARK_PRIVATE_KEY')
ws_url = os.getenv('EDGEX_WS_URL', 'wss://quote.edgex.exchange')

if not account_id or not stark_key:
    print("❌ 缺少必要的环境变量")
    exit(1)

try:
    ws_manager = WebSocketManager(
        base_url=ws_url,
        account_id=int(account_id),
        stark_pri_key=stark_key
    )
    print("✅ WebSocketManager 初始化成功")
    
    # 尝试连接
    print("尝试连接...")
    ws_manager.connect_private()
    print("✅ 连接成功！")
    
    # 等待几秒
    import time
    time.sleep(2)
    
    # 断开
    ws_manager.disconnect_private()
    print("✅ 已断开连接")
    
except Exception as e:
    print(f"❌ 连接失败: {e}")
    import traceback
    traceback.print_exc()
```

## 推荐的修复方案

### 方案 1: 修复 SDK 导入问题（如果存在）

如果实际安装的是 `edgex-python-sdk`，修改 `exchanges/edgex.py`:

```python
# 原代码
from edgex_sdk import Client, OrderSide, WebSocketManager, ...

# 修改为（根据实际包结构调整）
try:
    from edgex_sdk import Client, OrderSide, WebSocketManager, ...
except ImportError:
    from edgex_python_sdk import Client, OrderSide, WebSocketManager, ...
```

### 方案 2: 重新安装正确的 SDK

```bash
# 卸载现有版本
pip uninstall edgex-sdk edgex-python-sdk -y

# 安装 requirements.txt 中指定的版本
pip install -r requirements.txt
```

### 方案 3: 检查并更新环境变量

1. 确认 `.env` 文件存在
2. 确认所有必要的变量都已设置
3. 验证变量值是否正确

### 方案 4: 联系技术支持

如果以上方法都无效，可能需要：
1. 联系 EDGEX 技术支持
2. 检查 EDGEX 官方文档是否有 API 变更
3. 查看 EDGEX 状态页面确认服务是否正常

## 快速检查清单

- [ ] 运行 `python check_websocket_config.py` 检查配置
- [ ] 运行 `python test_import.py` 检查导入
- [ ] 运行 `python test_websocket.py` 测试连接
- [ ] 检查 `pip list | grep edgex` 确认安装的包
- [ ] 验证 `.env` 文件中的配置
- [ ] 检查网络连接
- [ ] 验证 API 密钥有效性

## 下一步

1. 运行诊断脚本收集信息
2. 根据诊断结果采取相应的修复措施
3. 如果问题持续，查看 EDGEX 官方文档或联系技术支持
