import streamlit as st
import pandas as pd
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import io
import urllib.request
import os

# Função para baixar e carregar fontes vetoriais (evita distorção visual)
def carregar_fonte(nome_arquivo, url, tamanho):
    if not os.path.exists(nome_arquivo):
        try:
            urllib.request.urlretrieve(url, nome_arquivo)
        except Exception:
            return ImageFont.load_default()
    return ImageFont.truetype(nome_arquivo, tamanho)

# URLs diretas das fontes Roboto do Google
URL_ROBOTO_REGULAR = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
URL_ROBOTO_BOLD = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"

# Configuração da página
st.set_page_config(page_title="Credenciamento FEIBAM", layout="centered")
st.title("🎟️ Sistema de Credenciamento - FEIBAM")

# 1. Upload do Arquivo CSV
arquivo_csv = st.file_uploader("Faça o upload da lista de participantes (CSV)", type=["csv"])

if arquivo_csv:
    # Lendo o arquivo
    df = pd.read_csv(arquivo_csv, dtype=str)
    
    # Limpar a coluna de Documento para a busca por CPF
    if 'Documento' in df.columns:
        df['CPF_Busca'] = df['Documento'].str.replace(r'\D', '', regex=True)
    else:
        st.error("Erro: A coluna 'Documento' não foi encontrada no ficheiro CSV.")
    
    st.success("Base de dados carregada! Pronto para operar.")
    st.divider()
    
    # 2. Sistema de Busca
    cpf_digitado = st.text_input("Digite o CPF do participante (apenas números):")
    
    if st.button("Gerar Credencial em PDF"):
        cpf_limpo = ''.join(filter(str.isdigit, cpf_digitado))
        
        if cpf_limpo:
            participante = df[df['CPF_Busca'] == cpf_limpo]
            
            if participante.empty:
                st.error("Participante não encontrado. Verifique o CPF.")
            else:
                st.success("Participante encontrado!")
                
                # 3. Extraindo os dados
                dados = participante.iloc[0]
                
                nome_cracha = str(dados.get('Nome Crachá', ''))
                nome_completo = str(dados.get('Nome', 'NOME NÃO ENCONTRADO'))
                if nome_cracha != 'nan' and nome_cracha.strip() != '':
                    nome = nome_cracha.upper()
                else:
                    nome = nome_completo.upper()
                
                empresa = str(dados.get('Nome Fantasia da Empresa', '')).upper()
                funcao = str(dados.get('Seu cargo na empresa:', '')).upper()
                
                # Usando o Número de Inscrição para ambos os códigos (QR e Barras)
                numero_inscricao = str(dados.get('Número de Inscrição', '00000000')) 
                
                categoria = str(dados.get('Categoria', 'VISITANTE')).strip().capitalize()

                # 4. Lógica de Cores
                cores = {
                    "Lojista": "#005bb5",
                    "Distribuidor": "#008a00",
                    "Expositor": "#d11141",
                    "Visitante": "#333333",
                    "Empresarial": "#ff9900"
                }
                cor_tema = cores.get(categoria, "#333333") 

                # 5. Desenhando a Credencial (800x500 pixels)
                img = Image.new('RGB', (800, 500), color='white')
                draw = ImageDraw.Draw(img)
                
                fonte_titulo = carregar_fonte("Roboto-Bold.ttf", URL_ROBOTO_BOLD, 22)
                fonte_padrao = carregar_fonte("Roboto-Regular.ttf", URL_ROBOTO_REGULAR, 16)
                fonte_pequena = carregar_fonte("Roboto-Regular.ttf", URL_ROBOTO_REGULAR, 12)

                # --- BACKGROUND ---
                draw.rectangle([0, 0, 800, 40], fill=cor_tema)
                draw.text((400, 20), f"FEIBAM - {categoria.upper()}", fill="white", font=fonte_titulo, anchor="mm")

                # Linha divisória
                for y in range(50, 480, 15):
                    draw.line([(400, y), (400, y+8)], fill="lightgray", width=2)

                # --- LADO ESQUERDO ---
                draw.text((200, 70), nome, fill="black", font=fonte_titulo, anchor="mm")
                
                if empresa != 'NAN' and empresa != '':
                    draw.text((200, 100), f"{empresa}", fill=cor_tema, font=fonte_titulo, anchor="mm")
                if funcao != 'NAN' and funcao != '':
                    draw.text((200, 125), f"{funcao}", fill="black", font=fonte_padrao, anchor="mm")

                # QR Code
                qr = qrcode.make(numero_inscricao)
                qr = qr.resize((150, 150))
                img.paste(qr, (125, 140)) 
                
                draw.text((200, 305), numero_inscricao, fill="black", font=fonte_padrao, anchor="mm")

                # Código de Barras
                try:
                    # Voltamos a usar o numero_inscricao aqui
                    codigo_barras = Code128(numero_inscricao, writer=ImageWriter())
                    arquivo_temp = io.BytesIO()
                    opcoes_barras = {"module_height": 8.0, "font_size": 0, "text_distance": 0, "quiet_zone": 1.0}
                    codigo_barras.write(arquivo_temp, options=opcoes_barras)
                    
                    img_barras = Image.open(arquivo_temp).resize((240, 50))
                    img.paste(img_barras, (80, 340))
                    # Texto opcional abaixo do código de barras
                    # draw.text((200, 395), f"{numero_inscricao}", fill="gray", font=fonte_pequena, anchor="mm")
                except Exception:
                    draw.text((200, 380), "[Erro ao gerar Cód. Barras]", fill="red", font=fonte_pequena, anchor="mm")

                # --- LADO DIREITO (Idêntico ao PDF do Even3) ---
                x_dir = 430
                
                draw.text((x_dir, 70), "Evento", fill="black", font=fonte_titulo)
                draw.text((x_dir, 100), "FEIBAM | Feira de Equipamentos e\nInovações Multimarcas na Bahia - 2026", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 160), "Local", fill="black", font=fonte_titulo)
                draw.text((x_dir, 190), "Ville Conventions", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 240), "Data inicial", fill="black", font=fonte_titulo)
                draw.text((x_dir, 270), "01/05/2026 00:00:00 08:00", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 320), "Data final", fill="black", font=fonte_titulo)
                draw.text((x_dir, 350), "02/05/2026 00:00:00 21:00", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 400), "Inscrição", fill="black", font=fonte_titulo)
                draw.text((x_dir, 430), categoria, fill=cor_tema, font=fonte_padrao)

                # 6. Salvar em PDF e disponibilizar para Download
                st.image(img, caption=f"Visualização: Credencial de {nome}", use_column_width=True)
                
                buf = io.BytesIO()
                # Exportando direto para PDF com ótima qualidade
                img.save(buf, format="PDF", resolution=100.0)
                byte_pdf = buf.getvalue()
                
                st.download_button(
                    label="📄 Fazer Download da Credencial em PDF",
                    data=byte_pdf,
                    file_name=f"credencial_{cpf_limpo}.pdf",
                    mime="application/pdf"
                )
