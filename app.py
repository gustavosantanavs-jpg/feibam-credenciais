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

# URL direta do logotipo da FEIBAM (usando um link encontrado na busca)
URL_LOGO_FEIBAM = "https://images.sympla.com.br/6997a1332a73b-lg.png"

# Função para baixar e carregar arquivos (fontes ou imagens)
def baixar_arquivo(nome_arquivo, url):
    if not os.path.exists(nome_arquivo):
        try:
            urllib.request.urlretrieve(url, nome_arquivo)
        except Exception as e:
            st.error(f"Erro ao baixar o arquivo {nome_arquivo}: {e}")
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
                
                # Baixando e Carregando Recursos
                baixar_arquivo("Roboto-Regular.ttf", URL_ROBOTO_REGULAR)
                baixar_arquivo("Roboto-Bold.ttf", URL_ROBOTO_BOLD)
                caminho_logo = baixar_arquivo("logo_feibam.png", URL_LOGO_FEIBAM)

                # Carregando as fontes
                fonte_titulo = carregar_fonte("Roboto-Bold.ttf", 22)
                fonte_padrao = carregar_fonte("Roboto-Regular.ttf", 16)
                fonte_pequena = carregar_fonte("Roboto-Regular.ttf", 12)

                # Carregando e Redimensionando o Logo
                logo_orig = None
                if caminho_logo:
                    try:
                        logo_orig = Image.open(caminho_logo)
                        if logo_orig.mode != 'RGBA':
                            logo_orig = logo_orig.convert('RGBA')
                        # Redimensionar para ficar proporcional na header
                        logo_redim = logo_orig.resize((200, 80), Image.Resampling.LANCZOS)
                        width_logo, height_logo = logo_redim.size
                    except Exception:
                        logo_orig = None

                # --- LINHAS DE DOBRA E CORTE ---
                # Linha Vertical
                for y in range(0, 1131, 15):
                    draw.line([(400, y), (400, y+8)], fill="lightgray", width=1)
                
                # Linha Horizontal
                for x in range(0, 800, 15):
                    draw.line([(x, 565), (x+8, 565)], fill="lightgray", width=1)


                # --- LADO ESQUERDO SUPERIOR (Frente do Crachá) ---
                y_frente = 30
                # Colocar o Logo Centrado
                if logo_orig:
                    img.paste(logo_redim, (200 - (width_logo // 2), y_frente), logo_redim)
                    y_frente += height_logo + 20 # Espaço após o logo
                else:
                    y_frente += 10 # Pequeno espaço se não tiver logo

                draw.text((200, y_frente), nome, fill="black", font=fonte_titulo, anchor="mm")
                
                if empresa != 'NAN' and empresa != '':
                    draw.text((200, y_frente + 35), f"{empresa}", fill=cor_tema, font=fonte_titulo, anchor="mm")
                if funcao != 'NAN' and funcao != '':
                    draw.text((200, y_frente + 60), f"{funcao}", fill="black", font=fonte_padrao, anchor="mm")

                # QR Code
                qr = qrcode.make(numero_inscricao)
                qr = qr.resize((160, 160))
                # Ajustar a posição do QR para não sobrepor o texto que subiu
                img.paste(qr, (120, y_frente + 90)) 
                
                draw.text((200, y_frente + 265), numero_inscricao, fill="black", font=fonte_padrao, anchor="mm")

                # Código de Barras
                try:
                    codigo_barras = Code128(numero_inscricao, writer=ImageWriter())
                    arquivo_temp = io.BytesIO()
                    opcoes_barras = {"module_height": 8.0, "font_size": 0, "text_distance": 0, "quiet_zone": 1.0}
                    codigo_barras.write(arquivo_temp, options=opcoes_barras)
                    
                    img_barras = Image.open(arquivo_temp).resize((240, 60))
                    # Ajustar posição do Cód. Barras
                    img.paste(img_barras, (80, y_frente + 300))
                except Exception:
                    draw.text((200, y_frente + 340), "[Erro ao gerar Cód. Barras]", fill="red", font=fonte_pequena, anchor="mm")


                # --- LADO DIREITO SUPERIOR (Verso do Crachá) ---
                x_dir = 450
                y_verso = 30

                # Colocar o Logo Centrado no verso também
                if logo_orig:
                    img.paste(logo_redim, (600 - (width_logo // 2), y_verso), logo_redim)
                    y_verso += height_logo + 20 
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

                # 6. Salvar em PDF e disponibilizar para Download
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
