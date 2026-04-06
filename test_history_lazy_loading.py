from src.core.history import HistoryRecord


def page_slice(records, rendered_count, page_size):
    return records[rendered_count : rendered_count + page_size]


def test_page_slice_returns_first_batch():
    records = [HistoryRecord(title=str(i)) for i in range(50)]

    batch = page_slice(records, 0, 20)

    assert len(batch) == 20
    assert batch[0].title == "0"
    assert batch[-1].title == "19"


def test_page_slice_returns_remaining_batch():
    records = [HistoryRecord(title=str(i)) for i in range(50)]

    batch = page_slice(records, 40, 20)

    assert len(batch) == 10
    assert batch[0].title == "40"
    assert batch[-1].title == "49"


def test_page_slice_returns_empty_when_all_rendered():
    records = [HistoryRecord(title=str(i)) for i in range(10)]

    batch = page_slice(records, 10, 20)

    assert batch == []
