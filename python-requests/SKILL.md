---
name: python-requests
description: 根据已登录浏览器中的真实操作链生成简洁的 Python requests 脚本。优先通过 9222 端口附着用户已打开的 Chrome 和现有标签页做抓包与请求链分析；如果当前工具只能提供受管新浏览器、空白页或独立会话，必须改走直接 CDP 附着，仍无法附着时立即停止，不能把新打开的浏览器当成用户当前页面。适用于需要从现有浏览器会话逆向接口、复刻 Web 操作、分析 headers/cookies/tokens/pagination/downloads、抽取加密参数或生成请求脚本的任务。
---

# Python Requests

使用本 skill 将一段清晰的浏览器操作流程转成小而直接的 Python `requests` 脚本。优先复用用户已有 Chrome 会话中的真实请求链，但不要依赖脆弱的 UI 自动化，也不要直接把浏览器当前登录态里的现成认证参数“抄出来”当成最终方案。

CloakBrowser、Scrapling、MCP/CDP 只用于前期页面接管、抓包和请求链分析，最终交付的 Python 脚本不得包含任何浏览器接管、CDP 接管、9222 检查或浏览器调试参数。

如果当前可用浏览器工具只暴露受管新会话，例如页面列表里只有新的 `about:blank`、空白标签页，或必须调用 `new_page` 才能看到目标站点，视为“未附着到用户现有 Chrome”。此时不得继续把该受管会话当成当前页面，而要改走直接 `127.0.0.1:9222` 的 CDP 附着；如果仍无法附着，就停止并告知用户。

CloakBrowser、Scrapling 和 CDP 的优先级必须按任务场景判断，不能写成全局固定顺序。当前任务要求复用“用户已登录的当前页面”时，真实会话优先，先附着已有 Chrome/CDP；只有 CloakBrowser 明确暴露同一个用户已登录 profile、目标标签页或等价可验证会话时，才可作为该场景的接入口。当前任务要求新建受控浏览器、处理指纹敏感页面或先完成可授权登录时，优先尝试 CloakBrowser，其次尝试 Scrapling，最后再退回普通 CDP/浏览器路径。Scrapling 更适合无须复用当前真实标签页的抓取、动态渲染和用户显式传入认证参数的场景，不应被描述为“已接管当前页面”。

接管浏览器的目的，是执行用户描述的页面操作并同步监听 Network/HAR/Fetch/XHR，从而定位完成业务目标所需的真实接口、参数来源和请求时序。接管不是最终运行方案；最终脚本必须回落到 Python `requests`，并剥离 CloakBrowser、Scrapling、CDP、MCP、9222、HAR 捕获和页面自动化逻辑。

对象属性也要收敛：`self.xxx` 只保存跨多个方法复用的长期状态；某次调用才需要的输入值，应直接作为方法参数或局部变量传递，不要全部塞进对象属性。

## 规则优先级

1. 以本 `SKILL.md` 为主规则。
2. `references/development-standards.md` 只作为执行清单，不重新定义主策略。
3. `agents/openai.yaml` 只负责提醒 agent 执行本 skill，不单独创造与本文件冲突的规则。

如果三者有冲突，以本文件为准。

## 目标

目标不是“从浏览器里拿到一份能跑的现成 token”，而是：

- 还原真实业务请求链。
- 识别认证参数、分页参数、导出链、签名链的来源。
- 生成结构直接、可维护、可复测的 Python `requests` 脚本。
- 在需要把接口响应重组为表格导出时，按页面实际表头落表，并额外产出字段映射 JSON；如果只是复刻原始下载请求，则不保存字段映射表。

## 工作流程

1. 先判断任务属于“复用当前已登录页面”还是“新建受控浏览器会话”。复用当前页面时，优先连接已有 Chrome 的 `127.0.0.1:9222` 调试端口；新建受控会话时，按 CloakBrowser -> Scrapling -> 普通 CDP/浏览器路径尝试。
2. 复用当前页面时，先检查 `http://127.0.0.1:9222/json` 或 `http://127.0.0.1:9222/json/version` 是否可用，只接管已打开的浏览器和已有标签页，禁止新开浏览器或新起 Chrome 实例。
3. 确认目标标签页、当前 URL、登录状态，以及用户给出的图片或文字操作路径是否足够明确。
4. 先验证当前页面控制能力是否真的附着在该已有标签页上；如果只能看到新的 `about:blank`、空白受管页、独立会话，或需要新开页才能继续，立即停止使用该会话并改走直接 CDP 附着。
5. 仅在确认已附着到用户现有标签页后，再用可用的页面接管工具或直接 CDP 执行用户描述的操作。优先用页面快照定位元素，再执行点击、填写、上传、按键和等待。
6. 接管执行操作前先开启网络捕获；在每一步操作期间抓包，保留请求方法、URL、query、body、请求头、响应状态、响应体、跳转、下载地址和关键时序。
7. 梳理请求链，区分初始化、鉴权、token 刷新、预检噪声、业务接口、分页接口、详情接口、导出接口和下载接口。
8. 优先还原“可重复生成”的认证链路，再用 Python `requests.Session` 复刻最小必要业务链路，只保留必需 headers、cookies、token 和业务参数，并用浏览器结果校验。
9. 如果浏览器包里计算了 `sign`、`nonce`、`timestamp`、加密 payload、防重放 token 等动态字段，将加密或签名逻辑拆到独立模块。
10. 输出简洁脚本、运行说明、请求链摘要，以及按需的字段映射和验证结果。最终落地脚本只保留实际运行所需参数，不保留 CDP/MCP 接管逻辑。

## 输入清晰度

开始操作前要求用户描述足够具体。可接受两类输入：

- 文字路径，例如“打开账号管理，搜索用户 X，点击详情，切到使用记录，导出本月数据”。
- 图片或截图描述，需要说明可见控件、目标字段、页面状态和最终要产出的结果。

如果描述缺少目标页面、目标账号或对象、过滤条件、时间范围、导出格式或成功标准，先追问。不要猜测删除、禁用、付款、审批、提交等不可逆操作。

## Chrome 与抓包规则

- 优先附着 `127.0.0.1:9222` 对应的已有 Chrome 会话。只有在已经确认当前页面工具看到的就是该现有标签页时，才使用页面选择、快照、点击、填写、等待、控制台或网络检查、截图和下载确认。
- 如果当前页面工具显示的是受管新浏览器、孤立会话，或页面列表里只有新的 `about:blank`，不要把它当成目标页面；改走直接 `http://127.0.0.1:9222/json` 和匹配标签页的 `webSocketDebuggerUrl`。
- 如果直接 CDP 也无法附着到用户现有标签页，立即停止并说明无法接管当前会话；不要继续抓包，不要伪造“当前页面已就绪”的状态。
- 禁止通过 `new_page`、重新导航空白受管页、重新登录站点或新起 Chrome 的方式“补救”附着失败；这会把抓包对象变成新会话。
- CloakBrowser 接入口只在两类情况下使用：一是它能暴露用户指定的既有 profile、目标标签页或可验证登录态；二是用户明确要求从 CloakBrowser 新建受控会话。接入方式可以是本地 API、CLI、SDK、HAR 导出或其暴露的 DevTools/CDP 地址，但这些只属于分析阶段。
- CloakBrowser、Scrapling 或 CDP 若要作为接口定位入口，最低必须能完成页面操作接管，并暴露请求方法、URL、query、body、headers、响应状态、响应体或下载链；如果只能渲染页面但不能可靠输出请求链，只能作为页面观察辅助，不能作为接口定位主入口。
- Scrapling 接入口用于无需接管用户当前标签页的抓取或动态渲染场景。它可以作为新建受控会话的第二选择，但不能替代“当前已登录页面”的真实性校验；用于接口定位时，必须能提供足够的请求元数据或可复核的 HAR/Network 记录。
- 如果 CloakBrowser 或 Scrapling 启动的是新会话，必须明确标注为新会话，不得声称已经复用了用户当前页面；认证仍按用户显式输入、前置接口或可还原链路处理。
- 上述 MCP/CDP 能力只用于分析阶段，禁止把 `cdp_debug_url`、`webSocketDebuggerUrl`、`127.0.0.1:9222`、`/json`、`/json/version` 或任何 CDP 命令写入最终交付脚本。
- 如果页面工具暴露不了完整请求头或请求体，改用 Chrome DevTools Protocol：访问 `http://127.0.0.1:9222/json`，附着匹配标签页的 `webSocketDebuggerUrl`。
- 必须先确认 9222 端口可用，再接管已有标签页。禁止为了抓包而新开浏览器。
- 必须围绕用户的具体操作抓包：先开始捕获，再执行操作，等待完成后停止捕获。
- 忽略普通 `OPTIONS` 预检请求，除非它揭示了必要的自定义鉴权头。
- 保留足够元数据，能解释每个请求为什么需要或为什么可以跳过。
- 最终答复中不要打印或硬编码长期有效密钥。优先使用用户输入、`if __name__ == "__main__"` 测试参数或带占位符的本地配置块。

## 会话判定与终止条件

- 以下信号可视为“已附着到用户现有 Chrome”：目标 URL、标题或标签页内容与用户当前页面一致；可见登录态与用户描述一致；不需要 `new_page` 或重新登录即可继续。
- 以下信号视为“未附着”：页面列表里只有新的 `about:blank` 或空白页；当前工具明显是独立受管浏览器；一旦操作就要求从首页重新打开站点或重新登录。
- 遇到“未附着”时，不要继续对该受管会话做点击、导航或抓包。先切换到直接 CDP 附着；仍失败则停止并向用户报告阻塞原因。

## 认证参数规则

这是本 skill 的硬约束：

- 禁止通过 CDP `Runtime.evaluate`、JS 注入、读取 `localStorage`、`sessionStorage`、`document.cookie`、页面全局变量或直接调用前端现成函数的方式，提取当前浏览器里已经存在的 `access_token`、refresh token、cookie、签名结果或其他认证参数，作为脚本最终依赖。
- 抓包的目的不是“抄现成 token”，而是识别认证参数的来源、刷新方式、前置接口和生成规则。
- 可以使用抓包结果确认字段名、字段位置和前置接口，但不能把浏览器当前值直接当成“算法”。
- 可以分析前端 JS bundle、source map、请求前后的参数差异，定位签名或加密算法。禁止直接借浏览器执行现成前端函数来代算最终签名。

认证来源优先级固定如下，后面的方案只有在前面的方案不可行时才使用：

1. 还原登录、换票、刷新 token、签名、加密、挑战前置请求。
2. 如果认证参数是前置接口返回的，直接把该前置接口纳入请求链。
3. 如果认证参数无法安全重放，但用户可明确提供，则改成用户传参。
4. 只有在用户明确允许且更适合时，才改成环境变量或 `.env`。

补充约束：

- cookie 默认由用户以字符串形式传入，不自动从浏览器读取。
- 如果必须依赖用户已有授权但无法安全还原，脚本应显式要求用户提供短期 token 或 cookie，而不是自动从浏览器偷取。
- 如果确实找不到可重放的认证链路，要在最终结果中明确说明，并退化为“用户手动传入 cookie 或 token”或“环境变量注入认证参数”的脚本形态。

## 请求分析

对每个候选接口判断：

- 它是否是完成业务目标所必需，还是埋点、配置、静态资源或无关日志。
- 哪些字段是动态的：路由参数、query、JSON body、form data、headers、cookies、CSRF、Bearer token、租户 ID、时间戳、nonce、签名或加密 payload。
- 哪个前置响应提供了后续请求所需的 ID、token、credential 或下载地址。
- 是否存在分页、排序、筛选、导出轮询、异步任务状态、短期签名下载 URL。
- 响应是否能用数量、ID、时间戳、文件存在性、checksum 或样例行做确定性校验。

## 重试、异常与任务状态

生成脚本必须区分“可重试临时错误”和“应立即抛出的确定性错误”，不要把所有异常都吞掉或无限重试。

重试规则：

- 仅对重复请求可能成功的状态做有限重试，例如网络超时、连接断开、`408`、`429`、`500`、`502`、`503`、`504`。
- 重试必须有最大次数、明确 `timeout` 和退避等待；默认 3 次以内，避免生产接口压力。
- 对可能创建任务、提交订单、触发导出任务的 POST 请求，只有在接口具备幂等键、可查重任务 ID，或先查询已有任务状态时才自动重试，避免重复创建。
- `401`、`403`、未登录、未选身份、无权限、身份失效、风控、验证码、MFA、参数错误、字段缺失等确定性错误不重试，直接抛出带上下文的异常。
- 异步导出中的“排队中、生成中、处理中”按轮询处理，不按普通异常重试；轮询必须设置最大等待时间。
- 接口成功但数据为空时，不默认当异常。只有页面或汇总接口明确显示有数据、而明细接口为空时，才抛出数据一致性异常。

异常内容必须带上足够定位信息：

- 子任务名或报表名
- 请求方法和 URL
- 关键业务参数，例如店铺、日期、页码、报表类型
- HTTP 状态码
- 接口自身的 `code`、`msg`、`success`
- 响应摘要，避免输出完整敏感响应

当一个大采集任务包含多个子采集脚本、多个报表、多个店铺或多个日期分片时，必须区分已完成任务和未完成任务：

- 每个子任务要生成稳定 `task_key`，建议由平台、账号或店铺、报表名、日期范围、分页/筛选参数组成。
- 每个子任务要记录输入指纹 `input_hash`，防止参数变化后误跳过旧结果。
- 子任务成功后记录为 `success`，并记录完成时间、输出文件、记录数、校验摘要；下次重跑同一大任务时，`task_key + input_hash` 一致且输出存在，应自动跳过。
- 子任务失败后记录为 `failed`，写入错误类型、错误信息、失败时间、是否可重试；当前大任务继续执行其他不依赖它的子任务。
- `running`、`partial`、`failed`、`blocked` 都不视为已完成；下次重跑默认重新尝试，除非用户显式要求跳过失败项。
- 如果错误是全局认证、身份、权限或风控问题，会影响所有子任务，应停止整个大任务并抛出全局异常，不要继续制造一批无效失败记录。
- 子任务状态文件默认使用 JSON，例如 `task_state.json`；状态文件属于运行产物，路径作为 `run()` 或 `main()` 参数传入，不默认保存到 `self`。
- 可参考 [`references/task-state-template.json`](references/task-state-template.json) 设计状态文件。不要把任务状态写死在 `.py` 常量里。

## 表头与落表规则

- 所有导出的表头必须按照页面上实际显示的前台表头落表，不允许直接使用 response 返回字段名作为 CSV、Excel 或 JSON 表头。
- 表头顺序必须与页面显示顺序一致。
- 如果页面存在隐藏列、固定列、“更多字段”、合并列或操作列，只输出用户当前要求范围内的业务列。
- 只有在脚本需要把接口响应重组为 CSV、Excel 或 JSON 表格时，才额外产出一个 `field_mapping.json`。
- 如果请求属于原始下载类，且脚本只是保存服务端直接返回的 `csv`、`xlsx`、`zip`、`pdf` 或其他二进制文件，则不生成也不保存 `field_mapping.json`。
- 表格导出场景下，`field_mapping.json` 必须作为独立文件存在，脚本运行时应直接读取该 JSON，而不是在 `.py` 里再维护一份重复映射常量。
- `field_mapping.json` 的基础格式为：

```json
{
  "前台显示名称": "response返回字段"
}
```

- JSON 键顺序应与页面表头顺序一致。
- 如果字段来自嵌套对象，映射值写成点路径，例如：

```json
{
  "店铺名称": "data.shop_name",
  "执行结果": "records.status_name"
}
```

- 如果页面显示字段是基于 response 字段二次计算或格式化得到的，映射 JSON 仍要保留原始来源，必要时允许写成：

```json
{
  "运行时长": "__derived__.run_time -> format_duration"
}
```

- 不能因为 response 恰好使用英文 key，就把英文 key 直接当成导出表头。
- 如果页面表头与 response 字段不能完全一一对应，必须在最终说明中写明差异原因。

## 生成脚本形态

生成的代码保持直接。默认脚本形态固定如下。

### 标准产物组合

最小交付组合：

- `platform_section_function.py`
- `field_mapping.json`，仅当脚本把接口响应重组为表格导出时才生成

如果脚本只是复刻原始下载接口并保存服务端文件：

- 不生成 `field_mapping.json`

如果采用目录交付而不是散文件交付：

- 目录名也必须使用英文 `snake_case`
- 目录内主脚本继续命名为英文 `snake_case`，例如 `platform_section_function.py`

按需增加：

- `auth.py`，只有认证链明显独立时才拆
- `crypto_params.py` 或 `signature.py`，只有签名或加密逻辑明显独立时才拆
- `requirements.txt`，只有依赖超出标准库和 `requests` 时才创建
- `.env.example`，只有用户明确要求或方案确实更适合时才创建
- `task_state.json`，只有一个大任务包含多个可独立完成的子任务，且需要断点重跑/跳过已完成任务时才作为运行产物创建

默认不要生成：

- 多个 `utils` 文件
- 通用客户端类
- 插件体系
- 装饰器式抽象
- 面向“所有网站”的泛化框架

新增硬约束：

- 生成的代码必须至少包含 1 个明确的 `class`
- 每个函数和每个方法上方都必须有一句简短注释，说明职责
- `class` 数量默认控制为 1 个，除非业务复杂到必须拆分
- `class` 只为组织当前脚本职责服务，不要演变成通用框架
- 遵守高内聚、低耦合原则：一个完整功能优先在一个方法内完成，禁止抽离无关的小方法。
- 最终生成的 `.py` 脚本中禁止出现 `cdp_debug_url`、`webSocketDebuggerUrl`、`127.0.0.1:9222`、`/json`、`/json/version` 或其他 CDP/MCP 接管逻辑
- `self.xxx` 只保存长期复用状态，例如 `session`、字段映射、稳定配置
- 某次方法调用才会使用的输入值，直接作为方法参数或局部变量传递，不要机械地全部挂到对象属性
- `csv_path`、`mapping_output_path`、`json_path` 这类一次性输出参数默认不要保存到 `self`
- 请求头默认写成常量，类内必须封装一个 `update_headers()` 或同类方法统一更新会话头

### 标准模板文件

生成脚本时，优先参考以下模板文件：

- [`references/main-template.py`](references/main-template.py)
- [`references/field-mapping-template.json`](references/field-mapping-template.json)，仅表格导出场景参考
- [`references/task-state-template.json`](references/task-state-template.json)，仅大任务多子任务断点重跑场景参考

如果生成结果与模板偏差较大，必须有明确业务理由，例如认证链独立、导出链复杂或字段派生明显。

### 主脚本骨架

`platform_section_function.py` 的标准结构应尽量接近下面这套骨架。下面示例适用于表格导出场景；原始下载类请求可省略 `field_mapping_path`、`mapping_output_path` 和表格写出逻辑，改为直接保存下载文件：

```python
from datetime import datetime
from pathlib import Path
import csv
import json
import requests


BASE_URL = "https://example.com"
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


class PlatformSectionFunctionExporter:
    # 初始化会话和字段映射。
    def __init__(self, cookie, field_mapping_path):
        self.field_mapping = json.loads(Path(field_mapping_path).read_text(encoding="utf-8"))
        self.session = requests.Session()
        self.update_headers(cookie=cookie)

    # 用常量请求头更新当前会话头。
    def update_headers(self, cookie, extra_headers=None):
        headers = dict(BASE_HEADERS)
        headers["Cookie"] = cookie
        if extra_headers:
            headers.update(extra_headers)
        self.session.headers.clear()
        self.session.headers.update(headers)

    # 分页抓取业务记录。
    def fetch_records(self, shop_name, start_date, end_date, page_size):
        records = []
        page = 1
        while True:
            response = self.session.post(
                f"{BASE_URL}/api/example",
                json={
                    "shopName": shop_name,
                    "startDate": start_date,
                    "endDate": end_date,
                    "page": page,
                    "size": page_size,
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("success") is not True:
                raise RuntimeError(payload)
            current = payload.get("data", {}).get("records", [])
            if not current:
                break
            records.extend(current)
            if len(current) < page_size:
                break
            page += 1
        return records

    # 把响应记录转换成页面展示行。
    def build_row(self, record):
        row = {}
        for header, source in self.field_mapping.items():
            row[header] = record.get(source, "")
        return row

    # 输出 CSV 和字段映射文件。
    def write_outputs(self, rows, csv_path, mapping_output_path):
        csv_path = Path(csv_path)
        mapping_output_path = Path(mapping_output_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        mapping_output_path.parent.mkdir(parents=True, exist_ok=True)

        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.field_mapping.keys()))
            writer.writeheader()
            writer.writerows(rows)

        mapping_output_path.write_text(
            json.dumps(self.field_mapping, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 串联抓取和写出主流程。
    def run(self, shop_name, start_date, end_date, page_size, csv_path, mapping_output_path):
        records = self.fetch_records(
            shop_name=shop_name,
            start_date=start_date,
            end_date=end_date,
            page_size=page_size,
        )
        rows = [self.build_row(record) for record in records]
        self.write_outputs(
            rows=rows,
            csv_path=csv_path,
            mapping_output_path=mapping_output_path,
        )


if __name__ == "__main__":
    cookie = "当前测试 cookie 字符串"
    shop_name = "当前抓包店铺"
    start_date = "2026-05-01"
    end_date = "2026-05-22"
    page_size = 100
    field_mapping_path = Path(__file__).with_name("field_mapping.json")
    file_stem = f"platform_section_function_{datetime.now():%Y%m%d_%H%M%S}"
    csv_path = Path(__file__).resolve().parent / "output" / f"{file_stem}.csv"
    mapping_output_path = Path(__file__).resolve().parent / "output" / "field_mapping.json"
    exporter = PlatformSectionFunctionExporter(
        cookie=cookie,
        field_mapping_path=field_mapping_path,
    )
    exporter.run(
        shop_name=shop_name,
        start_date=start_date,
        end_date=end_date,
        page_size=page_size,
        csv_path=csv_path,
        mapping_output_path=mapping_output_path,
    )
```

### 参数策略

1. 业务关键测试参数默认放在 `if __name__ == "__main__"` 中集中传入。
2. 关键参数包括但不限于：店铺、cookie、token、日期范围、分页大小、导出路径、输出文件名；只有表格导出场景才包含字段映射路径。
3. 当用户明确要求本地可直接测试时，应把当前抓包或当前页面使用的值整理为测试参数写在 `__main__` 中。
4. 文件名、输出路径这类动态参数也应写在 `__main__` 中，不要藏在函数内部临时生成；字段映射路径仅在表格导出场景加入。
5. 如果同一脚本还需要 token、credential、appKey、sign salt 等参数，要么在主流程中自行生成，要么也作为显式入参传入。
6. 命令行参数和环境变量是补充方案，不是默认主方案。
7. CDP、9222 端口、`/json` 探活地址和 `webSocketDebuggerUrl` 只允许出现在抓包分析说明中，不允许作为最终脚本入参。
8. `self.xxx` 只保存跨方法长期复用状态；当前这次运行才会消费的筛选条件、分页值、payload 组成参数，优先直接作为方法参数传递。
9. `csv_path`、`mapping_output_path`、`json_path` 这类输出路径参数默认放在 `run()`、`write_outputs()` 或对应方法入参里，不要先塞进 `self`。

### 字段映射模板

`field_mapping.json` 的标准模板应尽量接近下面这套格式。原始下载类请求不使用这个文件：

```json
{
  "店铺名称": "data.shop_name",
  "执行结果": "data.status_name",
  "执行时间": "data.execute_time",
  "运行时长": "__derived__.run_time -> format_duration"
}
```

补充要求：

- JSON 键顺序必须与页面表头顺序一致。
- 值优先写 response 字段路径。
- 如果前台字段来自多个 response 字段拼接或格式化，统一写成 `__derived__.source -> transform_name`。
- 如果存在重复表头，映射值中要写明列来源，不允许只保留一个模糊字段名。
- 如果页面有“操作”“详情”“按钮”这类非数据列，不写入 `field_mapping.json`。

### 允许的函数规模

为了避免过度抽象，默认允许的函数层级只有：

- `fetch_*`：负责请求接口
- `build_*`：负责把 response 转成页面行数据、签名参数或导出参数
- `write_*`：负责落表、落 JSON、落文件
- `update_headers()`：负责基于请求头常量刷新会话头
- `run()` 或 `main()`：串联主流程
- `run_task` 或 `run_subtasks`：仅当大任务需要按子任务状态跳过已完成项、记录失败项时使用

补充限制：

- 非必要不要额外拆 `helper`、`utils`、`client`、`service`。
- 默认保留 1 个清晰的业务 `class`，并把主要逻辑收敛到这个 `class` 的 2 到 4 个方法中。
- 能并到 `fetch_*`、`build_*`、`write_*`、`run()` 或 `main()` 的逻辑，就不要继续外拆。
- 一个功能只在一个方法内完成；只有出现真实复用、独立签名/加密链路或清晰业务边界时，才允许拆出新方法。
- 子任务状态读写优先收敛在主流程方法内；只有多个步骤真实复用状态写入逻辑时，才允许抽出一个清晰的 `write_task_state()` 或同类方法。
- 每个函数和每个方法上方都要有一句简短注释，解释职责，不要省略。
- `update_headers()` 属于允许保留的少量基础方法，不视为过度抽象。
- 不要为了“好看”把所有入参都先挂到 `self`，一次性调用值应保留为方法参数或局部变量。
- 输出路径也按一次性调用值处理，默认不要保存到对象属性。

## 加密模块规则

只有存在动态加密、签名、混淆或防重放逻辑时才创建独立模块。模块名按用途命名，例如 `crypto_params.py`、`signature.py` 或 `auth.py`。

模块只暴露一两个清晰函数，例如 `build_signed_params(payload)`、`encrypt_payload(data)` 或 `build_auth_headers(payload)`。不要在加密模块里发网络请求。

需要记录算法来源：

- 浏览器包函数名
- JS 片段位置或资源 URL
- 相关字段名
- 抓包对比结论

如果算法依赖浏览器运行态，优先继续追查其真实来源：

- 是构建产物里的纯算法
- 是前置接口返回的动态盐值、票据或 credential
- 是服务端下发的一次性 token
- 是用户必须提供的显式入参或环境变量

不要把“浏览器里现在能读到的值”误当成算法本身。

## 开发规范

为真实目标生成脚本前，先阅读 [development-standards.md](references/development-standards.md)，并按其中清单执行。

核心规范：

- 使用 `requests.Session`
- 每个请求都设置明确 `timeout`
- 调用 `raise_for_status()`，并检查接口自己的 `success/code/msg`
- 增加有限重试和明确异常分类；只重试临时错误，认证、身份、权限、参数、验证码和风控错误直接抛出
- 大任务多子任务场景下使用任务状态 JSON，失败子任务记录后继续执行其他子任务，下次重跑自动跳过已完成子任务
- 不把从浏览器现成会话里直接读出的认证参数当作最终交付方案
- 表格导出场景下，表头按页面显示名称落表，并额外生成 `field_mapping.json`
- 表格导出场景下，读取独立的 `field_mapping.json`，不要在 `.py` 里再维护重复映射
- 生成代码时必须包含至少 1 个 `class`
- 每个函数和每个方法上方都要有简短注释
- 遵守高内聚、低耦合原则，一个功能只在一个方法内完成，禁止抽离无关的小方法
- 最终交付脚本不包含 `cdp_debug_url`、`webSocketDebuggerUrl`、`127.0.0.1:9222`、`/json`、`/json/version` 等分析期参数或检查逻辑
- `self.xxx` 只保留长期状态，不滥用为一次性调用参数容器
- `csv_path`、`mapping_output_path`、`json_path` 等输出路径不默认保存在对象属性里
- 请求头优先定义为常量，并在类内通过 `update_headers()` 统一更新
- 主脚本按英文 `snake_case` 命名，例如 `platform_section_function.py`
- 如果生成目录，目录名也按英文 `snake_case` 命名
- 中文业务词要翻译成英文语义词，不要直接用中文文件名；平台专有名词可使用稳定英文名、官方名或稳定 ASCII 标识
- 让脚本服务于当前工作流，不为“所有网站”过度抽象
- 交付前用浏览器结果校验脚本输出

## 常见补充点

交付前检查：

- 抓包阶段 9222 调试端口是否可用，且是否只接管了已有浏览器
- 如果页面工具只看到新的 `about:blank`、空白页或孤立受管会话，是否已经停止该路径并改走直接 CDP
- token 刷新或静默登录请求是否必须先执行
- token、credential、nonce、sign 是否来自前置响应，而不是本地存储
- cookie 是否由用户显式传入，而不是脚本自动抽取
- 租户、组织、工作区、项目、用户 ID 是否来自路由参数、前置接口或用户输入
- GraphQL 接口中是否用 `operationName`、`variables`、persisted query hash 替代 REST 路径
- 是否涉及 multipart 上传、二进制下载、导出任务轮询、短期签名下载 URL
- 是否需要大任务状态文件来跳过已完成子任务，并记录失败/未完成子任务
- 重试是否只覆盖临时错误，是否避免重复创建导出任务
- 是否有服务端分页、cursor 分页、无限滚动、表格排序和筛选状态
- 如果是表格导出，页面表头与 response 字段是否已经建立完整映射 JSON
- 日期边界、时区、语言、响应编码、压缩是否影响结果
- 是否有 CSRF、SameSite cookie、设备指纹、一次性 nonce、防重放时间戳
- 是否遇到 CAPTCHA、MFA、风控挑战或 WebAuthn，这类流程不能用 `requests` 绕过
- 是否是 WebSocket 或 SSE 流程，`requests` 只适合复刻其启动接口，不适合复刻实时流
- 大批量导出是否需要限速，避免触发生产接口限制

## 输出要求

返回：

- 生成的 Python 文件路径
- 如果是表格导出，生成的 `field_mapping.json` 路径
- 必要请求链摘要，只列真正有用的端点
- 必需运行参数和运行方式
- 如果是大任务多子任务采集，返回任务状态文件路径、已完成/跳过/失败/未完成数量，以及失败子任务摘要
- `__main__` 中当前测试参数的说明，例如店铺、cookie、日期范围、文件名；如果是表格导出，再补充字段映射路径
- 认证参数的来源说明：
  - 哪些是脚本自行生成
  - 哪些来自前置接口
  - 哪些需要用户提供
- 已执行的验证，以及剩余限制，例如验证码、MFA、短期 URL、时间敏感签名、浏览器运行态依赖或用户描述不完整
