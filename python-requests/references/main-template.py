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


# 操作步骤：- 打开示例报表页面；- 选择店铺和日期范围；- 点击查询。访问网址：https://example.com/report/page。
class PlatformSectionFunctionExporter:
    # 初始化请求会话和字段映射。
    def __init__(self, cookie, field_mapping_path):
        self.session = requests.Session()
        self.field_mapping = json.loads(Path(field_mapping_path).read_text(encoding="utf-8"))
        self.update_headers(cookie)

    # 用基础请求头刷新会话头。
    def update_headers(self, cookie, extra_headers=None):
        headers = dict(BASE_HEADERS)
        headers["Cookie"] = cookie
        if extra_headers:
            headers.update(extra_headers)
        self.session.headers.clear()
        self.session.headers.update(headers)

    # 操作步骤：- 打开示例报表页面；- 选择店铺和日期范围；- 点击查询或翻页。访问网址：https://example.com/report/page。
    def fetch_records(self, shop_name, start_date, end_date, page_size):
        """
        参数：shop_name 对应店铺名称，str，必填，来源为页面筛选条件；start_date 对应开始日期，str，必填，格式 YYYY-MM-DD；end_date 对应结束日期，str，必填，格式 YYYY-MM-DD；page_size 对应每页数量，int，必填，来源为页面分页大小。
        """
        records = []
        page = 1
        while True:
            """
            参数：shopName 对应请求店铺名称，str，必填，来源 shop_name；startDate 对应请求开始日期，str，必填，来源 start_date；endDate 对应请求结束日期，str，必填，来源 end_date；page 对应当前页码，int，必填，循环生成；size 对应每页数量，int，必填，来源 page_size。
            """
            payload = {
                "shopName": shop_name,
                "startDate": start_date,
                "endDate": end_date,
                "page": page,
                "size": page_size,
            }
            last_error = None
            for attempt in range(1, 4):
                try:
                    response = self.session.post(f"{BASE_URL}/api/example", json=payload, timeout=30)
                    if response.status_code in TRANSIENT_STATUS_CODES:
                        last_error = RuntimeError(f"temporary http status: {response.status_code}")
                        time.sleep(attempt * 2)
                        continue
                    response.raise_for_status()
                    result = response.json()
                    break
                except (requests.Timeout, requests.ConnectionError) as exc:
                    last_error = exc
                    time.sleep(attempt * 2)
            else:
                raise RuntimeError(f"request failed after retries: {last_error}")

            if result.get("success") is not True:
                raise RuntimeError(f"api failed: {result}")
            current = result.get("data", {}).get("records", [])
            records.extend(current)
            if len(current) < page_size:
                break
            page += 1
        return records

    # 操作步骤：- 打开示例报表页面；- 查询列表；- 保存页面展示结果。访问网址：https://example.com/report/page。
    def run(self, shop_id, shop_name, business_date, data_capture_time, output_filename, start_date, end_date, page_size, csv_path):
        records = self.fetch_records(shop_name, start_date, end_date, page_size)
        row_context = {
            "data_capture_time": data_capture_time,
            "business_date": business_date,
            "shop_id": shop_id,
            "shop_name": shop_name,
            "output_filename": output_filename,
        }
        rows = []
        for record in records:
            row = {}
            for header, source in self.field_mapping.items():
                if source.startswith("__meta__."):
                    row[header] = row_context.get(source.split(".", 1)[1], "")
                    continue
                if source.startswith("__derived__."):
                    row[header] = ""
                    continue
                value = record
                for key in source.split("."):
                    value = value.get(key) if isinstance(value, dict) else None
                row[header] = value if value not in (None, "") else ""
            rows.append(row)

        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.field_mapping.keys()))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    # __main__ 只保留实际运行参数，不包含抓包阶段参数。
    cookie = "当前测试 cookie 字符串"
    shop_id = "当前店铺ID"
    shop_name = "当前抓包店铺"
    business_date = "20260615"
    export_table_name = "示例报表"
    start_date = "2026-06-15"
    end_date = "2026-06-15"
    page_size = 100
    data_capture_time = datetime.now().strftime("%Y%m%d%H%M%S")
    output_filename = f"{data_capture_time}-{business_date}-{export_table_name}.csv"
    csv_path = Path(__file__).resolve().parent / "output" / output_filename
    field_mapping_path = Path(__file__).with_name("field_mapping.json")

    exporter = PlatformSectionFunctionExporter(cookie=cookie, field_mapping_path=field_mapping_path)
    exporter.run(
        shop_id=shop_id,
        shop_name=shop_name,
        business_date=business_date,
        data_capture_time=data_capture_time,
        output_filename=output_filename,
        start_date=start_date,
        end_date=end_date,
        page_size=page_size,
        csv_path=csv_path,
    )
