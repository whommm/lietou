from src.core.search_strategy_service import SearchStrategyService


def test_build_from_analysis_result_extracts_copy_links():
    service = SearchStrategyService()

    strategy = service.build_from_analysis_result(
        '<a href="copy://算法工程师">算法工程师</a>'
        '<a href="copy://推荐系统">推荐系统</a>'
        '<a href="copy://算法工程师">算法工程师</a>'
    )

    assert strategy.precise_keywords == ["算法工程师", "推荐系统"]
    assert strategy.expansion_keywords == []


def test_to_payload_returns_serializable_structure():
    service = SearchStrategyService()
    strategy = service.build_from_analysis_result(
        '<a href="copy://后端开发">后端开发</a>'
    )

    payload = service.to_payload(strategy)

    assert payload["precise_keywords"] == ["后端开发"]
    assert payload["boolean_queries"] == []


def test_build_from_analysis_result_extracts_structured_sections():
    service = SearchStrategyService()

    html = """
    <p><strong>第一轮精准搜索词（优先用于快速命中核心人群）：</strong></p>
    <div class="tag-cloud">
      <a href="copy://算法工程师" class="tag">算法工程师</a>
      <a href="copy://推荐系统" class="tag">推荐系统</a>
    </div>
    <p><strong>第二轮扩池词（用于扩大召回，挖到别人没搜到的人）：</strong></p>
    <div class="tag-cloud">
      <a href="copy://机器学习工程师" class="tag">机器学习工程师</a>
    </div>
    <p><strong>同义岗位词 / 内部叫法 / 替代叫法：</strong></p>
    <div class="tag-cloud">
      <a href="copy://算法专家" class="tag">算法专家</a>
    </div>
    <p><strong>核心能力 / 业务场景词：</strong></p>
    <div class="tag-cloud">
      <a href="copy://搜索排序" class="tag">搜索排序</a>
    </div>
    <p><strong>优先来源公司 / 团队线索：</strong></p>
    <div class="tag-cloud">
      <a href="copy://字节跳动" class="tag">字节跳动</a>
    </div>
    <p><strong>高噪音词提醒：</strong></p>
    <div class="alert alert-warning">算法 单独搜索噪音很大；建议搭配推荐系统或搜索排序</div>
    <p><strong>推荐组合搜索公式：</strong></p>
    <ol>
      <li>算法工程师 + 推荐系统</li>
      <li>算法专家 + 搜索排序</li>
    </ol>
    <p><strong>排除 / 去噪思路：</strong>排除纯学术背景；排除视觉算法方向</p>
    """

    strategy = service.build_from_analysis_result(html)

    assert strategy.precise_keywords == ["算法工程师", "推荐系统"]
    assert strategy.expansion_keywords == ["机器学习工程师"]
    assert strategy.synonyms == ["算法专家", "搜索排序"]
    assert strategy.source_company_hints == ["字节跳动"]
    assert any("算法工程师 + 推荐系统" in item for item in strategy.boolean_queries)
    assert any(
        "排除纯学术背景" in item or "纯学术背景" in item
        for item in strategy.exclude_keywords
    )
