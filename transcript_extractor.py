
import argparse
import csv

from youtube_transcript_api import YouTubeTranscriptApi

# Instância única reutilizada em todas as extrações
ytt_api = YouTubeTranscriptApi()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extrai transcrições de vídeos aprovados e exporta CSV."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Caminho do CSV de candidatos (com coluna 'aprovado').",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="transcricoes.csv",
        help="Caminho do arquivo CSV de saída. Padrão: transcricoes.csv",
    )
    return parser.parse_args()


def load_approved_videos(input_path):
    """Lê o CSV de candidatos e retorna apenas os vídeos com aprovado == True."""
    approved = []
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("aprovado", "").strip().lower() == "true":
                approved.append(row)
    return approved


def extract_transcript(video_id):
    """
    Extrai transcrição em português para um vídeo.

    Usa ytt_api.fetch() com languages=['pt', 'pt-BR'], que já faz fallback
    de legendas manuais para automáticas nativamente.

    Retorna tupla (transcricao, idioma).
    Se não houver legenda em português, retorna ("sem_transcrição", "sem_transcrição").
    """
    try:
        fetched = ytt_api.fetch(video_id, languages=["pt", "pt-BR"])
        text = " ".join(snippet.text for snippet in fetched)
        return text, "pt"
    except Exception:
        return "sem_transcrição", "sem_transcrição"


def export_csv(results, output_path):
    """Exporta lista de resultados para CSV UTF-8 com cabeçalho."""
    fieldnames = ["video_id", "titulo", "transcricao", "idioma"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    args = parse_args()

    approved_videos = load_approved_videos(args.input)

    if not approved_videos:
        print("Nenhum vídeo aprovado encontrado no CSV. Encerrando sem gerar arquivo de saída.")
        return

    print(f"{len(approved_videos)} vídeo(s) aprovado(s) encontrado(s). Iniciando extração...")

    results = []
    error_count = 0

    for video in approved_videos:
        video_id = video["video_id"]
        titulo = video.get("titulo", "")

        try:
            transcricao, idioma = extract_transcript(video_id)
        except Exception as e:
            print(f"Erro ao extrair transcrição do vídeo '{video_id}': {e}")
            transcricao = "erro_api"
            idioma = "erro_api"
            error_count += 1

        results.append(
            {
                "video_id": video_id,
                "titulo": titulo,
                "transcricao": transcricao,
                "idioma": idioma,
            }
        )

    export_csv(results, args.output)
    print(f"CSV exportado: {args.output} ({len(results)} vídeos)")

    if error_count > 0:
        print(f"Total de erros durante a extração: {error_count}")


if __name__ == "__main__":
    main()
