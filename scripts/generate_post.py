#!/usr/bin/env python3
"""
Zadz Blog — Gerador Automático de Posts Semanais
Busca notícias de tráfego pago via RSS (sem API key, 100% gratuito)
e adiciona um novo post ao posts.json
"""

import json
import re
import sys
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# ── FEEDS RSS ──────────────────────────────────────────────────────────────
RSS_FEEDS = [
    # Google / Search
    ("Search Engine Land — Paid Search", "https://searchengineland.com/category/google-ads/feed"),
    ("Search Engine Journal — Paid Search", "https://www.searchenginejournal.com/category/paid-search/feed/"),
    ("Search Engine Journal — Paid Social", "https://www.searchenginejournal.com/category/paid-social/feed/"),
    # Google oficial
    ("Google Ads Blog", "https://blog.google/products/ads/rss/"),
    # Neil Patel
    ("Neil Patel Blog", "https://neilpatel.com/blog/feed/"),
    # WordStream
    ("WordStream Blog", "https://www.wordstream.com/blog/feed"),
    # Marketing Land
    ("Marketing Land", "https://martech.org/feed/"),
]

# Palavras-chave relevantes para tráfego pago (PT + EN)
KEYWORDS = [
    "google ads", "meta ads", "facebook ads", "instagram ads", "tiktok ads",
    "performance max", "pmax", "smart bidding", "remarketing", "retargeting",
    "paid search", "paid social", "ppc", "cpc", "cpm", "roas", "cpa",
    "tráfego pago", "anúncios", "campaign", "bidding", "audience", "targeting",
    "shopping ads", "display ads", "youtube ads", "demand gen",
    "conversion", "landing page", "ad spend", "budget", "roi",
]

def fetch_feed(name, url):
    """Faz o download e parseia um feed RSS."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ZadzBlogBot/1.0)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)
    except Exception as e:
        print(f"  ⚠️  Erro ao buscar {name}: {e}")
        return []

    items = []
    # Suporta RSS 2.0 e Atom
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall(".//item") or root.findall(".//atom:entry", ns)

    for entry in entries:
        def get(tag, default=""):
            el = entry.find(tag) or entry.find(f"atom:{tag}", ns)
            return (el.text or "").strip() if el is not None else default

        title   = get("title")
        link    = get("link") or (entry.find("atom:link", ns) or entry).get("href", "")
        summary = re.sub(r"<[^>]+>", "", get("description") or get("summary"))[:400]
        pub     = get("pubDate") or get("published") or get("updated")

        if not title or not link:
            continue

        items.append({
            "source": name,
            "title": title,
            "link": link.strip(),
            "summary": summary.strip(),
            "pub": pub,
        })

    return items


def parse_date(pub_str):
    """Tenta converter uma string de data em objeto datetime."""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(pub_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def is_relevant(title, summary):
    """Verifica se o artigo é relevante para tráfego pago."""
    text = (title + " " + summary).lower()
    return any(kw in text for kw in KEYWORDS)


def load_posts(path="posts.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_posts(posts, path="posts.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def post_id_exists(posts, post_id):
    return any(p.get("id") == post_id for p in posts)


def generate_post(articles, week_str, today_str):
    """Monta o objeto de post a partir dos artigos coletados."""
    # Agrupa as fontes únicas
    sources_seen = set()
    sources = []
    for a in articles:
        if a["link"] not in sources_seen:
            sources_seen.add(a["link"])
            sources.append({"title": a["title"][:80], "url": a["link"]})

    # Detecta tags automaticamente
    all_text = " ".join(a["title"] + " " + a["summary"] for a in articles).lower()
    auto_tags = []
    tag_map = {
        "Google Ads": ["google ads", "pmax", "performance max", "demand gen", "shopping ads"],
        "Meta Ads": ["meta ads", "facebook ads", "instagram ads", "advantage+"],
        "TikTok Ads": ["tiktok ads", "tiktok"],
        "Estratégia": ["strategy", "estratégia", "bidding", "smart bidding", "roas", "cpa"],
        "Automação": ["automation", "automação", "ai", "machine learning", "smart"],
        "Novidades": ["update", "new", "launch", "feature", "announcing", "novo", "novidade"],
    }
    for tag, kws in tag_map.items():
        if any(kw in all_text for kw in kws):
            auto_tags.append(tag)

    if not auto_tags:
        auto_tags = ["Tráfego Pago", "Novidades"]

    # Monta o conteúdo do post
    headline_items = "\n".join(
        f"• {a['title']} [{a['source']}]" for a in articles[:6]
    )

    content = f"""Esta semana trouxe novidades importantes no universo de tráfego pago. Reunimos os principais destaques para você se manter atualizado.

📌 DESTAQUES DA SEMANA:

{headline_items}

---

{chr(10).join(f"🔹 {a['title']}%0A{a['summary'][:220]}..." for a in articles[:5])}

---

Acompanhe as fontes abaixo para se aprofundar em cada tema e fique de olho no nosso blog — toda semana trazemos uma nova curadoria com o que há de mais relevante no mundo de performance e tráfego pago.
""".replace("%0A", "\n")

    summary = f"Curadoria semanal com os {len(articles)} principais artigos e atualizações do mundo de tráfego pago: Google Ads, Meta Ads e muito mais."

    post_id = f"{today_str}-semana-{hashlib.md5(week_str.encode()).hexdigest()[:6]}"

    return {
        "id": post_id,
        "title": f"📰 Novidades de Tráfego Pago — {week_str}",
        "date": today_str,
        "summary": summary,
        "content": content,
        "tags": auto_tags[:4],
        "sources": sources[:8],
    }


def main():
    print("🚀 Zadz Blog — Buscando novidades de tráfego pago...\n")

    # Carrega posts existentes
    posts = load_posts()
    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")
    week_ago = today - timedelta(days=7)

    # Verifica se já existe post desta semana
    week_str = today.strftime("Semana %d/%m/%Y")
    post_id = f"{today_str}-semana-"
    if any(p.get("id", "").startswith(post_id[:16]) for p in posts):
        print("✅ Já existe um post para esta semana. Nada a fazer.")
        sys.exit(0)

    # Coleta artigos dos feeds
    all_articles = []
    for name, url in RSS_FEEDS:
        print(f"  📡 Buscando: {name}...")
        items = fetch_feed(name, url)
        for item in items:
            pub_dt = parse_date(item["pub"]) if item["pub"] else None
            # Aceita artigos da última semana (ou sem data)
            if pub_dt and pub_dt < week_ago:
                continue
            if is_relevant(item["title"], item["summary"]):
                all_articles.append(item)

    print(f"\n  ✅ {len(all_articles)} artigos relevantes encontrados.\n")

    if len(all_articles) < 2:
        print("⚠️  Poucos artigos encontrados. Post não gerado.")
        sys.exit(0)

    # Deduplica por URL
    seen = set()
    unique_articles = []
    for a in all_articles:
        if a["link"] not in seen:
            seen.add(a["link"])
            unique_articles.append(a)

    # Gera o novo post
    new_post = generate_post(unique_articles[:10], week_str, today_str)

    # Adiciona ao início da lista
    posts.insert(0, new_post)

    # Salva
    save_posts(posts)
    print(f"✅ Post salvo: {new_post['title']}")
    print(f"   Tags: {new_post['tags']}")
    print(f"   Fontes: {len(new_post['sources'])}")


if __name__ == "__main__":
    main()
