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
    assert isinstance(payload["atomic_terms"], dict)
    assert isinstance(payload["executable_rounds"], list)


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
    assert strategy.atomic_terms["capability_terms"]
    assert strategy.executable_rounds


def test_build_from_analysis_result_prefers_embedded_search_intent_json():
    service = SearchStrategyService()
    html = """
    <div class="tag-cloud">
      <a href="copy://灯具结构工程师" class="tag">灯具结构工程师</a>
    </div>
    <script type="application/json" data-search-intent="true">
    {
      "domain_terms": ["灯具", "照明", "LED"],
      "capability_terms": ["结构", "结构设计"],
      "process_terms": ["散热", "注塑"],
      "object_terms": ["外壳"],
      "exclude_terms": ["建筑结构"],
      "recommended_rounds": ["结构 灯具", "结构 照明", "结构 灯具 散热"]
    }
    </script>
    """

    strategy = service.build_from_analysis_result(html)

    assert strategy.atomic_terms["domain_terms"] == ["灯具", "照明", "LED"]
    assert strategy.atomic_terms["capability_terms"] == ["结构", "结构设计"]
    assert [item["query"] for item in strategy.executable_rounds] == [
        "结构 灯具",
        "结构 照明",
        "结构 灯具 散热",
    ]


def test_build_from_analysis_result_ignores_boolean_recommended_rounds():
    service = SearchStrategyService()
    html = """
    <script type="application/json" data-search-intent="true">
    {
      "recommended_rounds": [
        {"query":"（Java OR Python） AND “微服务” NOT 测试","match_mode":"all","scope":"目前职位","intent":"精准搜索"}
      ]
    }
    </script>
    """

    strategy = service.build_from_analysis_result(html)

    assert strategy.executable_rounds == []


def test_build_from_analysis_result_extracts_liepin_filters():
    service = SearchStrategyService()
    html = """
    <p>工作地点：深圳</p>
    <p>要求：3-5年经验，本科及以上，性别不限</p>
    <a href="copy://结构 灯具">结构 灯具</a>
    """

    strategy = service.build_from_analysis_result(html)
    payload = service.to_payload(strategy)

    assert strategy.filters["目前城市"] == ["深圳", "广州", "东莞", "惠州"]
    assert strategy.filters["工作年限"] == "3-5年"
    assert strategy.filters["教育经历"] == "本科"
    assert strategy.filters["性别"] == "不限"
    assert payload["filters"] == strategy.filters


def test_build_from_analysis_result_uses_modern_search_strategy_sections():
    service = SearchStrategyService()
    html = """
    <p><strong>表面要求：</strong>负责从市场调研到量产上市。</p>
    <p><strong>硬性门槛：</strong>5年+产品研发团队管理经验</p>
    <p><strong>可替代条件：</strong>大专学历</p>
    <p><strong>直接关键词（从JD表面直接提取）：</strong></p>
    <div class="tag-cloud">
      <a href="copy://产品总监">产品总监</a>
      <a href="copy://产品设计经理">产品设计经理</a>
      <a href="copy://3D打印">3D打印</a>
    </div>
    <p><strong>间接关键词（从职责本质剖析推导）：</strong></p>
    <div class="tag-cloud">
      <a href="copy://从0到1">从0到1</a>
      <a href="copy://量产">量产</a>
      <a href="copy://供应链管理">供应链管理</a>
    </div>
    <p><strong>长尾关键词（精准度最高）：</strong></p>
    <div class="tag-cloud">
      <a href="copy://文创产品开发">文创产品开发</a>
      <a href="copy://潮玩设计">潮玩设计</a>
    </div>
    <p><strong>渐进式搜索策略（4轮递进）：</strong></p>
    <ol>
      <li><strong>第1轮（测绘搜索，OR模式）：</strong>(产品总监 OR 设计总监) AND (文创 OR 潮玩 OR 玩具 OR 展馆)</li>
      <li><strong>第2轮（精准搜索，AND模式）：</strong>“产品设计” AND “3D打印” AND “供应链” AND “量产”</li>
    </ol>
    """

    strategy = service.build_from_analysis_result(html)

    assert strategy.filters.get("目前城市") is None
    assert strategy.filters["工作年限"] == "5年以上"
    assert strategy.filters["教育经历"] == "大专"
    assert strategy.filters["活跃度"] == "近一周"
    assert strategy.precise_keywords[:3] == ["产品总监", "产品设计经理", "3D打印"]
    assert strategy.expansion_keywords[:3] == ["从0到1", "量产", "供应链管理"]
    assert "文创产品开发" in strategy.synonyms
    assert strategy.executable_rounds[0]["query"] == "文创 潮玩"
    assert strategy.executable_rounds[0]["position_filter"] == "产品"
    assert strategy.executable_rounds[1]["query"] == "文创衍生品"
    assert strategy.executable_rounds[1]["position_filter"] == "产品"
    assert len(strategy.executable_rounds) == 2
    assert all("AND" not in item["query"] for item in strategy.executable_rounds)


def test_build_from_analysis_result_uses_keyword_matrix_when_no_progressive_rounds():
    service = SearchStrategyService()
    html = """
    <p><strong>硬性指标基线：</strong>统招大专及以上学历，5年+产品研发团队管理经验。</p>
    <p><strong>直接关键词（从JD表面直接提取）：</strong></p>
    <div class="tag-cloud">
      <a href="copy://产品总监">产品总监</a>
      <a href="copy://产品设计经理">产品设计经理</a>
      <a href="copy://设计总监">设计总监</a>
      <a href="copy://3D打印">3D打印</a>
      <a href="copy://工业设计">工业设计</a>
      <a href="copy://结构设计">结构设计</a>
    </div>
    <p><strong>间接关键词（从职责本质剖析推导）：</strong></p>
    <div class="tag-cloud">
      <a href="copy://从0到1">从0到1</a>
      <a href="copy://爆款">爆款</a>
      <a href="copy://打样">打样</a>
      <a href="copy://量产">量产</a>
      <a href="copy://供应链管理">供应链管理</a>
      <a href="copy://团队搭建">团队搭建</a>
    </div>
    <p><strong>长尾关键词（精准度最高）：</strong></p>
    <div class="tag-cloud">
      <a href="copy://文创产品开发">文创产品开发</a>
      <a href="copy://潮玩设计">潮玩设计</a>
      <a href="copy://展品设计">展品设计</a>
      <a href="copy://益智玩具设计">益智玩具设计</a>
    </div>
    """

    strategy = service.build_from_analysis_result(html)
    queries = [item["query"] for item in strategy.executable_rounds]

    assert strategy.filters["教育经历"] == "大专"
    assert strategy.filters["活跃度"] == "近一周"
    assert queries[0] == "文创 潮玩"
    assert queries[1] == "文创衍生品"
    assert queries[2] == "益智玩具 科普"
    assert queries[3] == "展品 展馆"
    assert len(queries) == 4
    assert strategy.executable_rounds[0]["position_filter"] == "产品"
    assert strategy.executable_rounds[-1]["position_filter"] == "产品"
    assert strategy.atomic_terms["capability_terms"][:3] == ["3D打印", "供应链管理", "量产"]
    assert strategy.atomic_terms["domain_terms"][:3] == ["文创产品开发", "潮玩设计", "展品设计"]
    assert all("AND" not in query and "OR" not in query and "NOT" not in query for query in queries)
    assert "产品" not in queries
    assert "设计" not in queries
