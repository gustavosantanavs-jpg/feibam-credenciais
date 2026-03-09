import streamlit as st
import pandas as pd
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import io
import urllib.request
import os

# URLs diretas das fontes Roboto do Google
URL_ROBOTO_REGULAR = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
URL_ROBOTO_BOLD = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"

# Função para baixar e carregar arquivos (fontes)
def baixar_arquivo(nome_arquivo, url):
    if not os.path.exists(nome_arquivo):
        try:
            urllib.request.urlretrieve(url, nome_arquivo)
        except Exception as e:
            st.error(f"Erro ao transferir o ficheiro {nome_arquivo}: {e}")
            return None
    return nome_arquivo

# Função para carregar uma fonte vetorial
def carregar_fonte(nome_arquivo, tamanho):
    try:
        return ImageFont.truetype(nome_arquivo, tamanho)
    except Exception:
        return ImageFont.load_default()

# Configuração da página
st.set_page_config(page_title="Credenciamento FEIBAM", layout="centered")
st.title("🎟️ Sistema de Credenciamento - FEIBAM")

# 1. Upload do Ficheiro CSV
arquivo_csv = st.file_uploader("Faça o upload da lista de participantes (CSV)", type=["csv"])

if arquivo_csv:
    # Lendo o ficheiro
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

                # 5. Desenhando a Credencial (Proporção Folha A4: 800x1131 pixels)
                img = Image.new('RGB', (800, 1131), color='white')
                draw = ImageDraw.Draw(img)
                
                # Descarregando e Carregando as fontes
                baixar_arquivo("Roboto-Regular.ttf", URL_ROBOTO_REGULAR)
                baixar_arquivo("Roboto-Bold.ttf", URL_ROBOTO_BOLD)

                fonte_titulo = carregar_fonte("Roboto-Bold.ttf", 22)
                fonte_padrao = carregar_fonte("Roboto-Regular.ttf", 16)
                fonte_pequena = carregar_fonte("Roboto-Regular.ttf", 12)

                # Carregando e Redimensionando o Logótipo Local
                logo_redim = None
                caminho_logo_local = "logo_feibam.png" # NOME DO SEU FICHEIRO PNG
                
                if os.path.exists(caminho_logo_local):
                    try:
                        logo_orig = Image.open(caminho_logo_local)
                        if logo_orig.mode != 'RGBA':
                            logo_orig = logo_orig.convert('RGBA')
                        
                        # --- FIX QUALIDADE: Redimensionamento Amigável ---
                        # Definimos uma LARGURA MÁXIMA para garantir a nitidez (ex: 300px)
                        LARGURA_MAX_LOGO = 300
                        
                        if logo_orig.width > LARGURA_MAX_LOGO:
                            # Redimensiona mantendo a proporção exata
                            logo_redim = logo_orig.resize(
                                (LARGURA_MAX_LOGO, int((LARGURA_MAX_LOGO / logo_orig.width) * logo_orig.height)),
                                Image.Resampling.LANCZOS # Melhor qualidade
                            )
                        else:
                            # Se for pequena, mantém a original para não pixelizar
                            logo_redim = logo_orig 
                            
                        width_logo, height_logo = logo_redim.size
                    except Exception as e:
                        st.warning(f"Não foi possível carregar o logótipo. Erro: {e}")
                        logo_redim = None

                # --- LINHAS DE DOBRA E CORTE ---
                # Linha Vertical
                for y in range(0, 1131, 15):
                    draw.line([(400, y), (400, y+8)], fill="lightgray", width=1)
                
                # Linha Horizontal
                for x in range(0, 800, 15):
                    draw.line([(x, 565), (x+8, 565)], fill="lightgray", width=1)


                # --- LADO ESQUERDO SUPERIOR (Frente do Crachá) ---
                y_frente = 30
                # --- FIX CENTRALIZAÇÃO: Colocar o Logótipo Centrado em 200 ---
                if logo_redim:
                    img.paste(logo_redim, (200 - (width_logo // 2), y_frente), logo_redim)
                    y_frente += height_logo + 25 # Espaço após o logótipo
                else:
                    y_frente += 10 # Pequeno espaço se não tiver logótipo

                # --- FIX CENTRALIZAÇÃO: Usar anchor="mm" e x=200 para tudo ---
                draw.text((200, y_frente), nome, fill="black", font=fonte_titulo, anchor="mm")
                
                if empresa != 'NAN' and empresa != '':
                    draw.text((200, y_frente + 40), f"{empresa}", fill=cor_tema, font=fonte_titulo, anchor="mm")
                if funcao != 'NAN' and funcao != '':
                    draw.text((200, y_frente + 65), f"{funcao}", fill="black", font=fonte_padrao, anchor="mm")

                # QR Code
                qr = qrcode.make(numero_inscricao)
                qr = qr.resize((160, 160))
                # Centralizando o QR Code (x=200 - metade da largura)
                img.paste(qr, (120, y_frente + 100)) 
                
                draw.text((200, y_frente + 275), numero_inscricao, fill="black", font=fonte_padrao, anchor="mm")

                # Código de Barras
                try:
                    codigo_barras = Code128(numero_inscricao, writer=ImageWriter())
                    arquivo_temp = io.BytesIO()
                    # Resolução melhorada para impressão
                    opcoes_barras = {"module_height": 8.0, "font_size": 0, "text_distance": 0, "quiet_zone": 1.0}
                    codigo_barras.write(arquivo_temp, options=opcoes_barras)
                    
                    img_barras = Image.open(arquivo_temp).resize((240, 60))
                    # Centralizando o Código de Barras (x=200 - metade da largura)
                    img.paste(img_barras, (80, y_frente + 320))
                except Exception:
                    draw.text((200, y_frente + 360), "[Erro ao gerar Cód. Barras]", fill="red", font=fonte_pequena, anchor="mm")


                # --- LADO DIREITO SUPERIOR (Verso do Crachá) ---
                x_dir = 450
                y_verso = 30

                # Colocar o Logótipo Centrado no verso também (centro da coluna é 600)
                if logo_redim:
                    img.paste(logo_redim, (600 - (width_logo // 2), y_verso), logo_redim)
                    y_verso += height_logo + 25 
                else:
                    y_verso += 10

                draw.text((x_dir, y_verso), "Evento", fill="black", font=fonte_titulo)
                draw.text((x_dir, y_verso + 30), "FEIBAM | Feira de Equipamentos e\nInovações Multimarcas na Bahia - 2026", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, y_verso + 90), "Local", fill="black", font=fonte_titulo)
                draw.text((x_dir, y_verso + 120), "Ville Conventions", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, y_verso + 170), "Data inicial", fill="black", font=fonte_titulo)
                draw.text((x_dir, y_verso + 200), "01/05/2026 00:00:00 08:00", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, y_verso + 250), "Data final", fill="black", font=fonte_titulo)
                draw.text((x_dir, y_verso + 280), "02/05/2026 00:00:00 21:00", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, y_verso + 330), "Inscrição", fill="black", font=fonte_titulo)
                draw.text((x_dir, y_verso + 360), categoria, fill=cor_tema, font=fonte_padrao)


                # --- PARTE INFERIOR DA FOLHA A4 ---
                texto_comprovante = "Esse documento comprova que sua inscrição\nno evento foi realizada."
                draw.text((400, 750), texto_comprovante, fill="black", font=fonte_padrao, anchor="mm", align="center")
                
                texto_rodape = "Even3\nOrganize eventos com a Even3\nwww.even3.com.br"
                draw.text((400, 950), texto_rodape, fill="gray", font=fonte_padrao, anchor="mm", align="center")

                # 6. Guardar em PDF e disponibilizar para Download
                st.image(img, caption=f"Visualização: Credencial de {nome}", use_column_width=True)
                
                buf = io.BytesIO()
                img.save(buf, format="PDF", resolution=100.0)
                byte_pdf = buf.getvalue()
                
                st.download_button(
                    label="📄 Fazer Download da Credencial em PDF",
                    data=byte_pdf,
                    file_name=f"credencial_{cpf_limpo}.pdf",
                    mime="application/pdf"
                )
