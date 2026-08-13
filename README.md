## Como Rodar

### Pré-requisitos

```bash
pip install -r requirements.txt
```

Você também precisará de uma chave da YouTube Data API v3 configurada como variável de ambiente (`YOUTUBE_API_KEY`).

### 1. Buscar vídeos

```bash
python video_searcher.py --terms "emagrecimento,como perder peso,dieta para emagrecer" --max-results 50 --output data/candidatos.csv
```
### 2. Curadoria manual

Abra `data/candidatos.csv` em um editor de planilhas (Excel, Google Sheets, etc.) e marque `True` na coluna `aprovado` para os vídeos que devem compor o corpus.

### 3. Extrair transcrições

```bash
python transcript_extractor.py --input data/candidatos.csv --output data/transcricoes.csv
```