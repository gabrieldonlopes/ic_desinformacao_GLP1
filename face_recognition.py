import os
import warnings
import logging

# configurando saída dos logs
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")
logging.getLogger('absl').setLevel(logging.ERROR)
logging.getLogger('tensorflow').setLevel(logging.ERROR)

from deepface import DeepFace

def analisar_agrupamento(pasta_frames):
    # Lista arquivos e ordena para garantir a sequência frame_0001, frame_0002...
    arquivos = sorted([f for f in os.listdir(pasta_frames) if f.startswith('frame_') and f.endswith(('.jpg', '.png', '.jpeg'))])
    
    if not arquivos:
        print("Nenhum frame encontrado na pasta.")
        return

    estado_atual = None
    frame_inicial = None
    frame_final = None

    def imprimir_intervalo(inicio, fim, estado):
        print("=====================================")
        print(f"{inicio} -> {fim}")
        if estado['identificada']:
            print("PESSOA: identificada")
            print(f"GÊNERO: {estado['genero']}")
            print(f"IDADE: {estado['idade']}")
        else:
            print("PESSOA: não identificada")
            print("GÊNERO: N/A")
            print("IDADE: N/A")
        print("") # Linha em branco para separar os blocos

    for arquivo in arquivos:
        print(f"Processando: {arquivo}...", end='\r')
        caminho_completo = os.path.join(pasta_frames, arquivo)
        nome_frame = arquivo.split('.')[0]

        # estado padrão
        estado_frame = { 
            'identificada': False,
            'genero': 'N/A',
            'idade': 'N/A'
        }

        try:
            resultados = DeepFace.analyze(
                img_path=caminho_completo,
                actions=['age', 'gender'],
                enforce_detection=True,
                detector_backend='retinaface', # modelo mais avançado para CPU
                silent=True
            )
            
            # pega os dados da pessoa principal no frame
            rosto = resultados[0] 
            idade = rosto['age']
            
            # categorização da idade
            if idade < 18:
                faixa_etaria = "Muito jovem"
            elif 18 <= idade <= 35:
                faixa_etaria = "Jovem"
            elif 36 <= idade <= 59:
                faixa_etaria = "Meia-idade"
            else:
                faixa_etaria = "Velho"

            # Formatação dos dados encontrados
            estado_frame['identificada'] = True
            estado_frame['genero'] = "Homem" if rosto['dominant_gender'] == "Man" else "Mulher"
            estado_frame['idade'] = faixa_etaria

        except ValueError:
            # Cai aqui se o DeepFace não encontrar ninguém no frame
            pass
        except Exception as e:
            print(f"Erro ao ler imagem {arquivo}: {e}")
            continue

        # Lógica para agrupar frames sequenciais iguais
        if estado_atual is None:
            # É o primeiríssimo frame do loop
            estado_atual = estado_frame
            frame_inicial = nome_frame
            frame_final = nome_frame
            
        elif estado_frame == estado_atual:
            frame_final = nome_frame
            
        else: 
            imprimir_intervalo(frame_inicial, frame_final, estado_atual)
            
            # inicia o acompanhamento do novo cenário
            estado_atual = estado_frame
            frame_inicial = nome_frame
            frame_final = nome_frame

    # Imprime o último bloco pendente quando os arquivos acabarem
    if estado_atual is not None:
        imprimir_intervalo(frame_inicial, frame_final, estado_atual)

# Substitua pelo caminho da sua pasta de frames
analisar_agrupamento("./output/emagrecimento,como perder peso,dieta para emagrecer/2-qmpmzLXhE/frames")