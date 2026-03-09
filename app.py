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
    # Lendo o arquivo em formato string para manter zeros à esquerda
    df = pd.read_csv(arquivo_csv, dtype=str)
    
    # Limpar a coluna de Documento (onde estão os CPFs) para deixar só números
    if 'Documento' in df.columns:
        df['CPF_Busca'] = df['Documento'].str.replace(r'\D', '', regex=True)
    else:
        st.error("Erro: A coluna 'Documento' não foi encontrada no ficheiro CSV.")
    
    st.success("Base de dados carregada! Pronto para operar.")
    st.divider()
    
    # 2. Sistema de Busca
    cpf_digitado = st.text_input("Digite o CPF do participante (apenas números):")
    
    if st.button("Gerar Credencial"):
        cpf_limpo = ''.join(filter(str.isdigit, cpf_digitado))
        
        if cpf_limpo:
            participante = df[df['CPF_Busca'] == cpf_limpo]
            
            if participante.empty:
                st.error("Participante não encontrado. Verifique o CPF.")
            else:
                st.success("Participante encontrado!")
                
                # 3. Extraindo os dados do CSV
                dados = participante.iloc[0]
                
                nome_cracha = str(dados.get('Nome Crachá', ''))
                nome_completo = str(dados.get('Nome', 'NOME NÃO ENCONTRADO'))
                if nome_cracha != 'nan' and nome_cracha.strip() != '':
                    nome = nome_cracha.upper()
                else:
                    nome = nome_completo.upper()
                
                empresa = str(dados.get('Nome Fantasia da Empresa', '')).upper()
                funcao = str(dados.get('Seu cargo na empresa:', '')).upper()
                
                # Buscando o ID exato do banco de dados do Even3 para os códigos
                id_even3 = str(dados.get('ID', '00000000')) 
                
                categoria = str(dados.get('Categoria', 'VISITANTE')).strip().upper()

                # 4. Lógica de Cores por Categoria
                cores = {
                    "LOJISTA": "#005bb5",      # Azul
                    "DISTRIBUIDOR": "#008a00", # Verde
                    "EXPOSITOR": "#d11141",    # Vermelho
                    "VISITANTE": "#333333",    # Cinza Escuro
                    "EMPRESARIAL": "#ff9900"   # Laranja
                }
                cor_tema = cores.get(categoria, "#333333") 

                # 5. Desenhando a Credencial (800x500 pixels)
                img = Image.new('RGB', (800, 500), color='white')
                draw = ImageDraw.Draw(img)
                
                # Carregando as fontes com qualidade (sem distorção)
                fonte_titulo = carregar_fonte("Roboto-Bold.ttf", URL_ROBOTO_BOLD, 26)
                fonte_padrao = carregar_fonte("Roboto-Regular.ttf", URL_ROBOTO_REGULAR, 18)
                fonte_pequena = carregar_fonte("Roboto-Regular.ttf", URL_ROBOTO_REGULAR, 14)

                # Tarja superior
                draw.rectangle([0, 0, 800, 50], fill=cor_tema)
                draw.text((400, 25), f"FEIBAM - {categoria}", fill="white", font=fonte_titulo, anchor="mm")

                # Linha divisória central
                for y in range(60, 480, 15):
                    draw.line([(400, y), (400, y+8)], fill="lightgray", width=2)

                # --- LADO ESQUERDO (Identificação e Códigos) ---
                draw.text((200, 90), nome, fill="black", font=fonte_titulo, anchor="mm")
                
                if empresa != 'NAN' and empresa != '':
                    draw.text((200, 125), f"Empresa: {empresa}", fill=cor_tema, font=fonte_padrao, anchor="mm")
                if funcao != 'NAN' and funcao != '':
                    draw.text((200, 150), f"Cargo: {funcao}", fill="black", font=fonte_padrao, anchor="mm")

                # QR Code gerado a partir do ID do banco de dados
                qr = qrcode.make(id_even3)
                qr = qr.resize((160, 160))
                img.paste(qr, (120, 180)) 
                
                draw.text((200, 355), id_even3, fill="black", font=fonte_padrao, anchor="mm")

                # Código de Barras gerado a partir do ID do banco de dados
                try:
                    codigo_barras = Code128(id_even3, writer=ImageWriter())
                    arquivo_temp = io.BytesIO()
                    # Opções para deixar o código de barras com uma resolução melhor
                    opcoes_barras = {"module_height": 10.0, "font_size": 0, "text_distance": 0, "quiet_zone": 1.0}
                    codigo_barras.write(arquivo_temp, options=opcoes_barras)
                    
                    img_barras = Image.open(arquivo_temp).resize((260, 60))
                    img.paste(img_barras, (70, 380))
                except Exception as e:
                    draw.text((200, 400), "[Erro ao gerar Cód. Barras]", fill="red", font=fonte_pequena, anchor="mm")

                # --- LADO DIREITO (Informações Fixas do Evento) ---
                x_dir = 430
                
                draw.text((x_dir, 100), "Evento", fill="black", font=fonte_titulo)
                draw.text((x_dir, 130), "FEIBAM", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 190), "Local", fill="black", font=fonte_titulo)
                draw.text((x_dir, 220), "Cruz das Almas - BA", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 280), "Acesso", fill="black", font=fonte_titulo)
                draw.text((x_dir, 310), "Livre para área de exposição", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 370), "Inscrição", fill="black", font=fonte_titulo)
                draw.text((x_dir, 400), categoria, fill=cor_tema, font=fonte_padrao)

                # 6. Exibir e Baixar
                st.image(img, caption=f"Credencial gerada para {nome}", use_column_width=True)
                
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.download_button(
                    label="⬇️ Fazer Download da Credencial",
                    data=byte_im,
                    file_name=f"credencial_{cpf_limpo}.png",
                    mime="image/png"
                )
