"""모든 플랫폼의 트렌드 데이터를 수집하여 data/{mode}/YYYY-MM-DD/ 에 JSON으로 저장

사용법:
  python collect_all.py                    # 패션 + 범용 둘 다
  python collect_all.py --mode fashion     # 패션만
  python collect_all.py --mode general     # 범용만
"""
import os
import sys
import json
import datetime
import importlib

COLLECTORS = [
    "youtube",
    "google_trends",
    "tiktok",
    "x_twitter",
    "naver",
    "reddit",
    "pinterest",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def run_collection(mode, collectors=None):
    """지정된 모드(fashion/general)로 수집 실행"""
    today = datetime.date.today().isoformat()
    today_dir = os.path.join(DATA_DIR, mode, today)
    os.makedirs(today_dir, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    meta = {"run_date": today, "run_timestamp": timestamp, "mode": mode, "results": {}}

    targets = collectors or COLLECTORS

    print(f"\n  === {mode.upper()} 모드 수집 시작 ===\n")

    for name in targets:
        if name not in COLLECTORS:
            print(f"  [!] 알 수 없는 수집기: {name} — 건너뜀")
            continue

        print(f"  [{COLLECTORS.index(name)+1}/{len(COLLECTORS)}] {name} 수집 중...", end=" ", flush=True)
        try:
            module = importlib.import_module(f"collectors.{name}")
            data = module.collect(mode=mode)

            # 타임스탬프 추가
            data["collected_at"] = timestamp

            # JSON 저장
            filepath = os.path.join(today_dir, f"{name}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 상태 확인
            status = data.get("status", "success")
            if status == "skipped":
                print(f"건너뜀 ({data.get('reason', '')})")
                meta["results"][name] = {"status": "skipped", "reason": data.get("reason", "")}
            elif status == "error":
                print(f"오류 ({data.get('reason', '')})")
                meta["results"][name] = {"status": "error", "reason": data.get("reason", "")}
            else:
                # 아이템 수 계산
                count = _count_items(data)
                print(f"OK ({count}개)")
                meta["results"][name] = {"status": "success", "items": count}

        except Exception as e:
            print(f"실패: {e}")
            meta["results"][name] = {"status": "error", "reason": str(e)}

    # 메타 파일 저장
    meta_path = os.path.join(today_dir, "_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 요약 출력
    success = [k for k, v in meta["results"].items() if v["status"] == "success"]
    skipped = [k for k, v in meta["results"].items() if v["status"] == "skipped"]
    failed = [k for k, v in meta["results"].items() if v["status"] == "error"]
    print()
    print(f"  [{mode}] 수집 완료: {today_dir}")
    if success:
        print(f"  성공: {', '.join(success)}")
    if skipped:
        print(f"  건너뜀: {', '.join(skipped)}")
    if failed:
        print(f"  실패: {', '.join(failed)}")

    return meta


def _count_items(data):
    """데이터에서 아이템 수를 재귀적으로 계산"""
    count = 0
    skip_keys = {"platform", "collected_at", "status", "source", "year",
                 "source_url", "mode", "category", "monitoring_keywords"}
    for key, val in data.items():
        if key in skip_keys:
            continue
        if isinstance(val, list):
            count += len(val)
        elif isinstance(val, dict):
            for v in val.values():
                if isinstance(v, list):
                    count += len(v)
                elif isinstance(v, dict):
                    for vv in v.values():
                        if isinstance(vv, list):
                            count += len(vv)
    return count


def main():
    # 모드 파싱
    modes = ["fashion", "general"]
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            modes = [sys.argv[idx + 1]]

    for mode in modes:
        run_collection(mode)


if __name__ == "__main__":
    main()
