# 📰 Blog Zadz — Guia de Configuração

Solução **100% gratuita** de blog com atualização automática semanal sobre tráfego pago.

---

## 📁 Arquivos criados

```
seu-repo/
├── blog.html                          ← Página do blog
├── posts.json                         ← Posts (atualizado automaticamente)
├── scripts/
│   └── generate_post.py               ← Script de geração de posts
└── .github/
    └── workflows/
        └── weekly-blog.yml            ← Automação semanal (GitHub Actions)
```

---

## 🚀 Passo a passo de configuração

### 1. Adicionar os arquivos ao seu repositório

Copie todos os arquivos acima para o seu repositório GitHub mantendo a mesma estrutura de pastas.

### 2. Ativar o GitHub Actions

1. Abra seu repositório no GitHub
2. Clique na aba **"Actions"** (menu superior)
3. Se aparecer um aviso, clique em **"I understand my workflows, go ahead and enable them"**

✅ Pronto! O GitHub Actions já está ativo.

### 3. Linkar a página no seu site

No seu HTML principal (index.html ou onde preferir), adicione o link para o blog:

```html
<a href="/blog.html">Blog</a>
```

### 4. Testar manualmente (opcional)

Para não esperar até segunda-feira, você pode rodar o workflow manualmente:

1. Vá na aba **Actions** do seu repositório
2. Clique em **"📰 Atualização Semanal do Blog Zadz"** no menu lateral
3. Clique em **"Run workflow"** → **"Run workflow"** (botão verde)
4. Aguarde ~1 minuto
5. O Netlify detecta o novo commit e faz o deploy automático!

---

## ⚙️ Como funciona (sem nenhuma API key)

```
Toda Segunda-Feira às 10h (Brasília)
           ↓
GitHub Actions acorda o script Python
           ↓
Script lê RSS de 7 sites de marketing (gratuito)
   • Search Engine Land
   • Search Engine Journal  
   • Google Ads Blog
   • Neil Patel Blog
   • WordStream Blog
   • Marketing Land
           ↓
Filtra artigos sobre tráfego pago da última semana
           ↓
Gera um post curado e adiciona ao posts.json
           ↓
Faz commit automático no GitHub
           ↓
Netlify detecta o commit e faz deploy
           ↓
Blog atualizado! ✅
```

---

## 🎨 Personalização

### Mudar o horário de publicação

Edite `.github/workflows/weekly-blog.yml`:

```yaml
# Toda segunda às 10h (Brasília)
- cron: '0 13 * * 1'

# Toda quarta às 9h (Brasília)
- cron: '0 12 * * 3'

# Todo sábado às 8h (Brasília)
- cron: '0 11 * * 6'
```

### Adicionar mais feeds RSS

Edite `scripts/generate_post.py` e adicione na lista `RSS_FEEDS`:

```python
RSS_FEEDS = [
    # Já incluídos...
    ("Nome do Blog", "https://url-do-feed-rss/feed"),
]
```

### Adicionar um post manualmente

Edite `posts.json` e adicione um objeto no início da lista:

```json
[
  {
    "id": "2025-04-01-meu-post",
    "title": "Título do meu post",
    "date": "2025-04-01",
    "summary": "Resumo curto que aparece no card.",
    "content": "Conteúdo completo do post.\n\nPode ter múltiplos parágrafos.",
    "tags": ["Google Ads", "Estratégia"],
    "sources": [
      { "title": "Nome da fonte", "url": "https://link.com" }
    ]
  },
  ... posts anteriores ...
]
```

---

## ❓ Perguntas frequentes

**O Netlify precisa de alguma configuração especial?**  
Não. Se o Netlify já está conectado ao seu repositório GitHub, ele detecta automaticamente qualquer novo commit e faz o deploy.

**Preciso de conta paga no GitHub?**  
Não. GitHub Actions é gratuito para repositórios públicos e também para privados (até 2.000 minutos/mês — o script usa menos de 1 minuto por semana).

**E se uma semana não tiver notícias relevantes?**  
O script verifica se há pelo menos 2 artigos antes de publicar. Se não encontrar, não cria post (evita posts vazios).

**Posso rodar o script no meu computador para testar?**  
Sim! Com Python instalado:
```bash
pip install feedparser
python scripts/generate_post.py
```

---

© Zadz Agência — Blog automatizado com GitHub Actions + RSS
