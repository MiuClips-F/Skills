---
name: python-requests
description: 根据已登录浏览器中的真实操作链生成简洁 Python requests 脚本。优先用 chrome-devtools-mcp 附着用户已打开的 Chrome 标签页抓包；如果 MCP 只能提供受管新浏览器、about:blank、独立会话或请求元数据不足，才改走直接 CDP 附着，仍失败则停止。适用于逆向 Web 接口、复刻页面操作、分析 headers/cookies/tokens/pagination/downloads、签名参数和生成按 Ponytail 收敛的少文件少函数 requests 脚本。
---

# Python Requests

将用户已登录浏览器中的真实页面操作链，整理成可复测、可维护、结构直接的 Python `requests` 脚本。抓包工具只用于分析阶段；最终交付脚本必须剥离 chrome-devtools-mcp、CloakBrowser、Scrapling、CDP、9222、HAR 捕获和页面自动化逻辑。

## 规则优先级

1. 以本 `SKILL.md` 为主规则。
2. 生成真实脚本前，必须阅读并执行 [`references/development-standards.md`](references/development-standards.md)。
3. 模板只作为默认骨架：[`references/main-template.py`](references/main-template.py)、[`references/field-mapping-template.json`](references/field-mapping-template.json)、[`references/task-state-template.json`](references/task-state-template.json)。
4. 交付前可运行 [`scripts/validate_generated_script.py`](scripts/validate_generated_script.py) 检查 Ponytail 和 CDP/MCP 泄漏。

如果文件之间冲突，以本文件为准。

## 核心链路

### 1. Session Attach

- 先判断任务是复用“用户当前已登录页面”，还是新建受控浏览器会话。
- 复用当前页面时，优先用 chrome-devtools-mcp 读取现有 Chrome 页面列表并匹配目标标签页。
- 只有 MCP 路径失败、只能看到受管 `about:blank`/空白页/独立会话，或拿不到足够请求元数据时，才检查 `http://127.0.0.1:9222/json` 或 `/json/version` 并改走直接 CDP。
- 直接 CDP 仍无法附着到用户已有标签页时，立即停止并说明阻塞原因。
- 禁止通过 `new_page`、重新导航空白页、重新登录站点或新起 Chrome 来“补救”当前页面附着失败。

### 2. Network Capture

- 只在确认附着到目标已有标签页后执行用户描述的点击、填写、筛选、导出、翻页等操作。
- 接管执行操作前开启网络捕获，操作完成后再停止捕获并筛选业务请求。
- 保留请求方法、URL、query、body、headers、响应状态、响应体、跳转、下载地址和关键时序。
- 忽略埋点、日志、静态资源和普通 `OPTIONS`，除非它们揭示必要鉴权头。

### 3. Request Chain Analysis

- 区分初始化、鉴权、token 刷新、业务接口、分页接口、详情接口、导出接口、任务轮询和下载接口。
- 找出后续请求依赖的前置 ID、credential、token、签名字段或短期下载 URL。
- 对动态字段判断来源：路由参数、前置响应、用户输入、时间戳、nonce、签名、加密 payload、租户/组织/店铺身份。
- 对响应设计确定性校验：数量、ID、日期范围、样例行、文件大小、后缀、checksum 或页面汇总对比。

### 4. Script Generation

- 最终脚本使用 `requests.Session`，每个请求设置明确 `timeout`，调用 `raise_for_status()` 并检查接口自己的 `success/code/msg`。
- cookie 默认由用户以字符串传入，不自动从浏览器读取。
- `if __name__ == "__main__"` 中集中传入 cookie、token、店铺、日期、分页、输出路径等实际运行参数；不要传 CDP 端口、`webSocketDebuggerUrl` 或页面接管参数。
- 表格导出才生成并读取独立 `field_mapping.json`；原始下载类请求只保存服务端返回的 `csv/xlsx/zip/pdf/binary` 文件，不生成字段映射。
- 输出表头必须使用页面显示表头和顺序，不能直接用 response 字段名当表头。

### 5. Verification

- 用浏览器结果或抓包结果校验脚本输出。
- 说明哪些认证参数由脚本生成、哪些来自前置接口、哪些需要用户提供。
- 核对重试只覆盖临时错误；认证、身份、权限、参数、验证码、MFA、风控错误直接抛出。
- 确认最终 `.py` 中没有 `cdp_debug_url`、`webSocketDebuggerUrl`、`127.0.0.1:9222`、`/json`、`/json/version`、MCP/CDP 接管逻辑。

## 认证硬约束

- 禁止通过 CDP `Runtime.evaluate`、JS 注入、读取 `localStorage`、`sessionStorage`、`document.cookie`、页面全局变量或直接调用前端现成函数，提取当前浏览器中已经存在的 `access_token`、refresh token、cookie、签名结果或其他认证参数作为最终依赖。
- 抓包目标是识别认证参数的来源、刷新方式、前置接口和生成规则，不是抄浏览器当前值。
- 可以分析 JS bundle、source map、请求前后参数差异来定位签名或加密算法；禁止借浏览器执行前端函数代算最终签名。
- 认证来源优先级固定为：还原登录/换票/刷新/签名/加密/挑战前置请求 -> 纳入前置接口返回 -> 用户显式传入 -> 用户明确允许时再用环境变量。
- 找不到可安全重放的认证链路时，退化为用户手动传入 cookie/token，并在最终说明中写清限制。

## Ponytail 输出门禁

Ponytail 在本 skill 中表示“最短可维护代码优先”：先判断代码是否需要存在，优先标准库和 `requests`，用最少文件、最少函数、最少状态完成当前需求。

默认交付形态：

- 1 个英文 `snake_case` 主脚本，例如 `platform_section_function.py`。
- 表格导出时额外生成 1 个 `field_mapping.json`；原始下载不生成。
- 默认至少包含 1 个明确业务 `class`，通常只保留 1 个业务类。
- 主逻辑默认收敛到 2 到 4 个主要方法；可保留 `update_headers()`、`fetch_*()`、`run()`，必要时才加 `build_*()` 或 `write_*()`。

默认禁止：

- 多个 `utils` 文件、通用客户端、插件体系、装饰器式抽象。
- `helper`、`client`、`service`、`factory` 这类只包一层的抽象。
- 面向“所有网站”的泛化框架、配置层、未来可能使用的文件。
- 把一次性参数机械挂到 `self`。

只有存在真实复用、独立认证/签名链、多子任务状态或明确业务边界时，才允许超过 1 个业务类、超过 4 个主要方法或新增独立模块。`self.xxx` 只保存跨方法长期状态，例如 `session`、字段映射、稳定配置；输出路径、筛选条件、分页值、payload 组成参数优先作为方法参数或局部变量。

## 文件与输出规则

- 表格文件名按 `数据抓取时间-业务日期-业务导出表名称.<suffix>`，例如 `20260616235435-20260615-已购客核心指标.csv`。
- 文件名不放店铺名、商品 ID、SKU、直播场次、账户等业务维度；这些字段写入文件内容。
- 爬取接口数据并重组表格时输出 UTF-8 CSV。
- 服务端原始下载文件按响应二进制原样保存，保留原始后缀。
- 大任务多子任务才使用 `task_state.json`，路径作为运行参数传入，不默认挂到 `self`。

## 最终答复

返回：

- 生成的 Python 文件路径。
- 表格导出场景的 `field_mapping.json` 路径。
- 必要请求链摘要，只列真正有用的端点。
- 必需运行参数和运行方式。
- 认证参数来源说明。
- 已执行验证和剩余限制。
