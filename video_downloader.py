import os
import csv
import argparse
import yt_dlp # biblioteca de download principal
import subprocess
import glob # para encontrar o vídeo independente da extensão

#TODO: adicionar detecção de vídeo 

def verificar_disponibilidade_legendas(video_id):
    """
    Verifica quais tipos de legenda em português (manual e/ou automática) 
    estão disponíveis para o vídeo. Retorna um dicionário com booleans.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    disponiveis = {"manual": False, "automatic": False}
    try:
        resultado = subprocess.check_output(
            ["yt-dlp", "--list-subs", url], 
            stderr=subprocess.STDOUT, 
            universal_newlines=True
        )
        saida = resultado.lower()
        
        # Verifica se há legendas manuais em PT
        if "available subtitles" in saida:
            partes = saida.split("available subtitles")
            secao_manual = partes[1].split("available automatic captions")[0] if "available automatic captions" in partes[1] else partes[1]
            if "pt" in secao_manual or "portuguese" in secao_manual:
                disponiveis["manual"] = True
                
        # Verifica se há legendas automáticas em PT
        if "available automatic captions" in saida:
            secao_auto = saida.split("available automatic captions")[1]
            if "pt" in secao_auto or "portuguese" in secao_auto:
                disponiveis["automatic"] = True
                
    except subprocess.CalledProcessError:
        pass
    
    return disponiveis

def configurar_diretorios_video(video_id):
    """Cria a estrutura de pastas isolada para um vídeo específico."""
    base_dir = f"output/{video_id}"
    os.makedirs(f"{base_dir}/frames", exist_ok=True)
    return base_dir

def baixar_midias(video_id, extrair_subs=False):
    """Baixa o áudio, vídeo base e gerencia o download de ambas as legendas."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    base_dir = configurar_diretorios_video(video_id)
    
    status_subs = {"manual": False, "automatic": False}
    if extrair_subs:
        status_subs = verificar_disponibilidade_legendas(video_id)
        encontrou_alguma = any(status_subs.values())
        if not encontrou_alguma:
            print(f"[{video_id}] Nenhuma legenda em português encontrada.")

    # 1. Configuração de Áudio e Legendas
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
        'cookiefile': 'cookies.txt',
        'writethumbnail': True,
    }

    if extrair_subs and any(status_subs.values()):
        opcoes_audio.update({
            'writesubtitles': status_subs["manual"],
            'writeautomaticsub': status_subs["automatic"],
            'subtitleslangs': ['pt'],
            'subtitlesformat': 'srt',
        })

    opcoes_video = {
        'format': 'worstvideo[ext=mp4]/worstvideo/worst', 
        'outtmpl': f'{base_dir}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt', 
    }

    print(f"[{video_id}] Baixando áudio, thumbnail" + (" e legendas disponíveis..." if (extrair_subs and any(status_subs.values())) else "..."))
    with yt_dlp.YoutubeDL(opcoes_audio) as ydl:
        ydl.download([url])

        arquivos_srt = glob.glob(f"{base_dir}/{video_id}*.srt") + glob.glob(f"{base_dir}/{video_id}*.vtt")
        
        for arquivo in arquivos_srt:
            if "manual_" in arquivo or "automatic_" in arquivo:
                continue

            nome_arquivo_baixo = os.path.basename(arquivo)
            
            if "auto" in nome_arquivo_baixo.lower() or (status_subs["automatic"] and not status_subs["manual"]):
                novo_nome = f"{base_dir}/automatic_{video_id}.srt"
            else:
                novo_nome = f"{base_dir}/manual_{video_id}.srt"
                
            if arquivo.endswith('.vtt'):
                novo_nome = novo_nome.replace('.srt', '.vtt')

            if os.path.exists(novo_nome):
                os.remove(novo_nome)
            
            os.rename(arquivo, novo_nome)
            print(f"[{video_id}] Legenda processada: {os.path.basename(novo_nome)}")

    print(f"[{video_id}] Baixando vídeo (fallback dinâmico)...")
    with yt_dlp.YoutubeDL(opcoes_video) as ydl:
        ydl.download([url])

def extrair_frames(video_id, fps_desejado="1/10"):
    """Encontra dinamicamente o arquivo de vídeo baixado e extrai os frames."""
    base_dir = f"output/{video_id}"
    pasta_frames = f"{base_dir}/frames"
    padrao_saida = f"{pasta_frames}/frame_%04d.jpg"

    os.makedirs(pasta_frames, exist_ok=True)

    arquivos_na_pasta = glob.glob(f"{base_dir}/{video_id}.*")
    caminho_video = None
    
    for arquivo in arquivos_na_pasta:
        if not arquivo.endswith(('.mp3', '.srt', '.vtt', '.jpg', '.m4a', '.webp')):
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
        subprocess.run(comando, check=True, stdout=subprocess.DEVNULL)
        print(f"[{video_id}] Frames extraídos com sucesso!")
        
        os.remove(caminho_video)
        print(f"[{video_id}] Vídeo original (.{extensao}) deletado.")
            
    except subprocess.CalledProcessError as e:
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