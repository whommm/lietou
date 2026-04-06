from src.core.history import HistoryRecord


def dedupe_company_titles(records, limit):
    company_titles = []
    seen_titles = set()
    for record in records:
        title = record.title.strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        company_titles.append(title)
        if len(company_titles) >= limit:
            break
    return company_titles


def make_job_option_label(record, index):
    base_title = record.title[:30] + "..." if len(record.title) > 30 else record.title
    time_suffix = record.created_at[5:16] if record.created_at else str(index + 1)
    return "{}  [{}]".format(base_title, time_suffix)


def test_company_titles_are_deduped_and_limited():
    records = [
        HistoryRecord(title="字节跳动", created_at="2026-04-05 10:00:00"),
        HistoryRecord(title="字节跳动", created_at="2026-04-05 09:00:00"),
        HistoryRecord(title="阿里巴巴", created_at="2026-04-05 08:00:00"),
    ]

    assert dedupe_company_titles(records, 2) == ["字节跳动", "阿里巴巴"]


def test_company_titles_can_be_limited_to_latest_three():
    records = [
        HistoryRecord(title="A"),
        HistoryRecord(title="B"),
        HistoryRecord(title="C"),
        HistoryRecord(title="D"),
    ]

    assert dedupe_company_titles(records, 3) == ["A", "B", "C"]


def test_job_option_label_uses_timestamp_suffix_to_avoid_collisions():
    record = HistoryRecord(
        title="高级算法工程师",
        created_at="2026-04-05 10:23:45",
    )

    assert make_job_option_label(record, 0) == "高级算法工程师  [04-05 10:23]"


def test_job_option_label_truncates_long_titles():
    record = HistoryRecord(
        title="这是一个非常长非常长非常长非常长非常长的岗位名称用于测试截断效果",
        created_at="2026-04-05 10:23:45",
    )

    label = make_job_option_label(record, 0)

    assert label.endswith("[04-05 10:23]")
    assert "..." in label
