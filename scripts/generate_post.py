#!/usr/bin/env python3
"""
Zadz Blog — Gerador Automático de Posts Semanais (v2)
Busca notícias de tráfego pago via RSS (sem API key, 100% gratuito)
"""

import json
import re
import sys
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import textwrap
import os

# Pillow para geração de imagens — instale com: pip install pillow
try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False
    print("⚠️  Pillow não instalado. Imagens não serão geradas. Execute: pip install pillow")

# deep-translator para tradução pt-BR — instale com: pip install deep-translator
try:
    from deep_translator import GoogleTranslator
    TRANSLATE_OK = True
except ImportError:
    TRANSLATE_OK = False
    print("⚠️  deep-translator não instalado. Execute: pip install deep-translator")
from datetime import datetime, timedelta, timezone

# ── FEEDS RSS (atualizados e testados) ────────────────────────────────────
RSS_FEEDS = [
    ("Search Engine Land",        "https://searchengineland.com/feed"),
    ("Search Engine Journal",     "https://www.searchenginejournal.com/feed/"),
    ("Neil Patel",                "https://neilpatel.com/blog/feed/"),
    ("HubSpot Marketing",         "https://blog.hubspot.com/marketing/rss.xml"),
    ("Social Media Examiner",     "https://www.socialmediaexaminer.com/feed/"),
    ("Marketing Land / Martech",  "https://martech.org/feed/"),
    ("WordStream",                "https://www.wordstream.com/blog/feed"),
    ("PPC Hero",                  "https://www.ppchero.com/feed/"),
    ("Jon Loomer Digital",        "https://www.jonloomer.com/feed/"),
    ("Semrush Blog",              "https://www.semrush.com/blog/feed/"),
]

# Palavras-chave relevantes para tráfego pago
KEYWORDS = [
    # Plataformas
    "google ads", "meta ads", "facebook ads", "instagram ads", "tiktok ads",
    "linkedin ads", "microsoft ads", "bing ads", "pinterest ads", "youtube ads",
    "amazon ads",
    # Tipos de campanha
    "performance max", "pmax", "demand gen", "smart campaign", "shopping ads",
    "display ads", "search ads", "discovery ads",
    # Termos técnicos
    "smart bidding", "target roas", "target cpa", "maximize conversions",
    "remarketing", "retargeting", "lookalike", "custom audience",
    "paid search", "paid social", "ppc", "sem",
    "cpc", "cpm", "cpa", "roas", "roi", "ad spend",
    "quality score", "ad rank", "impression share",
    "conversion tracking", "pixel", "gtag", "ga4",
    "landing page", "lead generation",
    "audience targeting", "segmentation",
    "ad creative", "ad copy", "call to action",
    # PT-BR
    "tráfego pago", "anúncios pagos", "gestão de tráfego",
    "campanha paga", "mídia paga", "links patrocinados",
    # Gerais relevantes
    "advertising", "campaign optimization",
    "click-through rate", "ctr", "cost per click",
    "return on ad spend", "ad performance",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

def detect_language(text):
    """Detecta se o texto está em inglês verificando palavras comuns."""
    if not text:
        return "unknown"
    en_markers = [
        "the ", " and ", " for ", " with ", " from ", " this ", " that ",
        " are ", " is ", " was ", " will ", " your ", " has ", " have ",
        " how ", " what ", " when ", " new ", " ads ", " ad ", " google ",
    ]
    text_lower = text.lower()
    hits = sum(1 for m in en_markers if m in text_lower)
    return "en" if hits >= 2 else "pt"

def translate_text(text, max_chars=450):
    """Traduz um texto para pt-BR. Retorna o original se a tradução falhar."""
    if not text or not TRANSLATE_OK:
        return text
    # Só traduz se detectar inglês
    if detect_language(text) != "en":
        return text
    try:
        # Limita o tamanho para evitar erro de quota
        chunk = text[:max_chars]
        translated = GoogleTranslator(source="auto", target="pt").translate(chunk)
        return translated or text
    except Exception as e:
        print(f"  ⚠️  Erro na tradução: {e}")
        return text
    
def translate_article(article):
    """Traduz título e resumo de um artigo para pt-BR."""
    article["title"]   = translate_text(article["title"])
    article["summary"] = translate_text(article["summary"])
    return article

def generate_cover_image(post_id, title, tags):
    """Gera uma imagem de capa 1200x630 para o post e salva em og-images/."""
    if not PILLOW_OK:
        return None

    os.makedirs("og-images", exist_ok=True)
    W, H = 1200, 630

    # Fundo degradê escuro
    img  = Image.new("RGB", (W, H), "#080B10")
    draw = ImageDraw.Draw(img)

    # Faixa de brilho lateral esquerda (accent #00E5FF)
    for i in range(300):
        alpha = int(30 * (1 - i / 300))
        draw.line([(i, 0), (i, H)], fill=(0, 229, 255, alpha))

    # Barra superior accent
    draw.rectangle([(0, 0), (W, 6)], fill="#00E5FF")

    # Fontes — tenta DejaVu (disponível no Ubuntu/GitHub Actions), fallback padrão
    try:
        font_logo  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 62)
        font_tags  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except:
        font_logo  = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_tags  = ImageFont.load_default()

    # Logo ZADZ
    draw.text((72, 48), "ZADZ", font=font_logo, fill="#00E5FF")

    # Título do post com quebra automática de linha
    clean_title = title.replace("📰 ", "").replace("Novidades de Tráfego Pago — ", "")
    wrapped     = textwrap.fill(clean_title[:100], width=22)
    draw.multiline_text((72, 140), wrapped, font=font_title, fill="#E8EDF5", spacing=16)

    # Tags na parte inferior
    tag_text = "  ·  ".join(tags[:3]) if tags else "Tráfego Pago"
    draw.text((72, H - 80), tag_text, font=font_tags, fill="#6B7A8D")

    # Linha separadora antes das tags
    draw.line([(72, H - 100), (W - 72, H - 100)], fill="#1a2535", width=1)

    path = f"og-images/{post_id}.png"
    img.save(path, "PNG", optimize=True)
    print(f"  🖼️  Imagem gerada: {path}")
    return "/" + path


def fetch_feed(name, url):
    """Faz o download e parseia um feed RSS com múltiplas estratégias."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        print(f"  ⚠️  HTTP {e.code} em {name}")
        return []
    except Exception as e:
        print(f"  ⚠️  Erro ao buscar {name}: {type(e).__name__}")
        return []

    # Remove namespaces problemáticos antes de parsear
    raw_str = raw.decode("utf-8", errors="replace")
    raw_str = re.sub(r' xmlns[^"]*"[^"]*"', '', raw_str)
    raw_str = re.sub(r"<\?xml[^>]+>", "", raw_str)

    try:
        root = ET.fromstring(raw_str)
    except ET.ParseError as e:
        print(f"  ⚠️  XML inválido em {name}: {e}")
        return []

    items = []
    entries = root.findall(".//item")
    is_atom = False

    if not entries:
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        is_atom = True

    for entry in entries:
        if is_atom:
            title_el = entry.find("{http://www.w3.org/2005/Atom}title")
            link_el  = entry.find("{http://www.w3.org/2005/Atom}link")
            sum_el   = (entry.find("{http://www.w3.org/2005/Atom}summary") or
                        entry.find("{http://www.w3.org/2005/Atom}content"))
            pub_el   = (entry.find("{http://www.w3.org/2005/Atom}published") or
                        entry.find("{http://www.w3.org/2005/Atom}updated"))

            title   = (title_el.text or "").strip() if title_el is not None else ""
            link    = link_el.get("href", "") if link_el is not None else ""
            summary = (sum_el.text or "").strip() if sum_el is not None else ""
            pub     = (pub_el.text or "").strip() if pub_el is not None else ""
        else:
            def get_text(tag):
                el = entry.find(tag)
                return (el.text or "").strip() if el is not None else ""

            title   = get_text("title")
            link    = get_text("link")
            pub     = get_text("pubDate") or get_text("date")
            desc    = get_text("description") or get_text("summary")
            summary = re.sub(r"<[^>]+>", "", desc)

        summary = re.sub(r"<[^>]+>", " ", summary)
        summary = re.sub(r"\s+", " ", summary).strip()[:500]

        if not title or not link:
            continue

        items.append({
            "source": name,
            "title": title,
            "link": link.strip(),
            "summary": summary,
            "pub": pub,
        })

    print(f"  ✅ {name}: {len(items)} artigos encontrados")
    return items


def parse_date(pub_str):
    """Tenta converter uma string de data em objeto datetime."""
    if not pub_str:
        return None
    pub_str = pub_str.strip()
    pub_str = re.sub(r"\s+(GMT|UTC|EST|PST|CST|MST|EDT|PDT|CDT|MDT)$", " +0000", pub_str)

    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d %b %Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(pub_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def score_relevance(title, summary):
    """Retorna score de relevância. Título tem peso dobrado."""
    text = (title + " " + summary).lower()
    score = 0
    for kw in KEYWORDS:
        if kw in text:
            score += 2 if kw in title.lower() else 1
    return score


def load_posts(path="posts.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_posts(posts, path="posts.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def generate_post(articles, week_str, today_str):
    """Monta o objeto de post a partir dos artigos coletados."""
    sources_seen = set()
    sources = []
    for a in articles:
        if a["link"] not in sources_seen:
            sources_seen.add(a["link"])
            sources.append({"title": a["title"][:80], "url": a["link"]})

    all_text = " ".join(a["title"] + " " + a["summary"] for a in articles).lower()
    auto_tags = []
    tag_map = {
        "Google Ads":   ["google ads", "pmax", "performance max", "demand gen", "shopping ads"],
        "Meta Ads":     ["meta ads", "facebook ads", "instagram ads", "advantage+", "meta"],
        "TikTok Ads":   ["tiktok ads", "tiktok"],
        "LinkedIn Ads": ["linkedin ads", "linkedin"],
        "Estratégia":   ["strategy", "estratégia", "bidding", "smart bidding", "roas", "cpa", "optimization"],
        "Automação":    ["automation", "automação", "ai", "machine learning", "smart", "automated"],
        "Novidades":    ["update", "new", "launch", "feature", "announcing", "novo", "novidade"],
        "Criativos":    ["creative", "criativo", "ad copy", "headline", "video ad"],
    }
    for tag, kws in tag_map.items():
        if any(kw in all_text for kw in kws):
            auto_tags.append(tag)
    if not auto_tags:
        auto_tags = ["Tráfego Pago", "Novidades"]

    destaques = "\n".join(
        f"• {a['title']} [{a['source']}]" for a in articles[:8]
    )

    detalhes = []
    for a in articles[:5]:
        resumo = a['summary'][:250].rstrip() + "..." if len(a['summary']) > 250 else a['summary']
        detalhes.append(f"🔹 {a['title']}\n{resumo}")

    content = f"""Esta semana trouxe novidades importantes no universo de tráfego pago. Reunimos os principais destaques para você se manter atualizado e à frente da concorrência.

📌 DESTAQUES DA SEMANA:

{destaques}

━━━━━━━━━━━━━━━━━━━━━━

{chr(10).join(detalhes)}

━━━━━━━━━━━━━━━━━━━━━━

Acompanhe as fontes abaixo para se aprofundar em cada tema. Toda semana a Zadz traz uma nova curadoria com o que há de mais relevante no mundo de performance e tráfego pago.

🚀 Precisa de ajuda para aplicar essas novidades nas suas campanhas? Fale com a Zadz!"""

    summary = (
        f"Curadoria semanal com {len(articles)} destaques do mundo de tráfego pago: "
        f"Google Ads, Meta Ads, estratégias e muito mais."
    )

    post_id = f"{today_str}-semana-{hashlib.md5(week_str.encode()).hexdigest()[:6]}"

    image_path = generate_cover_image(
    post_id,
    f"📰 Novidades de Tráfego Pago — {week_str}",
    auto_tags
)
    return {
        "id": post_id,
        "title": f"📰 Novidades de Tráfego Pago — {week_str}",
        "date": today_str,
        "summary": summary,
        "content": content,
        "tags": auto_tags[:4],
        "image": image_path,
        "sources": sources[:8],
    }


def main():
    print("=" * 55)
    print("🚀 Zadz Blog — Gerador de Posts v2")
    print("=" * 55)

    posts = load_posts()
    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")

    # Verifica se já existe post recente (menos de 6 dias)
    for p in posts:
        try:
            post_date = datetime.strptime(p.get("date", ""), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (today - post_date).days < 6:
                print(f"✅ Post recente já existe ({p['date']}). Nada a fazer.")
                sys.exit(0)
        except ValueError:
            continue

    week_str = today.strftime("%d/%m/%Y")
    cutoff = today - timedelta(days=14)

    print(f"\n📡 Buscando artigos (últimos 14 dias)...\n")
    all_articles = []

    for name, url in RSS_FEEDS:
        items = fetch_feed(name, url)
        for item in items:
            pub_dt = parse_date(item["pub"])
            if pub_dt and pub_dt < cutoff:
                continue
            score = score_relevance(item["title"], item["summary"])
            if score > 0:
                item["score"] = score
                all_articles.append(item)

    print(f"\n📊 Artigos relevantes encontrados: {len(all_articles)}")

    # Se poucos artigos, amplia para 30 dias
    if len(all_articles) < 5:
        print("⚠️  Poucos artigos. Ampliando janela para 30 dias...\n")
        cutoff = today - timedelta(days=30)
        all_articles = []
        for name, url in RSS_FEEDS:
            items = fetch_feed(name, url)
            for item in items:
                pub_dt = parse_date(item["pub"])
                if pub_dt and pub_dt < cutoff:
                    continue
                score = score_relevance(item["title"], item["summary"])
                if score > 0:
                    item["score"] = score
                    all_articles.append(item)
        print(f"\n📊 Artigos após ampliar janela: {len(all_articles)}")

    if len(all_articles) < 2:
        print("\n❌ Artigos insuficientes. Post não gerado.")
        sys.exit(0)

    # Deduplica e ordena por relevância
    seen = set()
    unique = []
    for a in sorted(all_articles, key=lambda x: x.get("score", 0), reverse=True):
        if a["link"] not in seen:
            seen.add(a["link"])
            unique.append(a)

    print(f"✅ {len(unique)} artigos únicos selecionados")
    print("\n🏆 Top 5 mais relevantes:")
    for a in unique[:5]:
        print(f"   [{a.get('score',0)} pts] {a['title'][:65]}")

    new_post = generate_post(unique[:10], week_str, today_str)
    posts.insert(0, new_post)
    save_posts(posts)

    print(f"\n✅ Post gerado com sucesso!")
    print(f"   Título : {new_post['title']}")
    print(f"   Tags   : {new_post['tags']}")
    print(f"   Fontes : {len(new_post['sources'])}")
    print("=" * 55)


if __name__ == "__main__":
    main()