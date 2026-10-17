# 安装与客户端接入

## 1. 环境准备

目前实际验证的是 Windows、Zotero 10.0.6 和 Python 3.12 系列环境。检查：

```powershell
python --version
git --version
```

选择一个长期保留的项目目录。移动项目或解释器后，需要重新生成并更新客户端配置中的绝对路径。以下 `python` 应替换成你实际使用的解释器；PowerShell 调用带空格的绝对路径时使用 `& '完整路径\python.exe'`。

```powershell
git clone https://github.com/z3271317085-star/agent-reader-bridge.git
cd agent-reader-bridge
python -m pip install --target vendor -r requirements-lock.txt
```

依赖锁文件来自已验证的 Windows 环境，包含 Windows 专用依赖。其他平台不可直接视为已支持；包版本不可用或 Python ABI 不兼容时，应先解决依赖问题，不要仅安装任意 MCP 版本，因为服务使用 MCP 2.3.0 的接口。

## 2. 本机构建和配对

```powershell
python -B build.py
```

构建结果：

| 文件 | 用途 |
|---|---|
| `runtime.json` | Python 服务的配对凭证，存在时复用 |
| `plugin/secret.js` | 插件配对凭证，由构建脚本生成 |
| `dist/agent-reader-bridge-0.1.3.xpi` | 安装至当前机器 Zotero 的插件 |
| `dist/codex-config.toml` | Codex MCP 配置片段 |
| `dist/agent-config.json` | 通用 MCP 客户端配置示例 |
| `dist/SHA256SUMS.txt` | 当前构建包校验值 |

生成的客户端命令使用运行 `build.py` 的 Python 解释器。XPI 与 runtime.json 必须配套；不要安装其他机器的配对包。重复构建会复用现有令牌。重新配对时先安全备份旧文件，再移走 runtime.json、重新构建并同时更新 Zotero 插件。

## 3. 安装 Zotero 插件

1. 打开 Zotero 10。
2. 打开“工具 → 插件”。
3. 点击齿轮，选择“从文件安装插件”。
4. 选择本机 `dist/agent-reader-bridge-0.1.3.xpi`。
5. 确认插件已启用，必要时重启 Zotero，然后打开一份 PDF。

插件使用自身认证端点，不要求打开 Zotero 常规 `/api` 功能。默认使用回环地址 `127.0.0.1:23119`，不提供外网监听或隧道。

当前没有自动更新服务器。清单使用 HTTPS 回环更新地址以满足 Zotero 10 安装要求，但本项目不在该地址提供 HTTPS 服务；更新检查可能连接失败。升级采用手动安装新配对包，不需要关闭 Zotero 安全检查或安装证书。

## 4. 接入 Codex

将构建产生的 `dist/codex-config.toml` 合并到你使用的 Codex MCP 配置中，保留其他已有服务器。结构示例：

```toml
[mcp_servers.zotero_reader]
command = 'C:\path\to\python.exe'
args = ['-B', 'C:\path\to\agent-reader-bridge\server.py']
startup_timeout_sec = 30
tool_timeout_sec = 90

[mcp_servers.zotero_reader.env]
PYTHONDONTWRITEBYTECODE = "1"
```

上面的路径只是占位示例，优先复制构建产物中的真实路径。配置放在哪个作用域，决定哪些项目和聊天可用。项目级配置还需被客户端信任并加载；不会自动覆盖所有其他工作区。

在 MCP 设置中确认 `zotero_reader` 已连接。若已有聊天尚未出现工具，完全退出并重启 Codex，再回到原对话，发送：

> 调用 zotero_reader 的 get_reading_context，告诉我当前论文标题、物理页码和选中文字。然后用返回的 snapshot_id 读取相关页。

本项目不依赖 Codex 的聊天注入接口，因此无需新建独立聊天窗口。已有聊天的历史保留和模型可见范围由 Codex 自身管理。

## 5. 接入 WorkBuddy 和其他 Agent

使用客户端提供的自定义 MCP 入口，导入 `dist/agent-config.json`，或按界面填写：

```json
{
  "mcpServers": {
    "zotero_reader": {
      "command": "C:\\path\\to\\python.exe",
      "args": ["-B", "C:\\path\\to\\agent-reader-bridge\\server.py"],
      "env": {"PYTHONDONTWRITEBYTECODE": "1"}
    }
  }
}
```

传输类型选择本地 `stdio`。不同客户端的外层配置结构和存放位置可能不同，不要盲目覆盖原配置。

WorkBuddy 国际版测试中使用了用户配置目录下的 `mcp.json`，但具体目录由产品版本与配置环境决定。启用并确认客户端自身的信任授权后，检查四项工具是否出现。关闭窗口可能仅最小化到托盘；需要重新加载时应使用“退出 / Quit”。

桌面版与 CLI、CCB 桥接的配置和登录可能相互独立。桌面已启用 MCP 不代表 CLI 自动可见；CLI 应显式加载同一份 `--mcp-config`。WorkBuddy 的延迟工具转发器在非交互执行中还可能需要额外权限，不能把“已连接”或模型输出 success 当成实际调用通过。不要因此修改全局免确认设置；优先交互授权并核对实际工具结果。

其他 Agent 只需支持本地 STDIO MCP。页面图片还需要客户端与模型支持图像工具结果。纯云端 Agent 若不能运行本机进程，不能直接访问此服务。

## 6. 验证链路

先在 Zotero 打开 PDF，然后执行：

```powershell
python -B -X utf8 server.py --context
python -B -X utf8 probe_mcp.py --pages
```

第一个命令检查插件认证和当前上下文；第二个通过真实 MCP SDK 子进程读取上下文与页面。不要把诊断进程产生的 snapshot_id 交给另一个进程使用。

最后在目标 Agent 中实际提问，并查看工具调用记录。这一步才验证客户端接入成功。常规启动 `server.py` 时使用 STDIO 协议，不能向它的 stdout 注入调试文本。
