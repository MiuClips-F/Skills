from datetime import datetime
from pathlib import Path
import csv
import json
import time

import requests


BASE_URL = "https://example.com"
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}
TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}


# 操作步骤：- 打开示例报表页面；- 确认已登录并进入目标报表。访问网址：https://example.com/report/page。
class PlatformSectionFunctionExporter:
    # 初始化会话和字段映射，无外部访问网址。
    def __init__(self, cookie, field_mapping_path):
        self.field_mapping = json.loads(Path(field_mapping_path).read_text(encoding="utf-8"))
        self.session = requests.Session()
        self.update_headers(cookie=cookie)

    # 用常量请求头更新当前会话头，无外部访问网址。
    def update_headers(self, cookie, extra_headers=None):
        headers = dict(BASE_HEADERS)
        headers["Cookie"] = cookie
        if extra_headers:
            headers.update(extra_headers)
        self.session.headers.clear()
        self.session.headers.update(headers)

    # 操作步骤：- 打开示例报表页面；- 选择店铺和日期范围；- 点击查询或翻页触发列表请求。访问网址：https://example.com/report/page。
    def fetch_records(self, shop_name, start_date, end_date, page_size):
        """
        参数：shop_name 对应店铺名称，str，必填，来源为当前抓包店铺；start_date 对应统计开始日期，str，必填，格式 YYYY-MM-DD；end_date 对应统计结束日期，str，必填，格式 YYYY-MM-DD；page_size 对应每页数量，int，必填，来源为页面分页大小。
        """
        records = []
        page = 1
        while True:
            """
            参数：shopName 对应请求店铺名称，str，必填，来源 shop_name；startDate 对应请求开始日期，str，必填，来源 start_date；endDate 对应请求结束日期，str，必填，来源 end_date；page 对应当前页码，int，必填，循环生成；size 对应每页数量，int，必填，来源 page_size。
            """
            request_payload = {
                "shopName": shop_name,
                "startDate": start_date,
                "endDate": end_date,
                "page": page,
                "size": page_size,
            }
            last_error = None
            for attempt in range(1, 4):
                try:
                    response = self.session.post(
                        f"{BASE_URL}/api/example",
                        json=request_payload,
                        timeout=30,
                    )
                    if response.status_code in TRANSIENT_STATUS_CODES:
                        last_error = RuntimeError(f"temporary http error: {response.status_code}")
                        time.sleep(attempt * 2)
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    break
                except (requests.Timeout, requests.ConnectionError) as exc:
                    last_error = exc
                    time.sleep(attempt * 2)
            else:
                raise RuntimeError(f"request failed after retries: {last_error}")

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

    # 把响应记录和运行上下文转换成页面展示行，无外部访问网址。
    def build_row(self, record, context):
        row = {}
        for header, source in self.field_mapping.items():
            if source.startswith("__context__."):
                row[header] = context.get(source.replace("__context__.", "", 1), "")
                continue
            if source.startswith("__derived__."):
                row[header] = ""
                continue
            value = record
            for key in source.split("."):
                value = value.get(key) if isinstance(value, dict) else None
            row[header] = value if value not in (None, "") else ""
        return row

    # 输出 CSV 和字段映射文件，无外部访问网址。
    def write_outputs(self, rows, csv_path, mapping_output_path):
        csv_path = Path(csv_path)
        mapping_output_path = Path(mapping_output_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        mapping_output_path.parent.mkdir(parents=True, exist_ok=True)

        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.field_mapping.keys()))
            writer.writeheader()
            writer.writerows(rows)

        mapping_output_path.write_text(
            json.dumps(self.field_mapping, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 操作步骤：- 打开示例报表页面；- 选择店铺和日期范围；- 点击查询生成报表列表；- 保存页面列表结果。访问网址：https://example.com/report/page。
    def run(self, report_context, start_date, end_date, page_size, csv_path, mapping_output_path):
        records = self.fetch_records(
            shop_name=report_context.get("shop_name", ""),
            start_date=start_date,
            end_date=end_date,
            page_size=page_size,
        )
        context = dict(report_context)
        context.setdefault("data_date", f"{start_date}~{end_date}")
        rows = [self.build_row(record, context) for record in records]
        self.write_outputs(
            rows=rows,
            csv_path=csv_path,
            mapping_output_path=mapping_output_path,
        )


if __name__ == "__main__":
    # __main__ 只保留实际运行参数，不包含抓包阶段使用的 CDP/9222 参数。
    cookie = "当前测试 cookie 字符串"
    shop_id = "当前店铺ID"
    shop_name = "当前抓包店铺"
    business_export_table_name = "示例报表"
    start_date = "2026-05-01"
    end_date = "2026-05-22"
    report_context = {
        "data_date": f"{start_date}~{end_date}",
        "shop_id": shop_id,
        "shop_name": shop_name,
        "product_id": "当前商品ID",
        "sku": "当前SKU",
        "product_name": "当前商品名称",
        "live_room_name": "当前直播间名称",
        "live_session_id": "当前直播场次ID",
        "account_name": "当前账户名",
        "account_id": "当前账户ID",
    }
    page_size = 100
    field_mapping_path = Path(__file__).with_name("field_mapping.json")
    data_fetch_time = datetime.now().strftime("%Y%m%d%H%M%S")
    file_stem = f"{data_fetch_time}-{business_export_table_name}"
    csv_path = Path(r"D:\exports") / f"{file_stem}.csv"
    mapping_output_path = csv_path.with_name(f"{file_stem}_field_mapping.json")
    exporter = PlatformSectionFunctionExporter(
        cookie=cookie,
        field_mapping_path=field_mapping_path,
    )
    exporter.run(
        report_context=report_context,
        start_date=start_date,
        end_date=end_date,
        page_size=page_size,
        csv_path=csv_path,
        mapping_output_path=mapping_output_path,
    )
