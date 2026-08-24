import os
import csv
import argparse
import yt_dlp # biblioteca de download principal
import subprocess
import glob # para encontrar o vídeo independente da extensão

def configurar_diretorios_video(video_id):
    """Cria a estrutura de pastas isolada para um vídeo específico."""
    base_dir = f"output/{video_id}"
    os.makedirs(f"{base_dir}/frames", exist_ok=True)
    return base_dir

def baixar_midias(video_id, extrair_subs=False):
    """Baixa o áudio e o vídeo base usando regras de formato mais flexíveis."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    base_dir = configurar_diretorios_video(video_id)
    
    # 1. Configuração de Áudio: Se não achar só áudio, baixa o pior vídeo e arranca o áudio
    opcoes_audio = {
        'format': 'bestaudio/best/worst',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{base_dir}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt', # LÊ INSTANTANEAMENTE (Crie o arquivo na mesma pasta)
    }

    if extrair_subs:
        opcoes_audio.update({
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['pt'],
            'subtitlesformat': 'srt',
        })

    # 2. Configuração de Vídeo: Tenta pior mp4, depois pior webm, depois qualquer pior formato
    opcoes_video = {
        'format': 'worstvideo[ext=mp4]/worstvideo/worst', 
        'outtmpl': f'{base_dir}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt', 
    }

    print(f"[{video_id}] Baixando áudio" + (" e legendas..." if extrair_subs else "..."))
    with yt_dlp.YoutubeDL(opcoes_audio) as ydl:
        ydl.download([url])

    print(f"[{video_id}] Baixando vídeo (fallback dinâmico)...")
    with yt_dlp.YoutubeDL(opcoes_video) as ydl:
        ydl.download([url])

def extrair_frames(video_id, fps_desejado="1/10"):
    """Encontra dinamicamente o arquivo de vídeo baixado e extrai os frames."""
    base_dir = f"output/{video_id}"
    padrao_saida = f"{base_dir}/frames/frame_%04d.jpg"

    # Busca qualquer arquivo no diretório raiz do vídeo que não seja texto ou áudio
    arquivos_na_pasta = glob.glob(f"{base_dir}/{video_id}.*")
    caminho_video = None
    
    for arquivo in arquivos_na_pasta:
        # Ignora arquivos de áudio, legendas e as próprias imagens
        if not arquivo.endswith(('.mp3', '.srt', '.vtt', '.jpg', '.m4a')):
            caminho_video = arquivo
            break

    if not caminho_video:
        print(f"[{video_id}] Aviso: Nenhum arquivo de vídeo encontrado para extrair frames.")
        return

    extensao = caminho_video.split('.')[-1]
    print(f"[{video_id}] Extraindo frames do arquivo .{extensao} (taxa: {fps_desejado})...")
    
    comando = [
        "ffmpeg",
        "-i", caminho_video,
        "-vf", f"fps={fps_desejado}",
        "-q:v", "2",
        padrao_saida
    ]

    try:
        subprocess.run(comando, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print(f"[{video_id}] Frames extraídos com sucesso!")
        
        # Deleta o vídeo original (seja mp4, webm ou mkv)
        os.remove(caminho_video)
        print(f"[{video_id}] Vídeo original (.{extensao}) deletado.")
            
    except subprocess.CalledProcessError:
        print(f"[{video_id}] Erro no FFmpeg. Pulando extração.")

def processar_video(video_id, extrair_subs):
    """Função orquestradora."""
    print(f"\n--- Iniciando processamento: {video_id} ---")
    try:
        baixar_midias(video_id, extrair_subs)
        extrair_frames(video_id)
    except Exception as e:
        print(f"[{video_id}] Falha ao processar: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrator Multimodal do YouTube")
    parser.add_argument("--id", type=str, help="ID único do vídeo")
    parser.add_argument("--csv", type=str, help="Caminho para o CSV")
    parser.add_argument("--limit", type=int, help="Quantidade máxima de vídeos", default=None)
    parser.add_argument("--subs", action="store_true", help="Baixa também a legenda .srt")
    
    args = parser.parse_args()
 
    if args.id:
        processar_video(args.id, args.subs)
        
    elif args.csv:
        if not os.path.exists(args.csv):
            print(f"Erro: O arquivo {args.csv} não foi encontrado.")
            exit(1)
            
        print(f"Lendo base de dados: {args.csv}")
        with open(args.csv, mode='r', encoding='utf-8') as arquivo_csv:
            leitor = csv.DictReader(arquivo_csv, delimiter=',') 
            videos_processados = 0
            for linha in leitor:
                if args.limit and videos_processados >= args.limit:
                    break
                video_id = linha.get('Video_id') or linha.get('video_id')
                if video_id:
                    processar_video(video_id, args.subs)
                    videos_processados += 1
                    
    else:
        parser.print_help()