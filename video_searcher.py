import argparse
import csv
import os

from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Busca vídeos no YouTube e exporta CSV de candidatos."
    )
    parser.add_argument(
        "--terms",
        type=str,
        required=True,
        help='Termos de busca separados por vírgula. Ex: "emagrecimento,como perder peso"',
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Número máximo de resultados por termo (máx 50). Padrão: 50.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="candidatos.csv",
        help="Caminho do arquivo CSV de saída. Padrão: candidatos.csv",
    )
    return parser.parse_args()


def build_youtube_client():
    """Cria o cliente da YouTube Data API v3 usando a chave de ambiente."""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "A variável de ambiente YOUTUBE_API_KEY não está definida. "
            "Defina-a antes de executar o script."
        )
    return build("youtube", "v3", developerKey=api_key)


def search_videos(youtube, term, max_results):
    """Busca vídeos para um termo e retorna lista de video_ids."""
    request = youtube.search().list(
        part="snippet",
        type="video",
        q=term,
        maxResults=max_results,
        order="relevance",
    )
    response = request.execute()
    video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
    return video_ids


def get_video_details(youtube, video_ids):
    """Obtém detalhes (statistics + snippet) para uma lista de video_ids."""
    if not video_ids:
        return []

    videos = []
    # A API aceita no máximo 50 ids por chamada
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        request = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(batch),
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item["snippet"]
            statistics = item.get("statistics", {})
            thumbnails = snippet.get("thumbnails", {})
            # Priorizar thumbnail de alta resolução
            thumbnail_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url", "")
            )
            videos.append(
                {
                    "video_id": item["id"],
                    "titulo": snippet.get("title", ""),
                    "canal": snippet.get("channelTitle", ""),
                    "data_publicacao": snippet.get("publishedAt", ""),
                    "visualizacoes": int(statistics.get("viewCount", 0)),
                    "url_thumbnail": thumbnail_url,
                    "aprovado": False,
                }
            )
    return videos


def export_csv(videos, output_path):
    """Exporta lista de vídeos para CSV UTF-8 com cabeçalho."""
    fieldnames = [
        "video_id",
        "titulo",
        "canal",
        "data_publicacao",
        "visualizacoes",
        "url_thumbnail",
        "aprovado",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(videos)


def main():
    args = parse_args()

    terms = [t.strip() for t in args.terms.split(",")]
    max_results = min(args.max_results, 50)  # YouTube API limita a 50

    youtube = build_youtube_client()

    # Dicionário para deduplicação por video_id
    seen_ids = set()
    all_videos = []

    for term in terms:
        try:
            video_ids = search_videos(youtube, term, max_results)

            if not video_ids:
                print(f"Termo com zero resultados: '{term}'")
                continue

            # Filtrar ids já vistos para deduplicação
            new_ids = [vid for vid in video_ids if vid not in seen_ids]

            if not new_ids:
                continue

            details = get_video_details(youtube, new_ids)

            for video in details:
                if video["video_id"] not in seen_ids:
                    seen_ids.add(video["video_id"])
                    all_videos.append(video)

        except Exception as e:
            print(f"Erro ao buscar termo '{term}': {e}")
            continue

    export_csv(all_videos, args.output)
    print(f"CSV exportado: {args.output} ({len(all_videos)} vídeos)")


if __name__ == "__main__":
    main()
