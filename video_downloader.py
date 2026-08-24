import os
import csv
import argparse
import yt_dlp
import subprocess

def configurar_diretorios_video(video_id):
    """Cria a estrutura de pastas isolada para um vídeo específico."""
    base_dir = f"output/{video_id}"
    
    # Cria apenas a pasta de frames. O áudio, legenda e o vídeo ficarão na raiz (base_dir)
    os.makedirs(f"{base_dir}/frames", exist_ok=True)
        
    return base_dir

def baixar_midias(video_id, extrair_subs=False):
    """Baixa o áudio e o vídeo base, com opção de incluir a transcrição (.srt)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    base_dir = configurar_diretorios_video(video_id)
    
    opcoes_audio = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{base_dir}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True
    }

    # Injeta as opções de legenda caso o argumento seja passado
    if extrair_subs:
        opcoes_audio.update({
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['pt'],  # Prioriza Português e Inglês
            'subtitlesformat': 'srt',
        })

    opcoes_video = {
        'format': 'worstvideo[ext=mp4]', 
        'outtmpl': f'{base_dir}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True
    }

    print(f"[{video_id}] Baixando áudio" + (" e legendas..." if extrair_subs else "..."))
    with yt_dlp.YoutubeDL(opcoes_audio) as ydl:
        ydl.download([url])

    print(f"[{video_id}] Baixando vídeo...")
    with yt_dlp.YoutubeDL(opcoes_video) as ydl:
        ydl.download([url])

def extrair_frames(video_id, fps_desejado="1/10"):
    """Extrai os frames usando FFmpeg e limpa o arquivo de vídeo original."""
    base_dir = f"output/{video_id}"
    caminho_video = f"{base_dir}/{video_id}.mp4"
    padrao_saida = f"{base_dir}/frames/frame_%04d.jpg"

    print(f"[{video_id}] Extraindo frames (taxa: {fps_desejado})...")
    
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
        
        if os.path.exists(caminho_video):
            os.remove(caminho_video)
            print(f"[{video_id}] Vídeo original (mp4) deletado para economizar espaço.")
            
    except subprocess.CalledProcessError:
        print(f"[{video_id}] Erro no FFmpeg. Pulando extração.")

def processar_video(video_id, extrair_subs):
    """Função orquestradora que executa todo o pipeline para um ID."""
    print(f"\n--- Iniciando processamento: {video_id} ---")
    try:
        baixar_midias(video_id, extrair_subs)
        extrair_frames(video_id)
    except Exception as e:
        print(f"[{video_id}] Falha ao processar: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrator Multimodal do YouTube (Áudio, Frames e Legendas)")
    parser.add_argument("--id", type=str, help="ID único do vídeo para download individual")
    parser.add_argument("--csv", type=str, help="Caminho para o arquivo CSV de entrada")
    parser.add_argument("--limit", type=int, help="Quantidade máxima de vídeos para processar do CSV", default=None)    
    parser.add_argument("--subs", action="store_true", help="Baixa também a transcrição/legenda em .srt")
    
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
                    print(f"\nLimite de {args.limit} vídeo(s) atingido. Encerrando.")
                    break
                
                video_id = linha.get('video_id')
                if video_id:
                    processar_video(video_id, args.subs)
                    videos_processados += 1
                else:
                    print("Aviso: Linha sem 'Video_id' encontrada, pulando...")
                    
    else:
        print("Uso incorreto. Forneça --id <VIDEO_ID> ou --csv <CAMINHO_DO_CSV>")
        parser.print_help()