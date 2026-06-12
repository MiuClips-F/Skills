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
            if source.startswith("__derived__."):
                row[header] = ""
                continue
            value = record
            for key in source.split("."):
                value = value.get(key) if isinstance(value, dict) else None
            row[header] = value if value not in (None, "") else ""
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
    # __main__ 只保留实际运行参数，不包含抓包阶段使用的 CDP/9222 参数。
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
