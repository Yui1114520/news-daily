#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions 版国际时政新闻推送脚本
每天自动抓取新闻、翻译成中文、生成HTML、推送微信
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta

# ============================================================
# 配置（从环境变量读取，GitHub Secrets 注入）
# ============================================================
WECHAT_APPID     = os.environ.get("WECHAT_APPID", "")
WECHAT_APPSECRET = os.environ.get("WECHAT_APPSECRET", "")
WECHAT_OPENID    = os.environ.get("WECHAT_OPENID", "")
WECHAT_TEMPLATE_ID = os.environ.get("WECHAT_TEMPLATE_ID", "")
GITHUB_PAGES_URL = os.environ.get("GITHUB_PAGES_URL", "https://yui1114520.github.io/news-daily/")

# RSS 新闻源
NEWS_SOURCES = [
    {"name": "BBC",       "url": "https://feeds.bbci.co.uk/news/world/rss.xml",        "weight": 10},
    {"name": "Reuters",   "url": "https://feeds.reuters.com/reuters/topNews",          "weight": 10},
    {"name": "AlJazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml",           "weight": 9},
    {"name": "Guardian",   "url": "https://www.theguardian.com/world/rss",               "weight": 9},
    {"name": "France24",   "url": "https://www.france24.com/en/rss",                    "weight": 8},
    {"name": "NYTimes",    "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "weight": 9},
    {"name": "Bloomberg",  "url": "https://www.bloomberg.com/feed/podcast/etf-iq.xml", "weight": 8},
]

TOP_N = 20

# ============================================================
# 免费翻译（Google Translate 非官方API，无需key）
# ============================================================
def translate_to_zh(text: str) -> str:
    """用 Google Translate 免费接口翻译（无需 API Key）"""
    if not text or len(text) < 5:
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "zh-CN",
            "dt": "t",
            "q": text[:500]   # 限制长度，避免超长
        }
        resp = requests.get(url, params=params, timeout=10)
        result = resp.json()
        # 返回格式: [[[翻译结果, 原文, ...]]]
        translated = "".join([seg[0] for seg in result[0] if seg[0]])
        return translated.strip()
    except Exception as e:
        print(f"[翻译失败] {e}，使用原文")
        return text


# ============================================================
# 抓取新闻
# ============================================================
def fetch_rss(source: dict) -> list:
    import feedparser
    try:
        resp = requests.get(source["url"], timeout=15)
        resp.encoding = resp.apparent_encoding
        feed = feedparser.parse(resp.text)
        items = []
        for entry in feed.entries[:10]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")[:200]
            link = entry.get("link", "")
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            pub_dt = datetime(*pub[:6]) if pub else datetime.now()
            items.append({
                "title": title,
                "summary": summary,
                "link": link,
                "pub_date": pub_dt.strftime("%Y-%m-%d %H:%M"),
                "source": source["name"],
                "weight": source["weight"],
            })
        print(f"  [OK] {source['name']}: {len(items)} 条")
        return items
    except Exception as e:
        print(f"  [失败] {source['name']}: {e}")
        return []


def score_news(news: dict) -> float:
    """热度评分：来源权重 + 时效性"""
    try:
        pub = datetime.strptime(news["pub_date"], "%Y-%m-%d %H:%M")
    except Exception:
        pub = datetime.now()
    hours_ago = (datetime.now() - pub).total_seconds() / 3600
    time_score = max(0, 20 - hours_ago / 2)
    return news["weight"] * 2 + time_score


def fetch_top_news(translate: bool = True) -> list:
    print("开始抓取新闻...")
    all_news = []
    for src in NEWS_SOURCES:
        all_news.extend(fetch_rss(src))

    # 去重（按标题）
    seen = set()
    unique = []
    for n in all_news:
        key = n["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(n)

    # 评分排序
    for n in unique:
        n["_score"] = score_news(n)
    unique.sort(key=lambda x: x["_score"], reverse=True)

    top = unique[:TOP_N]

    # 翻译
    if translate:
        print("开始翻译成中文...")
        for i, n in enumerate(top, 1):
            print(f"  翻译 {i}/{len(top)}: {n['title'][:30]}...")
            n["title_zh"]   = translate_to_zh(n["title"])
            n["summary_zh"] = translate_to_zh(n["summary"])
        # 翻译完成后，把中文替换成主字段
        for n in top:
            n["title"]   = n.get("title_zh", n["title"])
            n["summary"] = n.get("summary_zh", n["summary"])

    print(f"完成！共 {len(top)} 条新闻")
    return top


# ============================================================
# 生成 HTML 文章页
# ============================================================
def generate_html(news_list: list, output_path: str):
    today = datetime.now().strftime("%Y年%m月%d日")
    weekday = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"][datetime.now().weekday()]

    cards_html = ""
    for i, n in enumerate(news_list, 1):
        score = n.get("_score", 0)
        bar_width = min(100, int(score * 2))
        top_badge = ""
        if i <= 3:
            colors = ["#ff4444","#ff8800","#ffcc00"]
            labels  = ["TOP 1","TOP 2","TOP 3"]
            top_badge = f'<div class="top-badge" style="background:{colors[i-1]}">{labels[i-1]}</div>'

        cards_html += f'''
        <div class="news-card">
            {top_badge}
            <div class="rank">No.{i}</div>
            <div class="card-body">
                <h2 class="news-title">{n["title"]}</h2>
                <p class="news-summary">{n["summary"]}</p>
                <div class="news-meta">
                    <span class="source-tag">{n["source"]}</span>
                    <span class="pub-date">📅 {n["pub_date"]}</span>
                </div>
                <div class="heat-bar">
                    <div class="heat-fill" style="width:{bar_width}%"></div>
                    <span class="heat-label">热度 {score:.1f}</span>
                </div>
                <a href="{n["link"]}" class="read-btn" target="_blank">📖 阅读原文</a>
            </div>
        </div>
        '''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🌍 国际时政日报 · {today}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f0f2f5;
    color: #1a1a1a;
    padding: 16px;
  }}
  .header {{
    background: linear-gradient(135deg, #1a237e 0%, #283593 50%, #3949ab 100%);
    color: white;
    border-radius: 16px;
    padding: 28px 20px;
    text-align: center;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(26,35,126,0.3);
  }}
  .header h1 {{ font-size: 22px; margin-bottom: 8px; }}
  .header .sub {{ font-size: 14px; opacity: 0.85; }}
  .stats {{
    display: flex; gap: 12px; justify-content: center;
    margin-top: 14px; flex-wrap: wrap;
  }}
  .stat-item {{
    background: rgba(255,255,255,0.15); border-radius: 8px;
    padding: 6px 14px; font-size: 13px;
  }}
  .news-card {{
    background: white; border-radius: 14px; padding: 18px;
    margin-bottom: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    position: relative; overflow: hidden;
  }}
  .top-badge {{
    position: absolute; top: 0; right: 0;
    color: white; font-size: 11px; font-weight: bold;
    padding: 4px 10px; border-radius: 0 14px 0 10px;
  }}
  .rank {{
    display: inline-block; background: #1a237e; color: white;
    border-radius: 50%; width: 28px; height: 28px;
    text-align: center; line-height: 28px; font-size: 13px;
    font-weight: bold; margin-bottom: 10px;
  }}
  .news-title {{ font-size: 16px; font-weight: 700; line-height: 1.5; margin-bottom: 8px; }}
  .news-summary {{ font-size: 14px; color: #555; line-height: 1.6; margin-bottom: 10px; }}
  .news-meta {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }}
  .source-tag {{
    background: #e8eaf6; color: #3949ab; border-radius: 4px;
    padding: 2px 8px; font-size: 12px; font-weight: 600;
  }}
  .pub-date {{ font-size: 12px; color: #999; }}
  .heat-bar {{
    background: #eee; border-radius: 4px; height: 18px;
    position: relative; margin-bottom: 12px; overflow: hidden;
  }}
  .heat-fill {{
    background: linear-gradient(90deg, #ff6b6b, #ffa502);
    height: 100%; border-radius: 4px; transition: width 0.5s;
  }}
  .heat-label {{ position: absolute; right: 6px; top: 0; font-size: 11px; color: #666; line-height: 18px; }}
  .read-btn {{
    display: block; text-align: center; background: #1a237e; color: white;
    border-radius: 8px; padding: 8px; text-decoration: none;
    font-size: 14px; font-weight: 600;
  }}
  .read-btn:hover {{ background: #283593; }}
  .footer {{
    text-align: center; padding: 20px; color: #999; font-size: 13px;
  }}
</style>
</head>
<body>
<div class="header">
  <h1>🌍 国际时政日报</h1>
  <div class="sub">{today} {weekday}</div>
  <div class="stats">
    <div class="stat-item">📊 共 {len(news_list)} 条新闻</div>
    <div class="stat-item">🔥 按热度排序</div>
    <div class="stat-item">🤖 AI自动翻译</div>
  </div>
</div>

{cards_html}

<div class="footer">
  WorkBuddy 自动抓取 · AI翻译 · 热度排序<br>
  每日早上 8:00 自动更新
</div>
</body>
</html>'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[HTML] 已生成: {output_path}")


# ============================================================
# 微信推送
# ============================================================
def get_access_token() -> str:
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APPID}&secret={WECHAT_APPSECRET}"
    resp = requests.get(url, timeout=10).json()
    if "access_token" not in resp:
        raise Exception(f"获取token失败: {resp}")
    return resp["access_token"]


def send_wechat(news_list: list, article_url: str) -> dict:
    token = get_access_token()
    preview = "\n".join([f"• {n['title'][:25]}..." for n in news_list[:3]])
    today = datetime.now().strftime("%Y年%m月%d日")

    payload = {
        "touser": WECHAT_OPENID,
        "template_id": WECHAT_TEMPLATE_ID,
        "url": article_url,
        "data": {
            "title":    {"value": "🌍 国际时政日报", "color": "#1a73e8"},
            "date":     {"value": today,                "color": "#666666"},
            "preview":  {"value": preview,              "color": "#333333"},
            "remark":   {"value": "点击查看完整20条新闻 →", "color": "#07c160"},
        }
    }
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    return requests.post(url, json=payload, timeout=10).json()


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 50)
    print("国际时政新闻日报 - GitHub Actions 版")
    print("=" * 50)

    # Step 1: 抓取 + 翻译
    news_list = fetch_top_news(translate=True)

    # Step 2: 生成 HTML
    output_dir  = os.environ.get("OUTPUT_DIR", "docs")
    output_path = os.path.join(output_dir, "index.html")
    os.makedirs(output_dir, exist_ok=True)
    generate_html(news_list, output_path)

    # Step 3: 推送微信
    if not all([WECHAT_APPID, WECHAT_APPSECRET, WECHAT_OPENID, WECHAT_TEMPLATE_ID]):
        print("[警告] 微信配置不完整，跳过推送")
        print("请设置 GitHub Secrets: WECHAT_APPID, WECHAT_APPSECRET, WECHAT_OPENID, WECHAT_TEMPLATE_ID")
    else:
        print("发送微信模板消息...")
        result = send_wechat(news_list, GITHUB_PAGES_URL)
        if result.get("errcode", -1) == 0:
            print("[微信] 推送成功！")
        else:
            print(f"[微信] 推送失败: {result}")
            # 如果是 access_token 相关错误，打印更多信息
            if result.get("errcode") == 40001:
                print("  → appid 或 appsecret 可能有误，请检查 GitHub Secrets")

    print("完成！")
    return news_list[:3]


if __name__ == "__main__":
    main()
