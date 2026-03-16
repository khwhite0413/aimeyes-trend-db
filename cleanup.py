"""90일 이상 지난 수집 데이터를 삭제"""
import os
import re
import shutil
import datetime

RETENTION_DAYS = 90
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def main():
    if not os.path.isdir(DATA_DIR):
        print("data/ 폴더가 없습니다.")
        return

    cutoff = datetime.date.today() - datetime.timedelta(days=RETENTION_DAYS)
    total_deleted = 0
    total_kept = 0

    for mode in ["fashion", "general"]:
        mode_dir = os.path.join(DATA_DIR, mode)
        if not os.path.isdir(mode_dir):
            continue

        deleted = []
        kept = []

        for entry in sorted(os.listdir(mode_dir)):
            entry_path = os.path.join(mode_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            if not re.match(r"\d{4}-\d{2}-\d{2}$", entry):
                continue

            try:
                dir_date = datetime.date.fromisoformat(entry)
            except ValueError:
                continue

            if dir_date < cutoff:
                shutil.rmtree(entry_path)
                deleted.append(entry)
            else:
                kept.append(entry)

        total_deleted += len(deleted)
        total_kept += len(kept)

        if deleted:
            print(f"  [{mode}] 삭제: {len(deleted)}일치 ({deleted[0]} ~ {deleted[-1]})")
        else:
            print(f"  [{mode}] 삭제 대상 없음 (보존: {len(kept)}일치)")

    print(f"\n  전체: 보존 {total_kept}일치, 삭제 {total_deleted}일치")


if __name__ == "__main__":
    main()
