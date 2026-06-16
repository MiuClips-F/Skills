# Python Requests Skill

这个仓库保存 Codex 的 `python-requests` skill，用于把已经登录的浏览器真实操作链，整理成可复测、可维护的 Python `requests` 脚本。

核心目标不是从浏览器里复制一个现成 token，而是还原真实请求链：确认初始化、鉴权、分页、导出、下载、签名、加密参数的来源，并生成一个只包含业务运行所需参数的脚本。

## 目录结构

```text
python-requests/
  SKILL.md
  agents/
    openai.yaml
  references/
    development-standards.md
    field-mapping-template.json
    main-template.py
    task-state-template.json
```

- `SKILL.md`：skill 主规则，优先级最高。
- `agents/openai.yaml`：agent 入口提示，只负责提醒执行本 skill。
- `references/development-standards.md`：执行清单和交付前检查项。
- `references/main-template.py`：生成 requests 脚本时参考的主模板。
- `references/field-mapping-template.json`：表格导出场景的字段映射模板。
- `references/task-state-template.json`：大任务多子任务断点重跑的状态文件模板。

## 安装方式

把仓库里的 `python-requests` 目录复制到 Codex skills 目录。

Windows PowerShell 示例：

```powershell
Copy-Item -Recurse -Force .\python-requests "$env:USERPROFILE\.codex\skills\python-requests"
```

如果你的 Codex home 不在默认用户目录，请改成自己的 skills 路径：

```text
<CODEX_HOME>\skills\python-requests
```

安装后，在对话里使用：

```text
$python-requests 按当前页面抓包，生成 xxx 的 requests 脚本
```

## 使用前准备

本 skill 优先附着用户已经打开并登录好的 Chrome，要求 Chrome 开启远程调试端口 `9222`。

Windows PowerShell 示例：

```powershell
Start-Process "chrome.exe" -ArgumentList '--remote-debugging-port=9222'
```

如果需要指定独立用户目录，避免影响日常浏览器：

```powershell
Start-Process "chrome.exe" -ArgumentList "--remote-debugging-port=9222 --user-data-dir=$env:TEMP\chrome-cdp-profile"
```

然后在这个 Chrome 里登录目标系统，打开需要抓包的目标页面。

## 标准操作步骤

1. 打开已登录的目标页面。
2. 确认 Chrome 调试端口可访问：`http://127.0.0.1:9222/json/version`。
3. 在对话里说明清楚操作路径、筛选条件、时间范围、导出格式和成功标准。
4. 使用 `$python-requests` 发起任务。
5. skill 先确认是否附着到已有 Chrome 标签页。
6. 围绕用户描述的操作开始抓包。
7. 执行页面点击、筛选、分页、导出或下载操作。
8. 梳理请求链，去掉埋点、静态资源、无关日志和普通预检请求。
9. 还原最小必要请求链，生成 Python `requests.Session` 脚本。
10. 用页面结果校验脚本输出。

## 输入要求

发起任务时尽量说明这些信息：

- 目标页面或系统名称。
- 当前页面 URL 或页面标题。
- 具体操作路径，例如搜索、筛选、点击详情、导出。
- 店铺、账号、项目、组织、租户等业务对象。
- 日期范围、分页大小、排序方式。
- 输出格式，例如原始下载文件、CSV、Excel、JSON。
- 成功标准，例如文件存在、记录数一致、样例行一致。

示例：

```text
$python-requests 当前页面是商品明细，筛选 2026-06-12，点击导出，把下载链整理成 Python requests 脚本。
```

## 抓包规则

- 只接管已经打开的 Chrome 和已有标签页。
- 必须先检查 `127.0.0.1:9222` 是否可用。
- 如果页面工具只看到 `about:blank`、空白页或受管新会话，不能把它当成用户当前页面。
- 遇到受管新会话时，必须改走直接 CDP 附着。
- 如果直接 CDP 也无法附着，就停止并说明阻塞原因。
- 禁止为了抓包而新开浏览器、重新登录或用空白页重新导航目标站点。
- CDP 和 9222 只用于分析阶段，最终交付脚本不能包含这些调试参数。

## 浏览器接入口策略

入口优先级按任务场景判断，不使用全局固定顺序。

接管浏览器的目的，是执行用户描述的页面操作并同步监听 Network/HAR/Fetch/XHR，从而定位真实接口、参数来源和请求时序。接管不是最终运行方案；最终脚本必须回落到 Python `requests`，不保留 CloakBrowser、Scrapling、CDP、MCP、9222 或页面自动化逻辑。

复用当前已登录页面：

1. 已有 Chrome/CDP。
2. 能暴露同一用户 profile、目标标签页或可验证登录态的 CloakBrowser。
3. 停止并说明无法复用当前会话。

新建受控浏览器会话：

1. CloakBrowser。
2. Scrapling。
3. 普通 CDP 或浏览器路径。

Scrapling 更适合不依赖当前真实标签页的抓取、动态渲染和用户显式传入认证参数的场景。只要 CloakBrowser 或 Scrapling 启动的是新会话，就不能声称已经接管了用户当前页面。

任何接管入口用于接口定位时，最低必须能输出请求方法、URL、query、body、headers、响应状态、响应体或下载链。如果只能渲染页面但不能可靠输出请求链，只能作为页面观察辅助，不能作为接口定位主入口。

## 认证规则

- 禁止把浏览器当前已有的 token、cookie、签名结果直接读出来当成最终方案。
- 抓包的目标是识别认证参数来源，而不是复制现成值。
- 认证来源优先级：
  1. 还原登录、换票、刷新、签名、加密或挑战前置请求。
  2. 如果参数来自前置接口，把前置接口纳入请求链。
  3. 如果无法安全重放，改为用户显式传入。
  4. 只有用户明确允许时，才使用环境变量或 `.env`。
- cookie 默认由用户以字符串形式传入，不自动从浏览器读取。

## 输出规则

表格重组导出场景：

- 生成 `platform_section_function.py` 这类英文 `snake_case` 脚本。
- 生成独立 `field_mapping.json`。
- 表头使用页面前台显示名称。
- 表头顺序与页面一致。
- 数据日期、店铺 ID、店铺名、商品 ID、SKU、商品名称、直播间名称、直播场次 ID、账户名、账户 ID 等关键字段，只要当前业务存在，就必须写入文件内容，不能只写在文件名或目录名中。
- 脚本运行时读取独立字段映射文件，不在 `.py` 里重复维护映射。
- 最终 CSV 文件名按 `<yyyyMMddHHmmss>-<业务导出表名称>.csv` 命名，`yyyyMMddHHmmss` 是数据抓取日期时间，并用 UTF-8 保存。
- 输出目录和完整输出文件路径都由参数传入，包括文件名本身；脚本不默认使用脚本同级 `output` 目录。

原始下载场景：

- 只保存服务端直接返回的 `csv`、`xlsx`、`zip`、`pdf` 或其他二进制文件。
- 不生成 `field_mapping.json`。
- 文件名同样使用 `<yyyyMMddHHmmss>-<业务导出表名称>`，但保留服务端原始后缀。
- 完整下载文件路径由参数传入，不在脚本内部按店铺或报表自行拼接。
- 校验文件名、原始后缀、大小或样例打开结果。

多采集任务场景：

- 同一脚本包含多个采集请求任务、多个报表或多个业务功能时，按请求任务或业务功能拆分多个输出文件。
- 任务状态记录必须保存每个子任务实际输出路径，下次重跑只跳过 `task_key + input_hash` 一致且输出存在的已完成任务。

## 代码风格

- 使用 `requests.Session`。
- 每个请求都设置明确 `timeout`。
- 调用 `raise_for_status()`，并检查接口自己的 `success`、`code`、`msg`。
- 只对临时错误做有限重试，不无限重试。
- 认证、身份、权限、参数、验证码和风控错误直接抛出。
- 多子任务采集时使用由参数传入的状态文件路径记录状态，下次重跑自动跳过已完成子任务。
- 生成脚本至少包含 1 个明确的 `class`。
- 每个函数和每个方法上方都写一句简短中文注释。
- 对应页面操作、接口请求、导出链路或子任务编排的类/方法注释要包含“操作步骤”和“访问网址”。
- 操作步骤写页面上点击哪里、选择哪里、如何筛选或导出才能触发该请求，用 `-` 分割。
- 访问网址写浏览器地址栏显示的页面 URL，不写接口 path 或 API URL。
- 没有外部访问网址的本地处理方法只写职责，不强行补 URL。
- 采集请求方法体开头要用三引号写参数注释，说明参数对应功能、类型、是否必填、格式或来源。
- 实际 `query`、`json`、`form data` 或分页参数构造前，也要用三引号写请求参数注释。
- 默认只保留 1 个业务 `class`。
- 遵守高内聚、低耦合原则，一个完整功能优先在一个方法内完成。
- 禁止抽离无关的小方法、通用 `utils`、通用 client 或插件式框架。
- `self.xxx` 只保存长期复用状态，例如 `session`、字段映射、稳定配置。
- 一次性参数，例如筛选条件、分页值、输出路径，直接作为方法参数或局部变量传递。
- 请求头优先定义为常量，并通过 `update_headers()` 统一更新会话头。

## 重试与断点重跑

单个请求的处理原则：

- 网络超时、连接断开、`408`、`429`、`500`、`502`、`503`、`504` 可以有限重试。
- 重试要设置最大次数、明确 `timeout` 和退避等待，默认不超过 3 次。
- 创建导出任务、提交任务这类 POST 请求，只有具备幂等键或能查重任务 ID 时才自动重试。
- `401`、`403`、未登录、未选身份、无权限、身份失效、参数错误、验证码、MFA、风控等直接抛出。
- “生成中、处理中、排队中”属于异步轮询，要设置最大等待时间。
- 接口成功但无数据不默认报错，除非页面或汇总接口明确显示应有数据。

大任务的处理原则：

- 一个大任务包含多个报表、店铺、日期分片或子采集脚本时，使用由参数传入的状态文件路径。
- 每个子任务使用稳定 `task_key`，并记录 `input_hash`。
- `success` 才算已完成，下次重跑同一 `task_key + input_hash` 且输出存在时自动跳过。
- `failed`、`partial`、`running`、`blocked` 都不算已完成，下次重跑默认重新尝试。
- 单个子任务失败时，记录错误并继续执行其他不依赖它的子任务。
- 全局认证、身份、权限或风控错误会影响所有子任务，应停止整个大任务。

## 常见问题

### 只能看到 about:blank 怎么办

这说明当前工具没有附着到用户已经打开的 Chrome 标签页。不要继续在这个空白页里导航目标站点，应切换到 `127.0.0.1:9222` 的直接 CDP 附着；如果仍失败，需要重新用 9222 启动 Chrome。

### 为什么不能自动读取 cookie

因为 skill 的目标是还原可维护请求链，而不是从浏览器偷取当前登录态。cookie 或短期 token 如果确实无法重放，应由用户显式提供。

### 什么时候生成 field_mapping.json

只有当脚本把接口响应重组为 CSV、Excel 或 JSON 表格时才生成。原始下载类请求不生成字段映射。

### 最终脚本里能保留 9222 吗

不能。9222、CDP、`/json`、`webSocketDebuggerUrl` 只属于抓包分析阶段，最终 Python requests 脚本不能包含这些逻辑。

## 交付检查

交付前至少确认：

- 是否真正附着到了已有 Chrome 标签页。
- 是否围绕用户指定操作抓包。
- 是否去掉了无关端点。
- 认证参数来源是否说明清楚。
- 表格导出是否按页面表头落表。
- 原始下载是否没有生成字段映射。
- 输出文件是否按 `<yyyyMMddHHmmss>-<业务导出表名称>` 命名，完整输出路径是否由参数传入，关键字段是否写入文件内容，爬取数据是否为 UTF-8 CSV，下载报表是否保留原后缀。
- 最终脚本是否移除了 CDP 和 9222 逻辑。
- 脚本输出是否与页面结果做过数量、样例行或文件级校验。
