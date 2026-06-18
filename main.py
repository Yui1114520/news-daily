#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国际时政新闻日报推送 - GitHub Actions 版 v5
按 10 个地理区域 x 10 个新闻领域 分类展示
v5: 每天3次推送(6:00/12:00/20:00) + 跨次去重 + 国内媒体源 + 关键词学习+反思
"""

import os
import sys
import json
import re
import requests
from datetime import datetime, timedelta
from collections import Counter

# 强制无缓冲输出（确保 print 立即可见）
sys.stdout.reconfigure(line_buffering=True)

# ============================================================
# 微信配置（从 GitHub Secrets 环境变量读取）
# ============================================================
WECHAT_APPID       = os.environ.get("WECHAT_APPID", "")
WECHAT_APPSECRET   = os.environ.get("WECHAT_APPSECRET", "")
WECHAT_OPENID      = os.environ.get("WECHAT_OPENID", "")
WECHAT_TEMPLATE_ID = os.environ.get("WECHAT_TEMPLATE_ID", "")
GITHUB_PAGES_URL   = os.environ.get("GITHUB_PAGES_URL", "https://yui1114520.github.io/news-daily/")
TOP_N = 20

# ============================================================
# 10 个地理区域定义
# ============================================================
REGIONS = [
    {"id":"east_asia",    "name":"东北亚",        "icon":"🌏",
     "keywords":["japan","korea","north korea","south korea","beijing","tokyo","seoul","pyongyang","taiwan","mongolia","ulaanbaatar","siberia","vladivostok","kuril","sakhalin","yakutia","日本","韩国","朝鲜","蒙古","东北亚","东亚","北亚","半岛","日韩","中俄边境","远东","西伯利亚"]},
    {"id":"east_europe",  "name":"东欧",           "icon":"🏰",
     "keywords":["ukraine","russia","moscow","kyiv","belarus","poland","hungary","romania","moldova","slovakia","czechia","bulgaria","serbia","balkan","croatia","slovenia","bosnia","montenegro","albania","kosovo","estonia","latvia","lithuania","乌克兰","俄罗斯","莫斯科","东欧","波兰","巴尔干","波罗的海","白俄罗斯"]},
    {"id":"west_europe",  "name":"西欧/北欧/南欧", "icon":"🏛️",
     "keywords":["france","germany","uk","britain","italy","spain","portugal","netherlands","belgium","sweden","norway","denmark","finland","iceland","greece","switzerland","austria","ireland","eu","european union","european commission","european parliament","nato","brussels","paris","berlin","london","rome","madrid","stockholm","oslo","copenhagen","helsinki","vienna","dublin","lisbon","amsterdam","北欧","西欧","南欧","欧盟","欧洲","北约"]},
    {"id":"middle_east",  "name":"中东与北非",     "icon":"🕌",
     "keywords":["israel","iran","saudi","saudi arabia","egypt","iraq","syria","lebanon","jordan","turkey","qatar","uae","kuwait","bahrain","oman","yemen","libya","tunisia","morocco","algeria","gaza","west bank","hamas","hezbollah","houthis","arab","middle east","persian gulf","red sea","suez","iranian","turkish","ottoman","以色列","伊朗","沙特","中东","北非","叙利亚","伊拉克","黎巴嫩","也门","加沙","红海","苏伊士","土耳其","卡塔尔"]},
    {"id":"north_america","name":"北美",            "icon":"🗽",
     "keywords":["united states","usa","us ","u.s.","trump","biden","harris","congress","senate","white house","canada","mexico","washington","pentagon","state department","capitol","supreme court","wall street","federal reserve","美国","加拿大","墨西哥","特朗普","拜登","华盛顿","北美","华尔街","美联储","国会"]},
    {"id":"latin_america","name":"拉丁美洲及加勒比","icon":"🌴",
     "keywords":["brazil","argentina","colombia","venezuela","peru","chile","cuba","haiti","caribbean","amazon","latin america","panama","ecuador","bolivia","paraguay","uruguay","dominican","guatemala","honduras","el salvador","nicaragua","costa rica","jamaica","mercosur","巴西","阿根廷","古巴","委内瑞拉","拉美","加勒比","拉丁美洲","海地"]},
    {"id":"sub_sahara",   "name":"撒哈拉以南非洲", "icon":"🌍",
     "keywords":["africa","african union","nigeria","kenya","ghana","ethiopia","tanzania","south africa","angola","mozambique","madagascar","cameroon","senegal","ivory coast","cote d'ivoire","uganda","zimbabwe","zambia","namibia","botswana","gabon","togo","benin","liberia","sierra leone","malawi","sahel","mali","niger","chad","sudan","somalia","congo","drc","democratic republic","rwanda","burundi","burkina faso","central african republic","south sudan","eritrea","djibouti","sub-saharan","sahara","sahel alliance","非洲","南非","埃塞俄比亚","肯尼亚","尼日利亚","非盟","苏丹","索马里","刚果","萨赫勒","撒哈拉","南苏丹","布基纳法索","中非"]},
    {"id":"south_asia",   "name":"南亚",           "icon":"🕍",
     "keywords":["india","pakistan","bangladesh","sri lanka","nepal","afghanistan","bhutan","maldives","kashmir","modi","new delhi","islamabad","taliban","ddhaka","印度","巴基斯坦","孟加拉","斯里兰卡","阿富汗","南亚","克什米尔","塔利班","莫迪"]},
    {"id":"sea_oceania",  "name":"东南亚与大洋洲", "icon":"🌺",
     "keywords":["southeast asia","asean","philippines","vietnam","indonesia","malaysia","thailand","singapore","myanmar","cambodia","laos","brunei","timor","australia","new zealand","pacific","pacific island","south china sea","fiji","papua new guinea","solomon","南海","东南亚","菲律宾","越南","印尼","印度尼西亚","澳大利亚","新西兰","缅甸","泰国","新加坡","东盟","大洋洲","太平洋"]},
    {"id":"central_asia", "name":"中亚与高加索",   "icon":"🏔️",
     "keywords":["kazakhstan","uzbekistan","kyrgyzstan","tajikistan","turkmenistan","georgia","armenia","azerbaijan","silk road","caspian","astana","tashkent","baku","tbilisi","yerevan","caucasus","nagorno","scs","stans","哈萨克","乌兹别克","格鲁吉亚","亚美尼亚","阿塞拜疆","中亚","高加索","里海","丝绸之路"]},
]

# ============================================================
# 10 个新闻领域定义
# ============================================================
DOMAINS = [
    {"id":"geopolitics",     "name":"地缘",    "icon":"🗺️","color":"#c62828",
     "keywords":["china","us","russia","eu","bilateral","multilateral","strategic competition","great power","hegemon","indo-pacific","nato expansion","sco","shanghai cooperation","quad","aukus","polar","arctic","taiwan strait","south china sea","territory","border dispute","sovereignty","alliance","geopolit","sphere of influence","multipolar","bipolar","unipolar","containment","deterrence","pivot","rebalance","地缘","大国博弈","中美","中俄","中欧","美俄","印太","北约东扩","上合","四方安全","奥库斯","台海","南海","北极","领土","主权","联盟","势力范围","多极化","战略竞争","战略博弈"]},
    {"id":"military",        "name":"军武",    "icon":"⚔️","color":"#6a1b9a",
     "keywords":["military","weapon","missile","nuclear","nuclear weapon","nuclear bomb","npt","non-proliferation","troops","army","navy","air force","drone","uav","war","battle","offensive","defense","strike","combat","soldier","armed forces","military base","overseas bases","military alliance","arms trade","arms deal","arms race","defense budget","weapons export","ballistic","cruise missile","hypersonic","civil war","insurgency","border clash","skirmish","ceasefire"," Militia","军武","军事","武器","导弹","核武器","核不扩散","战争","战斗","军队","空袭","无人机","海军","军备竞赛","军火贸易","海外驻军","局部战争","内战","边境冲突","弹道导弹","巡航导弹","高超音速","民兵","武装"]},
    {"id":"economy",         "name":"经贸",    "icon":"💹","color":"#1565c0",
     "keywords":["trade","economy","gdp","sanction","tariff","tariff wall","trade barrier","free trade","fta","investment","bank","currency","exchange rate","inflation","recession","supply chain","export","import","market","stock","commodity","oil price","gas price","grain price","mineral","crude oil","brent","wtc","opec","debt crisis","sovereign debt","capital flow","fdi","global supply chain","industrial chain","trade war","trade deficit","trade surplus","wto","经贸","贸易","经济","制裁","关税","壁垒","自贸协定","投资","货币","汇率","通胀","供应链","大宗商品","油气","粮食价格","矿产","欧佩克","债务危机","资本流动","产业链","贸易战","贸易逆差"]},
    {"id":"tech",            "name":"科创",    "icon":"🔬","color":"#00838f",
     "keywords":["technology","ai","artificial intelligence","chip","semiconductor","space","satellite","innovation","tech","cyber","digital","science","research","biotech","biomedical","new energy","quantum","5g","6g","battery","lithium","rare earth","tech sanction","tech blockade","chip ban","export control","supply chain transfer","decoupling","tech war","internet regulation","digital governance","algorithm","large language model","llm","gpt","科创","科技","人工智能","芯片","半导体","航天","航空","生物医药","新能源","量子","电池","稀土","技术封锁","技术制裁","产业链转移","脱钩","科技战","数字监管","大模型"]},
    {"id":"ecology",         "name":"生态",    "icon":"🌿","color":"#2e7d32",
     "keywords":["climate","climate change","extreme weather","hurricane","typhoon","flood","drought","wildfire","heatwave","cold wave","environment","carbon","carbon neutral","carbon neutrality","emission","carbon tax","cbam","renewable","renewable energy","energy","oil","gas","coal","green","solar","wind","hydro","biodiversity","pollution","water crisis","deforestation","rainforest","ocean","marine","polar ice","permafrost","glacier","sea level","ecological","cross-border pollution","生态","气候","极端天气","气候变化","洪水","干旱","野火","热浪","碳中和","碳排放","碳关税","化石能源","风电","光伏","新能源转型","雨林","海洋保护","极地","冰川","海平面","跨境污染","资源争夺"]},
    {"id":"diplomacy",       "name":"外交",    "icon":"🤝","color":"#0277bd",
     "keywords":["diplomacy","summit","negotiation","treaty","agreement","un","united nations","un security council","g20","g7","brics","asean","who","world health","wto","imf","world bank","multilateral","international organization","global governance","sanctions","counter-sanction","mediation","good offices","foreign minister","secretary of state","ambassador","envoy","state visit","visa policy","foreign policy","humanitarian aid","peace talk","peacekeeping","外交","峰会","谈判","条约","协议","联合国","安理会","G20","金砖","东盟","世卫","多边","国际组织","全球治理","制裁","反制裁","调停","斡旋","外长","大使","国事访问","签证","外援","和平谈判","维和"]},
    {"id":"livelihood",      "name":"民生",    "icon":"🏥","color":"#ef6c00",
     "keywords":["health","pandemic","epidemic","outbreak","disease","cholera","ebola","covid","virus","famine","hunger","food security","food crisis","poverty","refugee","refugee crisis","migration","displacement","idp","housing","education","humanitarian","humanitarian aid","humanitarian corridor","medical aid","medical assistance","welfare","pension","cost of living","unemployment","inflation","natural disaster","earthquake","tsunami","drought","malnutrition","starvation","clean water","sanitation","民生","传染病","疫情","饥荒","粮食安全","粮食危机","贫困","难民","战争难民","移民","住房","教育","人道主义","人道救援","医疗援助","福利","养老金","生活成本","失业","自然灾害","地震","海啸","营养不良","清洁饮水"]},
    {"id":"social_movement", "name":"社会运动","icon":"✊","color":"#ad1457",
     "keywords":["protest","demonstration","strike","riot","rally","march","uprising","unrest","civil unrest","election","vote","democracy","democratic","civil society","human rights","freedom","press freedom","opposition","populism","populist","nationalism","far-right","far-left","extremism","racial","ethnic","religious conflict","sectarian","sunni","shia","immigration","anti-immigration","xenophobia","gender equality","me too","feminist","lgbt","indigenous","aboriginal","boycott","sit-in","social movement","社会运动","抗议","示威","游行","罢工","骚乱","暴动","选举","投票","民主","公民社会","人权","自由","新闻自由","反对派","民粹","民族主义","极右","极左","种族","宗教冲突","教派","逊尼","什叶","移民潮","反移民","仇外","性别平权","女权","LGBT","原住民","抵制"]},
    {"id":"security",        "name":"治安",    "icon":"🛡️","color":"#4e342e",
     "keywords":["crime","terrorism","terrorist","extremist","jihadist","isis","al-qaeda","boko haram","al-shabaab","drug","drug cartel","narco","trafficking","human trafficking","arms trafficking","gang","mafia","organized crime","police","law enforcement","smuggling","smuggling ring","piracy","somali pirate","cybercrime","cyber attack","hacker","ransomware","data breach","assassination","coup","coup d'etat","prison","interpol","extradition","international court","icc","icj","tribunal","counter-terrorism","anti-terror","joint operation","治安","犯罪","恐怖主义","极端组织","伊斯兰国","基地组织","贩毒","毒品集团","跨国犯罪","人口贩卖","军火走私","帮派","黑手党","有组织犯罪","警察","走私","海盗","网络犯罪","黑客攻击","勒索软件","暗杀","政变","监狱","国际刑警","引渡","国际法庭","国际刑事法院","反恐","联合反恐"]},
    {"id":"culture",         "name":"人文",    "icon":"🎭","color":"#37474f",
     "keywords":["culture","religion","heritage","world heritage","unesco","art","film","festival","music","concert","sport","sports","olympic","world cup","fifa","asian games","archaeology","language","linguistic","tradition","cultural exchange","cultural diplomacy","international students","study abroad","education exchange","tourism","tourism recovery","travel","infrastructure aid","overseas construction","belt and road","bri","poverty alleviation","development aid","cultural industry","film industry","entertainment","literature","museum","exhibition","人文","文化","宗教","遗产","世界遗产","艺术","电影","音乐","体育","奥运","世界杯","亚运","考古","语言","传统","文化交流","留学","教育交流","旅游","文旅复苏","基建援助","一带一路","扶贫","发展援助","影视","文学","博物馆","展览"]},
]

# ============================================================
# RSS 新闻源（优先使用 Google News 聚合 + 主流媒体）
# Google News RSS 最稳定，覆盖面最广，不易失效
# ============================================================
NEWS_SOURCES = [
    # --- Google News 聚合源（最稳定，覆盖全球） ---
    {"name":"GoogleNews-World",    "url":"https://news.google.com/rss?topic=w&hl=en-US&gl=US&ceid=US:en",                    "weight":10},
    {"name":"GoogleNews-Asia",     "url":"https://news.google.com/rss/search?q=international+news+asia&hl=en-US&gl=US&ceid=US:en",  "weight":8},
    {"name":"GoogleNews-Europe",   "url":"https://news.google.com/rss/search?q=international+news+europe&hl=en-US&gl=US&ceid=US:en", "weight":8},
    {"name":"GoogleNews-MidEast",  "url":"https://news.google.com/rss/search?q=middle+east+news&hl=en-US&gl=US&ceid=US:en",        "weight":8},
    {"name":"GoogleNews-Africa",   "url":"https://news.google.com/rss/search?q=africa+news&hl=en-US&gl=US&ceid=US:en",             "weight":7},
    {"name":"GoogleNews-Americas", "url":"https://news.google.com/rss/search?q=latin+america+caribbean+news&hl=en-US&gl=US&ceid=US:en", "weight":7},

    # --- 国内媒体（国际新闻视角） ---
    {"name":"Xinhua-EN",       "url":"https://news.google.com/rss/search?q=site:xinhuanet.com+english&hl=en-US&gl=US&ceid=US:en",   "weight":9},
    {"name":"CGTN",            "url":"https://news.google.com/rss/search?q=site:cgtn.com+world&hl=en-US&gl=US&ceid=US:en",          "weight":9},
    {"name":"GlobalTimes-EN",  "url":"https://news.google.com/rss/search?q=site:globaltimes.cn&hl=en-US&gl=US&ceid=US:en",         "weight":8},
    {"name":"SCMP",            "url":"https://www.scmp.com/rss/91/feed",                                                     "weight":9},
    {"name":"Xinhua-CN-World", "url":"http://www.xinhuanet.com/english/rss/world.xml",                                      "weight":8},

    # --- 主流国际媒体 RSS（长期稳定） ---
    {"name":"BBC",       "url":"https://feeds.bbci.co.uk/news/world/rss.xml",                              "weight":10},
    {"name":"Guardian",  "url":"https://www.theguardian.com/world/rss",                                     "weight":9},
    {"name":"AlJazeera", "url":"https://www.aljazeera.com/xml/rss/all.xml",                                "weight":9},
    {"name":"DW",        "url":"https://rss.dw.com/xml/rss-en-world",                                      "weight":8},
    {"name":"France24",  "url":"https://www.france24.com/en/rss",                                          "weight":8},
    {"name":"NPR-World", "url":"https://feeds.npr.org/1004/rss.xml",                                       "weight":8},
    {"name":"RFI",       "url":"https://en.rfi.fr/rss",                                                    "weight":7},
    {"name":"SkyNews",   "url":"https://feeds.skynews.com/feeds/rss/world.xml",                             "weight":7},
    {"name":"CNBC-World","url":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "weight":7},
    {"name":"ABC-Intl",  "url":"https://abcnews.go.com/abcnews/internationalheadlines.rss",                 "weight":7},
]


# ============================================================
# 翻译
# ============================================================
def _contains_chinese(text):
    """检查文本是否已包含中文字符"""
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False


# 翻译源健康状态：失败一次后自动跳过，避免每次都等超时
_translator_health = {"Google": True, "MyMemory": True, "DeepL": True}


def _try_google_translate(text):
    """翻译源1: Google Translate 免费接口"""
    resp = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "auto", "tl": "zh-CN", "dt": "t", "q": text[:500]},
        timeout=8,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    result = "".join([seg[0] for seg in resp.json()[0] if seg[0]]).strip()
    if result and _contains_chinese(result):
        return result
    return None


def _try_my_memory_translate(text):
    """翻译源2: MyMemory 免费翻译 API（带email提升额度）"""
    resp = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": text[:500], "langpair": "en|zh-CN", "de": "newsbot@daily.com"},
        timeout=8,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    data = resp.json()
    result = data.get("responseData", {}).get("translatedText", "").strip()
    if result and _contains_chinese(result) and "MYMEMORY WARNING" not in result.upper():
        return result
    return None


def _try_deepl_translate(text):
    """翻译源3: DeepL 免费接口（备用）"""
    resp = requests.post(
        "https://api-free.deepl.com/v2/translate",
        data={"text": text[:500], "target_lang": "ZH"},
        timeout=8,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    if resp.status_code == 200:
        translations = resp.json().get("translations", [])
        if translations:
            result = translations[0].get("text", "").strip()
            if result and _contains_chinese(result):
                return result
    return None


def translate_to_zh(text):
    """多源翻译，确保输出中文"""
    if not text or len(text) < 5:
        return text

    # 如果原文已经是中文，直接返回
    if _contains_chinese(text):
        return text

    # 依次尝试 3 个翻译源（已失败的自动跳过）
    translators = [
        ("Google",   _try_google_translate),
        ("MyMemory", _try_my_memory_translate),
        ("DeepL",    _try_deepl_translate),
    ]

    for name, func in translators:
        if not _translator_health[name]:
            continue
        try:
            result = func(text)
            if result:
                return result
            else:
                print("    [翻译源:" + name + "] 无中文结果，跳过")
        except Exception as e:
            err_str = str(e)
            # 连接超时/失败/429限频 → 标记此源不可用，后续直接跳过
            if any(kw in err_str.lower() for kw in ["timeout", "connection", "max retries", "expecting value", "jsondecodeerror"]):
                _translator_health[name] = False
                print("    [翻译源:" + name + "] 不可用（限频/连接失败），后续跳过")
            else:
                print("    [翻译源:" + name + "] 失败: " + err_str)

    # 所有翻译源都失败时的最终保底：截断英文标题，至少不让它太长
    print("    [翻译] 所有源失败，保留原文")
    return text


# ============================================================
# 摘要智能清洗
# ============================================================
# 空洞摘要特征词（这类描述通常只是标题复述或引导语，不含实质信息）
_VAGUE_PATTERNS = [
    re.compile(r"^以下是.{0,20}(的|关于|中).{0,15}(以及|和|将|如何|为什么)", re.IGNORECASE),
    re.compile(r"^(here|what|why|how|this is|read more|learn about|find out)", re.IGNORECASE),
    re.compile(r"^(点击|这里|详见|阅读|请看|查看|更多|以下是|以下是关于)"),
    re.compile(r"^.{0,10}(代价|影响|后果|发展|情况|动态|进展|变化|详情|分析|解读)(。|$|，|,)"),
    re.compile(r"^(在|after|as|following).{0,30}(月|天|周|小时|months?|days?|weeks?|hours?).{0,10}(，|,|$)"),
]

def clean_summary(summary, title):
    """
    清洗翻译后的摘要：
    1. 检测空洞描述 → 返回空（显示时用标题替代）
    2. 去掉HTML标签
    3. 截断过长摘要
    """
    if not summary:
        return ""

    # 去掉 HTML 标签
    summary = re.sub(r"<[^>]+>", "", summary).strip()

    if not summary or len(summary) < 8:
        return ""

    # 检测空洞模式
    for pat in _VAGUE_PATTERNS:
        if pat.search(summary):
            return ""  # 空洞摘要

    # 如果摘要和标题高度重复 → 丢弃摘要
    s_head = summary[:15].strip()
    t_head = title[:15].strip()
    if s_head and t_head and (s_head in t_head or t_head in s_head):
        if len(summary) <= len(title) + 5:
            return ""

    # 截断到200字
    if len(summary) > 200:
        summary = summary[:197] + "..."

    return summary


# ============================================================
# 抓取
# ============================================================
def fetch_rss(source):
    import feedparser
    try:
        resp = requests.get(source["url"], timeout=12, headers={"User-Agent":"Mozilla/5.0"})
        resp.encoding = resp.apparent_encoding
        feed = feedparser.parse(resp.text)
        items = []
        for entry in feed.entries[:12]:
            title   = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()[:300]
            link    = entry.get("link", "")
            pub     = entry.get("published_parsed") or entry.get("updated_parsed")
            pub_dt  = datetime(*pub[:6]) if pub else datetime.now()
            if title:
                items.append({
                    "title":    title,
                    "summary":  summary,
                    "link":     link,
                    "pub_date": pub_dt.strftime("%Y-%m-%d %H:%M"),
                    "source":   source["name"],
                    "weight":   source["weight"],
                })
        print("  [OK] " + source["name"] + ": " + str(len(items)) + " 条")
        return items
    except Exception as e:
        print("  [FAIL] " + source["name"] + ": " + str(e))
        return []


def score_news(news):
    """
    热度评分 v3：
      - 基础分 = 新闻源权重
      - 时效性 = 越新分数越高（12小时内满分，48小时后衰减为0）
      - 讨论度 = 标题/摘要的词频密度（长标题+多关键词命中 = 热）
    """
    try:
        pub = datetime.strptime(news["pub_date"], "%Y-%m-%d %H:%M")
    except Exception:
        pub = datetime.now()

    hours_ago = max(0, (datetime.now() - pub).total_seconds() / 3600)

    # 时效性分数：12小时内满分18，48小时后归零（线性衰减）
    if hours_ago <= 12:
        time_score = 18
    elif hours_ago <= 48:
        time_score = 18 * (1 - (hours_ago - 12) / 36)
    else:
        time_score = 0

    # 讨论度：标题+摘要里的大写单词数（推测为专有名词/热点事件）
    text = (news.get("title", "") + " " + news.get("summary", ""))
    proper_nouns = len(re.findall(r"\b[A-Z][a-z]{2,}\b", text))
    discussion_score = min(proper_nouns * 1.5, 12)  # 上限12分

    # 基础分：新闻源权重
    base_score = news["weight"] * 1.5

    return base_score + time_score + discussion_score


# ============================================================
# 分类
# ============================================================
def _kw_match(kw, text):
    """关键词匹配：英文用全词匹配（\b）避免 war→Warsh 这种子串误命中，中文直接包含"""
    if not kw:
        return False
    # 纯中文/含中文的关键词 → 用 in 包含匹配
    if re.search(r"[\u4e00-\u9fff]", kw):
        return kw in text
    # 英文关键词 → 用单词边界全词匹配，避免 "war" 命中 "Warsh"/"warrant"
    return bool(re.search(r"\b" + re.escape(kw) + r"\b", text))


def classify_news(news):
    text = (news.get("title","") + " " + news.get("summary","")).lower()

    # 默认区域：如果没有匹配到任何关键词，归为"北美"
    default_region_id = "north_america"
    best_region, best_rs = default_region_id, 0
    for r in REGIONS:
        s = sum(1 for kw in r["keywords"] if _kw_match(kw, text))
        if s > best_rs:
            best_rs, best_region = s, r["id"]
    news["region"] = best_region

    # 默认领域：如果没有匹配到任何关键词，归为"外交"
    default_domain_id = "diplomacy"
    best_domain, best_ds = default_domain_id, 0
    for d in DOMAINS:
        s = sum(1 for kw in d["keywords"] if _kw_match(kw, text))
        if s > best_ds:
            best_ds, best_domain = s, d["id"]
    news["domain"] = best_domain

    return news


# ============================================================
# 关键词自动学习扩展
# ============================================================
# 英文停用词（过滤无意义的词）
_STOP_WORDS_EN = set("""
a an the and or of to in for on with by from at as is are was were be been being
this that these those it its they them their there here what which who whom when where why how
will would could should may might can need also very much many more most less only
have has had do does did done hadnt didnt doesnt cant wont shouldnt couldnt mustnt
the of and to a in is it you that he was for on are with his they i we be been has
are this not but have had from she said says have will were been has are my your his her
its our their say says said was were been his her its our their
""".split())

_STOP_WORDS_ZH = set("的是不和了在有着就也这那与或及等对而而且被由"
                     "一个这个那个什么怎么为何如何已经正在可以能够应该")

def _tokenize(text):
    """从英文文本中提取有意义的词（长度>=4，排除停用词）"""
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    return [w for w in words if w not in _STOP_WORDS_EN]


# ============================================================
# 跨推送去重机制：每次推送后记录已推送新闻标题，
# 下次推送时过滤掉已推送过的，确保3次推送内容不重复
# ============================================================
def _get_pushed_path():
    """获取已推送新闻记录文件的路径"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "pushed_news.json")

def load_pushed_titles():
    """加载已推送新闻的标题集合（用于去重）"""
    path = _get_pushed_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # data 格式: {"titles": ["标题1", "标题2", ...], "updated": "2026-06-18"}
            titles = set(data.get("titles", []))
            # 只保留最近24小时内的记录（超过24小时的自动过期，允许旧新闻重新出现）
            updated = data.get("updated", "")
            if updated:
                try:
                    last_push = datetime.strptime(updated, "%Y-%m-%d")
                    # 如果记录超过24小时，清空（新的一天可以推昨天的旧新闻了）
                    if datetime.now() - last_push > timedelta(hours=24):
                        print("[去重] 已推送记录超过24小时，自动清空")
                        return set()
                except ValueError:
                    pass
            print("[去重] 已推送记录: {} 条新闻标题".format(len(titles)))
            return titles
        except Exception:
            pass
    return set()

def save_pushed_titles(titles_set):
    """保存已推送新闻的标题集合到 pushed_news.json"""
    path = _get_pushed_path()
    data = {
        "titles": list(titles_set),
        "updated": datetime.now().strftime("%Y-%m-%d")
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print("[去重] 已保存推送记录: {} 条".format(len(titles_set)))
    except Exception as e:
        print("[去重] 保存失败: " + str(e))


def _load_keyword_cache():
    """从 keywords_cache.json 加载历史上学习到的新关键词"""
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords_cache.json")
    if not os.path.exists(cache_path):
        # 如果缓存文件不存在（首次运行），创建空缓存
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"domains": {}, "regions": {}, "updated": ""}, f, ensure_ascii=False, indent=2)
        return {"domains": {}, "regions": {}, "updated": ""}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        pass
    return {"domains": {}, "regions": {}, "updated": ""}


def _save_keyword_cache(cache):
    """保存学习结果到 keywords_cache.json"""
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords_cache.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print("[学习] 关键词缓存已保存")
    except Exception as e:
        print("[学习] 保存缓存失败: " + str(e))


def reflect_keywords(all_news, domains, regions):
    """
    关键词反思机制：推送完成后自动审查学到的关键词
    - 对每个学到的关键词，统计它在当前分类新闻中的"命中率"
    - 命中率 = 该词出现在该领域/区域新闻中的比例 vs 出现在全部新闻中的比例
    - 如果命中率 < 50%（说明这个词不够专精，分类不准），从关键词和缓存中删除
    """
    cache = _load_keyword_cache()
    removed_count = 0

    # ----- 反思领域关键词 -----
    for d in domains:
        d_id = d["id"]
        learned_kws = cache.get("domains", {}).get(d_id, [])
        if not learned_kws:
            continue

        # 该领域新闻的文本集
        d_news = [n for n in all_news if n.get("domain") == d_id]
        d_texts = [(n.get("title", "") + " " + n.get("summary", "")).lower() for n in d_news]
        # 全部新闻的文本集
        all_texts = [(n.get("title", "") + " " + n.get("summary", "")).lower() for n in all_news]

        to_remove = []
        for kw in learned_kws:
            # 该词在该领域新闻中的命中率
            d_hits = sum(1 for t in d_texts if _kw_match(kw, t))
            d_rate = d_hits / max(len(d_texts), 1)
            # 该词在全部新闻中的命中率
            a_hits = sum(1 for t in all_texts if _kw_match(kw, t))
            a_rate = a_hits / max(len(all_texts), 1)
            # 如果该领域命中率 <= 全体命中率（说明这个词不专精于该领域）
            if d_rate <= a_rate * 1.0 or d_hits < 1:
                to_remove.append(kw)
                print("  [反思·领域:" + d["name"] + "] 删除不恰当关键词: " + kw
                      + " (领域命中率 {:.0%}".format(d_rate) + ", 全体命中率 {:.0%}".format(a_rate) + ")")

        # 从 keywords 列表和缓存中移除
        for kw in to_remove:
            if kw in d["keywords"]:
                d["keywords"].remove(kw)
            removed_count += 1

        # 更新缓存：只保留通过反思的词
        surviving = [kw for kw in learned_kws if kw not in to_remove]
        cache["domains"][d_id] = surviving

    # ----- 反思区域关键词 -----
    for r in regions:
        r_id = r["id"]
        learned_kws = cache.get("regions", {}).get(r_id, [])
        if not learned_kws:
            continue

        r_news = [n for n in all_news if n.get("region") == r_id]
        r_texts = [(n.get("title", "") + " " + n.get("summary", "")).lower() for n in r_news]
        all_texts = [(n.get("title", "") + " " + n.get("summary", "")).lower() for n in all_news]

        to_remove = []
        for kw in learned_kws:
            r_hits = sum(1 for t in r_texts if _kw_match(kw, t))
            r_rate = r_hits / max(len(r_texts), 1)
            a_hits = sum(1 for t in all_texts if _kw_match(kw, t))
            a_rate = a_hits / max(len(all_texts), 1)
            if r_rate <= a_rate * 1.0 or r_hits < 1:
                to_remove.append(kw)
                print("  [反思·区域:" + r["name"] + "] 删除不恰当关键词: " + kw
                      + " (区域命中率 {:.0%}".format(r_rate) + ", 全体命中率 {:.0%}".format(a_rate) + ")")

        for kw in to_remove:
            if kw in r["keywords"]:
                r["keywords"].remove(kw)
            removed_count += 1

        surviving = [kw for kw in learned_kws if kw not in to_remove]
        cache["regions"][r_id] = surviving

    _save_keyword_cache(cache)

    if removed_count > 0:
        print("[反思] 本次共删除 " + str(removed_count) + " 个不恰当关键词")
    else:
        print("[反思] 所有所学关键词均通过审查，无需删除")

    return removed_count


def expand_keywords(all_news, domains, regions, min_freq=2, max_new=15):
    """
    从已分类的新闻中学习新关键词，自动扩充到 domains/regions 的 keywords 里
    - min_freq: 至少在 N 条新闻里出现才考虑加入
    - max_new: 每个领域/区域最多新增 N 个关键词
    """
    cache = _load_keyword_cache()
    today = datetime.now().strftime("%Y-%m-%d")
    new_count = 0

    # ----- 学习领域关键词 -----
    for d in domains:
        d_id = d["id"]
        # 收集该领域所有已分类新闻的文本
        d_news = [n for n in all_news if n.get("domain") == d_id]
        if len(d_news) < 3:
            continue  # 样本太少，跳过

        # 提取所有词
        all_words = []
        for n in d_news:
            text = (n.get("title", "") + " " + n.get("summary", ""))
            all_words.extend(_tokenize(text))

        # 统计词频，过滤已有关键词
        existing_kws = set(kw.lower() for kw in d["keywords"])
        word_counts = Counter(all_words)
        candidates = []
        for word, cnt in word_counts.most_common(80):
            if cnt >= min_freq and word not in existing_kws and len(word) >= 4:
                candidates.append((word, cnt))

        # 取 top 候选，加入 keywords
        added = cache.get("domains", {}).get(d_id, [])
        to_add = []
        for word, cnt in candidates[:max_new]:
            if word not in added and word not in existing_kws:
                to_add.append(word)
                existing_kws.add(word)
                new_count += 1

        if to_add:
            d["keywords"].extend(to_add)
            # 更新缓存
            if "domains" not in cache:
                cache["domains"] = {}
            cache["domains"][d_id] = added + to_add
            print("  [领域:" + d["name"] + "] 新增关键词: " + ", ".join(to_add[:8]) + ("..." if len(to_add) > 8 else ""))

    # ----- 学习区域关键词 -----
    for r in regions:
        r_id = r["id"]
        r_news = [n for n in all_news if n.get("region") == r_id]
        if len(r_news) < 3:
            continue

        all_words = []
        for n in r_news:
            text = (n.get("title", "") + " " + n.get("summary", ""))
            all_words.extend(_tokenize(text))

        existing_kws = set(kw.lower() for kw in r["keywords"])
        word_counts = Counter(all_words)
        added = cache.get("regions", {}).get(r_id, [])
        to_add = []
        for word, cnt in word_counts.most_common(80):
            if cnt >= min_freq and word not in existing_kws and len(word) >= 4 and word not in added:
                to_add.append(word)
                existing_kws.add(word)
                new_count += 1
            if len(to_add) >= max_new:
                break

        if to_add:
            r["keywords"].extend(to_add)
            if "regions" not in cache:
                cache["regions"] = {}
            cache["regions"][r_id] = added + to_add
            print("  [区域:" + r["name"] + "] 新增关键词: " + ", ".join(to_add[:8]) + ("..." if len(to_add) > 8 else ""))

    cache["updated"] = today
    _save_keyword_cache(cache)

    if new_count > 0:
        print("[学习] 本次共新增 " + str(new_count) + " 个关键词")
    else:
        print("[学习] 无新增关键词（已有足够覆盖）")

    return new_count


def apply_cached_keywords(domains, regions):
    """启动时把缓存里学习到的关键词加载进来"""
    cache = _load_keyword_cache()
    count = 0
    for d in domains:
        cached = cache.get("domains", {}).get(d["id"], [])
        for kw in cached:
            if kw not in d["keywords"]:
                d["keywords"].append(kw)
                count += 1
    for r in regions:
        cached = cache.get("regions", {}).get(r["id"], [])
        for kw in cached:
            if kw not in r["keywords"]:
                r["keywords"].append(kw)
                count += 1
    if count > 0:
        print("[学习] 已从缓存加载 " + str(count) + " 个历史关键词")
    return count


def _balanced_select(unique_news, top_n):
    """
    均衡分配算法 v2：确保 10 个区域 + 10 个领域 都有覆盖
    策略：
      1. 先对每条新闻做预分类（只设 region/domain，不修改原数据）
      2. 第一轮：每个区域至少 1 条保底（降低门槛，留名额给领域）
      3. 第二轮：每个未出现的领域补入 1-2 条
      4. 第三轮：强制覆盖——对仍未出现的区域/领域，用最低匹配分数>0的新闻强制归入
      5. 第四轮：剩余名额按热度排序填充
    """
    # 预分类（不修改原始dict）
    classified = []
    for n in unique_news:
        text = (n.get("title","") + " " + n.get("summary","")).lower()
        best_r, best_rs = "north_america", 0
        for r in REGIONS:
            s = sum(1 for kw in r["keywords"] if _kw_match(kw, text))
            if s > best_rs:
                best_rs, best_r = s, r["id"]
        best_d, best_ds = "diplomacy", 0
        for d in DOMAINS:
            s = sum(1 for kw in d["keywords"] if _kw_match(kw, text))
            if s > best_ds:
                best_d, best_ds = d["id"], s
        classified.append((n, best_r, best_d))

    selected = []       # 最终选中
    used_ids = set()    # 已选中的新闻 title[:30] 去重

    def add_news(n, r_id, d_id):
        key = n["title"][:30]
        if key in used_ids:
            return False
        used_ids.add(key)
        n_copy = dict(n)
        n_copy["region"] = r_id
        n_copy["domain"] = d_id
        selected.append(n_copy)
        return True

    # ---- 第一轮：区域保底（每区至少 1 条） ----
    for region in REGIONS:
        r_id = region["id"]
        candidates = [(n, r, d) for (n, r, d) in classified if r == r_id]
        candidates.sort(key=lambda x: x[0]["_score"], reverse=True)
        for n, r, d in candidates[:1]:  # 每区至少1条
            add_news(n, r, d)

    # ---- 第二轮：领域补缺 ----
    covered_domains = set(n["domain"] for n in selected)
    missing_domains = [d for d in DOMAINS if d["id"] not in covered_domains]

    for domain in missing_domains:
        d_id = domain["id"]
        # 在未选中的新闻里找这个领域的（不限区域）
        candidates = [(n, r, d) for (n, r, d) in classified
                      if d == d_id and n["title"][:30] not in used_ids]
        candidates.sort(key=lambda x: x[0]["_score"], reverse=True)
        # 补入 1-2 条（如果有足够的候选）
        for n, r, d in candidates[:2]:
            if len(selected) >= top_n:
                break
            add_news(n, r, d)

    # ---- 第三轮：强制覆盖未出现的区域和领域 ----
    covered_regions = set(n["region"] for n in selected)
    covered_domains = set(n["domain"] for n in selected)
    still_missing_regions = [r for r in REGIONS if r["id"] not in covered_regions]
    still_missing_domains = [d for d in DOMAINS if d["id"] not in covered_domains]

    # 对于仍未出现的区域：找任何新闻中匹配分数>0的，强制归入该区域
    for region in still_missing_regions:
        if len(selected) >= top_n:
            break
        r_id = region["id"]
        # 找未选中的新闻里与该区域关键词匹配分数最高的
        best_candidate = None
        best_match_score = 0
        for n, orig_r, orig_d in classified:
            if n["title"][:30] in used_ids:
                continue
            text = (n.get("title","") + " " + n.get("summary","")).lower()
            r_score = sum(1 for kw in region["keywords"] if _kw_match(kw, text))
            if r_score > best_match_score:
                best_match_score = r_score
                best_candidate = (n, orig_r, orig_d)
        if best_candidate and best_match_score > 0:
            n, orig_r, orig_d = best_candidate
            # 强制归入该区域，领域保持原分类
            add_news(n, r_id, orig_d)
        elif best_candidate:
            # 即使匹配分数=0，也强制归入（宁可覆盖也不要空区域）
            n, orig_r, orig_d = best_candidate
            add_news(n, r_id, orig_d)

    # 对于仍未出现的领域：同理
    covered_domains = set(n["domain"] for n in selected)
    still_missing_domains = [d for d in DOMAINS if d["id"] not in covered_domains]

    for domain in still_missing_domains:
        if len(selected) >= top_n:
            break
        d_id = domain["id"]
        best_candidate = None
        best_match_score = 0
        for n, orig_r, orig_d in classified:
            if n["title"][:30] in used_ids:
                continue
            text = (n.get("title","") + " " + n.get("summary","")).lower()
            d_score = sum(1 for kw in domain["keywords"] if _kw_match(kw, text))
            if d_score > best_match_score:
                best_match_score = d_score
                best_candidate = (n, orig_r, orig_d)
        if best_candidate:
            n, orig_r, orig_d = best_candidate
            # 强制归入该领域，区域保持原分类
            add_news(n, orig_r, d_id)

    # ---- 第四轮：按热度填满剩余名额 ----
    remaining = [(n, r, d) for (n, r, d) in classified
                 if n["title"][:30] not in used_ids]
    remaining.sort(key=lambda x: x[0]["_score"], reverse=True)

    for n, r, d in remaining:
        if len(selected) >= top_n:
            break
        add_news(n, r, d)

    # 输出覆盖统计
    regions_covered = set(n["region"] for n in selected)
    domains_covered = set(n["domain"] for n in selected)
    print("[均衡] 区域覆盖: {}/10, 领域覆盖: {}/10, 总计: {}条".format(
        len(regions_covered), len(domains_covered), len(selected)))

    # 返回 top_n 条（selected）+ 全部已选中含分类信息（用于HTML生成各视图）
    return selected[:top_n], selected


# ============================================================
# 主抓取+翻译+分类流程
# ============================================================
def fetch_and_classify(translate=True):
    print("抓取新闻中...")

    # 启动时加载历史上学习到的关键词
    apply_cached_keywords(DOMAINS, REGIONS)

    # 加载已推送新闻标题（去重）
    pushed_titles = load_pushed_titles()

    all_news = []
    for src in NEWS_SOURCES:
        all_news.extend(fetch_rss(src))

    seen, unique = [], []
    seen_keys = set()
    for n in all_news:
        key = n["title"][:30]
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(n)

    # 去重：过滤掉已经推送过的新闻
    if pushed_titles:
        before_count = len(unique)
        unique = [n for n in unique if n["title"][:30] not in pushed_titles]
        removed = before_count - len(unique)
        print("[去重] 过滤掉 {} 条已推送新闻，剩余 {} 条".format(removed, len(unique)))

    for n in unique:
        n["_score"] = score_news(n)
    unique.sort(key=lambda x: x["_score"], reverse=True)

    # 取候选池（TOP_N * 3 保证有足够多的新闻供均衡分配挑选）
    pool = unique[:TOP_N * 3]

    if translate:
        print("翻译中（{} 条）...".format(len(pool)))
        for i, n in enumerate(pool, 1):
            print("  {}/{}: {}...".format(i, len(pool), n["title"][:35]))
            n["title"]   = translate_to_zh(n["title"])
            n["summary"] = translate_to_zh(n["summary"])
            # 翻译后清洗摘要
            n["summary"] = clean_summary(n["summary"], n["title"])

    print("均衡分配中...")
    top_news, balanced_all = _balanced_select(pool, TOP_N)

    # 从已分类的新闻中学习新关键词，自动扩充
    print("关键词学习中...")
    expand_keywords(balanced_all, DOMAINS, REGIONS)

    # 反思机制：审查学到的关键词，删除不恰当的
    print("关键词反思中...")
    reflect_keywords(balanced_all, DOMAINS, REGIONS)

    # 保存本次推送的新闻标题到去重记录
    for n in top_news:
        pushed_titles.add(n["title"][:30])
    save_pushed_titles(pushed_titles)

    return top_news, balanced_all


# ============================================================
# 生成 HTML（使用 str.format 避免 % 转义问题）
# ============================================================
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#1a1a1a}
.header{background:linear-gradient(135deg,#1a237e,#283593,#3949ab);color:#fff;padding:28px 16px;text-align:center}
.header h1{font-size:22px;margin-bottom:6px}
.header .sub{font-size:14px;opacity:.85}
.stats{display:flex;gap:10px;justify-content:center;margin-top:14px;flex-wrap:wrap}
.stat-item{background:rgba(255,255,255,.15);border-radius:8px;padding:5px 12px;font-size:13px}
.tab-nav{display:flex;background:#fff;padding:0 16px;position:sticky;top:0;z-index:99;border-bottom:1px solid #eee;overflow-x:auto}
.tab-btn{flex:none;padding:12px 16px;font-size:14px;font-weight:600;color:#888;border:none;background:none;cursor:pointer;white-space:nowrap;border-bottom:3px solid transparent;transition:.2s}
.tab-btn.active{color:#1a237e;border-bottom-color:#1a237e}
.tab-pane{display:none;padding:16px}
.tab-pane.active{display:block}
.news-card{background:#fff;border-radius:14px;padding:16px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.card-header{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.rank-badge{background:#1a237e;color:#fff;border-radius:50%;width:26px;height:26px;text-align:center;line-height:26px;font-size:13px;font-weight:700;flex-shrink:0}
.top-badge{color:#fff;font-size:11px;font-weight:700;padding:3px 8px;border-radius:20px}
.news-title{font-size:16px;font-weight:700;line-height:1.5;margin-bottom:8px}
.news-summary{font-size:13px;color:#555;line-height:1.6;margin-bottom:10px}
.news-tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.tag{font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600}
.region-tag{background:#e8eaf6;color:#3949ab}
.domain-tag{border:1px solid;background:transparent}
.source-tag{background:#f3f4f6;color:#555}
.time-tag{color:#999;background:none;padding:0}
.heat-bar{background:#eee;border-radius:4px;height:6px;margin-bottom:12px;overflow:hidden}
.heat-fill{background:linear-gradient(90deg,#e53935,#fb8c00);height:100%;border-radius:4px}
.read-btn{display:block;text-align:center;background:#1a237e;color:#fff;border-radius:8px;padding:9px;text-decoration:none;font-size:14px;font-weight:600}
.region-section{background:#fff;border-radius:14px;padding:14px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.region-header{display:flex;align-items:center;gap:8px;margin-bottom:12px;padding-bottom:10px;border-bottom:2px solid #eee}
.region-icon{font-size:20px}
.region-name{font-size:16px;font-weight:700;color:#1a237e;flex:1}
.region-count{background:#e8eaf6;color:#3949ab;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:600}
.region-item{padding:10px 0;border-bottom:1px solid #f5f5f5}
.region-item:last-child{border-bottom:none}
.ri-domain{display:inline-block;color:#fff;font-size:11px;padding:2px 8px;border-radius:20px;margin-bottom:5px;font-weight:600}
.ri-title{display:block;font-size:14px;font-weight:600;color:#1a1a1a;text-decoration:none;line-height:1.5;margin-bottom:4px}
.ri-title:hover{color:#1a237e}
.ri-meta{font-size:12px;color:#999}
.domain-section{background:#fff;border-radius:14px;padding:14px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.domain-header{display:flex;align-items:center;gap:8px;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid #eee}
.domain-icon{font-size:20px}
.domain-name{font-size:16px;font-weight:700;flex:1;color:#333}
.domain-count{background:#f3f4f6;color:#555;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:600}
.domain-item{padding:10px 0;border-bottom:1px solid #f5f5f5;display:flex;flex-direction:column;gap:4px}
.domain-item:last-child{border-bottom:none}
.di-region{font-size:11px;color:#888}
.di-title{font-size:14px;font-weight:600;color:#1a1a1a;text-decoration:none;line-height:1.5}
.di-title:hover{color:#1a237e}
.di-source{font-size:12px;color:#aaa}
.region-stats{background:#fff;border-radius:14px;padding:16px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.region-stats h3{font-size:14px;color:#888;margin-bottom:12px}
.rstat-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.rstat{display:flex;justify-content:space-between;align-items:center;background:#f8f9fa;border-radius:8px;padding:8px 12px;font-size:13px}
.rstat b{color:#1a237e;font-size:16px}
.footer{text-align:center;padding:20px;color:#999;font-size:12px}
"""

JS = """
function showTab(id,btn){
  document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
  window.scrollTo(0,0);
}
"""

def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def generate_html(top_news, all_news, output_path):
    today   = datetime.now().strftime("%Y年%m月%d日")
    weekday = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"][datetime.now().weekday()]

    region_map = {r["id"]: r for r in REGIONS}
    domain_map = {d["id"]: d for d in DOMAINS}

    # ---- TOP 20 热度榜 ----
    top_cards = []
    for i, n in enumerate(top_news, 1):
        score     = n.get("_score", 0)
        bar_w     = min(100, int(score * 2.5))
        badge     = ""
        if i <= 3:
            badge_colors = ["#e53935","#fb8c00","#fdd835"]
            badge = '<span class="top-badge" style="background:{c}">TOP {n}</span>'.format(c=badge_colors[i-1], n=i)

        region = region_map.get(n.get("region",""), {})
        domain = domain_map.get(n.get("domain",""), {})
        r_label = "{icon} {name}".format(icon=region.get("icon","🌐"), name=region.get("name","未知"))
        d_label = "{icon} {name}".format(icon=domain.get("icon","📌"), name=domain.get("name","综合"))
        d_color = domain.get("color","#555")

        summary_html = ""
        if n.get("summary") and len(n["summary"].strip()) > 0:
            summary_html = '<p class="news-summary">{summary}</p>'.format(summary=esc(n["summary"]))

        top_cards.append("""
        <div class="news-card">
          <div class="card-header">
            <div class="rank-badge">{rank}</div>
            {badge}
          </div>
          <h2 class="news-title">{title}</h2>
          {summary_html}
          <div class="news-tags">
            <span class="tag region-tag">{rlabel}</span>
            <span class="tag domain-tag" style="border-color:{dc};color:{dc}">{dlabel}</span>
            <span class="tag source-tag">{source}</span>
            <span class="tag time-tag">{date}</span>
          </div>
          <div class="heat-bar"><div class="heat-fill" style="width:{bw}%"></div></div>
          <a href="{link}" class="read-btn" target="_blank">阅读原文</a>
        </div>""".format(
            rank=i, badge=badge,
            title=esc(n["title"]), summary_html=summary_html,
            rlabel=r_label, dlabel=d_label, dc=d_color,
            source=esc(n["source"]), date=esc(n["pub_date"]),
            bw=bar_w, link=esc(n["link"])
        ))

    # ---- 区域视图 ----
    region_sections = []
    for region in REGIONS:
        r_news = [x for x in all_news if x.get("region") == region["id"]][:5]
        if not r_news:
            continue
        items = []
        for n in r_news:
            d = domain_map.get(n.get("domain",""), {})
            items.append("""
            <div class="region-item">
              <div class="ri-domain" style="background:{dc}">{dicon} {dname}</div>
              <a href="{link}" class="ri-title" target="_blank">{title}</a>
              <div class="ri-meta">{src} &nbsp;·&nbsp; {date}</div>
            </div>""".format(
                dc=d.get("color","#555"), dicon=d.get("icon","📌"), dname=d.get("name","综合"),
                link=esc(n["link"]), title=esc(n["title"]),
                src=esc(n["source"]), date=esc(n["pub_date"])
            ))
        region_sections.append("""
        <div class="region-section">
          <div class="region-header">
            <span class="region-icon">{icon}</span>
            <span class="region-name">{name}</span>
            <span class="region-count">{cnt} 条</span>
          </div>
          <div>{items}</div>
        </div>""".format(icon=region["icon"], name=region["name"], cnt=len(r_news), items="".join(items)))

    # ---- 领域视图 ----
    domain_sections = []
    for domain in DOMAINS:
        d_news = [x for x in all_news if x.get("domain") == domain["id"]][:4]
        if not d_news:
            continue
        items = []
        for n in d_news:
            r = region_map.get(n.get("region",""), {})
            items.append("""
            <div class="domain-item">
              <span class="di-region">{ricon} {rname}</span>
              <a href="{link}" class="di-title" target="_blank">{title}</a>
              <span class="di-source">{src}</span>
            </div>""".format(
                ricon=r.get("icon","🌐"), rname=r.get("name","未知"),
                link=esc(n["link"]), title=esc(n["title"]), src=esc(n["source"])
            ))
        domain_sections.append("""
        <div class="domain-section" style="border-top:3px solid {dc}">
          <div class="domain-header">
            <span class="domain-icon">{icon}</span>
            <span class="domain-name">{name}</span>
            <span class="domain-count">{cnt} 条</span>
          </div>
          <div>{items}</div>
        </div>""".format(dc=domain["color"], icon=domain["icon"], name=domain["name"],
                         cnt=len(d_news), items="".join(items)))

    # ---- 统计 ----
    rstat_items = []
    for region in REGIONS:
        cnt = sum(1 for x in all_news if x.get("region") == region["id"])
        rstat_items.append('<div class="rstat"><span>{icon}{name}</span><b>{cnt}</b></div>'.format(
            icon=region["icon"], name=region["name"], cnt=cnt))

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>国际时政日报 · {today}</title>
<style>{css}</style>
</head>
<body>
<div class="header">
  <h1>🌍 国际时政日报</h1>
  <div class="sub">{today} &nbsp; {weekday}</div>
  <div class="stats">
    <div class="stat-item">📊 10 大区域</div>
    <div class="stat-item">🏷️ 10 个领域</div>
    <div class="stat-item">🤖 AI翻译</div>
    <div class="stat-item">🔥 热度排序</div>
  </div>
</div>
<div class="tab-nav">
  <button class="tab-btn active" onclick="showTab('hot',this)">🔥 热度榜</button>
  <button class="tab-btn" onclick="showTab('region',this)">🌏 按区域</button>
  <button class="tab-btn" onclick="showTab('domain',this)">🏷️ 按领域</button>
  <button class="tab-btn" onclick="showTab('overview',this)">📊 覆盖统计</button>
</div>
<div id="hot" class="tab-pane active">{top_cards}</div>
<div id="region" class="tab-pane">{region_sections}</div>
<div id="domain" class="tab-pane">{domain_sections}</div>
<div id="overview" class="tab-pane">
  <div class="region-stats">
    <h3>各区域新闻条数</h3>
    <div class="rstat-grid">{rstat_items}</div>
  </div>
</div>
<div class="footer">WorkBuddy 自动抓取 · AI翻译 · 热度排序 · 每日早上8:00更新</div>
<script>{js}</script>
</body>
</html>""".format(
        today=today, weekday=weekday, css=CSS, js=JS,
        top_cards="\n".join(top_cards),
        region_sections="\n".join(region_sections),
        domain_sections="\n".join(domain_sections),
        rstat_items="\n".join(rstat_items),
    )

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("[HTML] 已生成: " + output_path)


# ============================================================
# 微信推送
# ============================================================
def send_wechat(news_list, article_url):
    url_token = ("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential"
                 "&appid=" + WECHAT_APPID + "&secret=" + WECHAT_APPSECRET)
    resp = requests.get(url_token, timeout=10).json()
    if "access_token" not in resp:
        raise Exception("获取token失败: " + str(resp))
    token = resp["access_token"]

    today   = datetime.now().strftime("%Y年%m月%d日")
    preview = "\n".join(["• " + n["title"][:28] for n in news_list[:3]])

    payload = {
        "touser":      WECHAT_OPENID,
        "template_id": WECHAT_TEMPLATE_ID,
        "url":         article_url,
        "data": {
            "title":   {"value": "国际时政日报", "color": "#1a73e8"},
            "date":    {"value": today,          "color": "#666666"},
            "preview": {"value": preview,         "color": "#333333"},
            "remark":  {"value": "点击查看完整内容（10大区域·10个领域）→", "color": "#07c160"},
        }
    }
    url_send = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=" + token
    return requests.post(url_send, json=payload, timeout=10).json()


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 50)
    print("国际时政日报 v5 - 每天3次推送·跨次去重·国内媒体源")
    print("=" * 50)

    top_news, all_news = fetch_and_classify(translate=True)

    output_dir  = os.environ.get("OUTPUT_DIR", "docs")
    output_path = os.path.join(output_dir, "index.html")
    generate_html(top_news, all_news, output_path)

    if all([WECHAT_APPID, WECHAT_APPSECRET, WECHAT_OPENID, WECHAT_TEMPLATE_ID]):
        print("发送微信模板消息...")
        result = send_wechat(top_news, GITHUB_PAGES_URL)
        if result.get("errcode", -1) == 0:
            print("[微信] 推送成功！")
        else:
            print("[微信] 推送结果: " + str(result))
    else:
        print("[跳过] 微信配置不完整")

    print("\n完成！TOP 3 新闻:")
    for i, n in enumerate(top_news[:3], 1):
        print("  " + str(i) + ". " + n["title"][:50])


if __name__ == "__main__":
    main()
