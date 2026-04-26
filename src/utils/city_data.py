"""City helpers for Liepin search filters."""

import re
from typing import Dict, List


CITY_ADJACENT: Dict[str, List[str]] = {
    "北京": ["天津", "廊坊", "保定"],
    "上海": ["苏州", "杭州", "无锡"],
    "广州": ["深圳", "佛山", "东莞"],
    "深圳": ["广州", "东莞", "惠州"],
    "杭州": ["上海", "苏州", "宁波"],
    "南京": ["苏州", "无锡", "常州"],
    "苏州": ["上海", "无锡", "杭州"],
    "成都": ["重庆", "绵阳", "德阳"],
    "重庆": ["成都", "泸州", "遂宁"],
    "武汉": ["鄂州", "黄石", "孝感"],
    "西安": ["咸阳", "宝鸡", "渭南"],
    "长沙": ["株洲", "湘潭", "岳阳"],
    "郑州": ["洛阳", "开封", "新乡"],
    "天津": ["北京", "廊坊", "唐山"],
    "青岛": ["济南", "烟台", "潍坊"],
    "济南": ["青岛", "淄博", "泰安"],
    "厦门": ["泉州", "漳州", "福州"],
    "福州": ["厦门", "泉州", "莆田"],
    "宁波": ["杭州", "绍兴", "舟山"],
    "佛山": ["广州", "深圳", "东莞"],
    "东莞": ["深圳", "广州", "惠州"],
    "惠州": ["深圳", "东莞", "广州"],
}

KNOWN_CITIES = sorted(
    set(CITY_ADJACENT.keys()).union(
        city for adjacent in CITY_ADJACENT.values() for city in adjacent
    ),
    key=len,
    reverse=True,
)


def normalize_city(value: str) -> str:
    """Return a normalized city name without common suffix noise."""
    value = (value or "").strip()
    value = re.sub(r"(市|地区|城区|省)$", "", value)
    return value.strip()


def extract_city_from_text(text: str) -> str:
    """Extract the first known city from JD or analysis text."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    for city in KNOWN_CITIES:
        if re.search(r"(?<![\u4e00-\u9fff]){}(?:市)?(?![\u4e00-\u9fff])".format(re.escape(city)), text):
            return city
    for pattern in (
        r"(?:工作地点|工作地址|所在城市|城市|地点)[:：\s]*([\u4e00-\u9fff]{2,6})",
        r"([\u4e00-\u9fff]{2,6})市",
    ):
        match = re.search(pattern, text)
        if match:
            return normalize_city(match.group(1))
    return ""


def get_default_adjacent_cities(city: str, limit: int = 3) -> List[str]:
    """Return default nearby cities for the given city."""
    city = normalize_city(city)
    return list(CITY_ADJACENT.get(city, []))[:limit]


def build_default_city_scope(city: str, limit: int = 4) -> List[str]:
    """Return primary city plus nearby cities, deduplicated."""
    city = normalize_city(city)
    values = [city] if city else []
    values.extend(get_default_adjacent_cities(city, max(0, limit - 1)))
    deduped = []
    for item in values:
        if item and item not in deduped:
            deduped.append(item)
    return deduped[:limit]
