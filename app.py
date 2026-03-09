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
                
                numero_inscricao = str(dados.get('Número de Inscrição', '00000000')) 
                
                categoria = str(dados.get('Categoria', 'VISITANTE')).strip().capitalize()

                # 4. Lógica de Cores (Ainda usaremos na empresa e no nome da inscrição para dar destaque)
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
                
                fonte_titulo = carregar_fonte("Roboto-Bold.ttf", URL_ROBOTO_BOLD, 22)
                fonte_padrao = carregar_fonte("Roboto-Regular.ttf", URL_ROBOTO_REGULAR, 16)
                fonte_pequena = carregar_fonte("Roboto-Regular.ttf", URL_ROBOTO_REGULAR, 12)

                # --- LINHAS DE DOBRA E CORTE ---
                # Linha Vertical (meio da folha)
                for y in range(0, 1131, 15):
                    draw.line([(400, y), (400, y+8)], fill="lightgray", width=1)
                
                # Linha Horizontal (meio da folha - onde divide a frente do verso inferior)
                for x in range(0, 800, 15):
                    draw.line([(x, 565), (x+8, 565)], fill="lightgray", width=1)


                # --- LADO ESQUERDO SUPERIOR (Frente do Crachá) ---
                draw.text((200, 60), nome, fill="black", font=fonte_titulo, anchor="mm")
                
                if empresa != 'NAN' and empresa != '':
                    draw.text((200, 95), f"{empresa}", fill=cor_tema, font=fonte_titulo, anchor="mm")
                if funcao != 'NAN' and funcao != '':
                    draw.text((200, 120), f"{funcao}", fill="black", font=fonte_padrao, anchor="mm")

                # QR Code
                qr = qrcode.make(numero_inscricao)
                qr = qr.resize((170, 170))
                img.paste(qr, (115, 140)) 
                
                draw.text((200, 320), numero_inscricao, fill="black", font=fonte_padrao, anchor="mm")

                # Código de Barras
                try:
                    codigo_barras = Code128(numero_inscricao, writer=ImageWriter())
                    arquivo_temp = io.BytesIO()
                    opcoes_barras = {"module_height": 8.0, "font_size": 0, "text_distance": 0, "quiet_zone": 1.0}
                    codigo_barras.write(arquivo_temp, options=opcoes_barras)
                    
                    img_barras = Image.open(arquivo_temp).resize((250, 60))
                    img.paste(img_barras, (75, 360))
                except Exception:
                    draw.text((200, 390), "[Erro ao gerar Cód. Barras]", fill="red", font=fonte_pequena, anchor="mm")


                # --- LADO DIREITO SUPERIOR (Verso do Crachá) ---
                x_dir = 450 # Margem direita a partir da linha central
                
                draw.text((x_dir, 60), "Evento", fill="black", font=fonte_titulo)
                draw.text((x_dir, 90), "FEIBAM | Feira de Equipamentos e\nInovações Multimarcas na Bahia - 2026", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 160), "Local", fill="black", font=fonte_titulo)
                draw.text((x_dir, 190), "Ville Conventions", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 250), "Data inicial", fill="black", font=fonte_titulo)
                draw.text((x_dir, 280), "01/05/2026 00:00:00 08:00", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 340), "Data final", fill="black", font=fonte_titulo)
                draw.text((x_dir, 370), "02/05/2026 00:00:00 21:00", fill="black", font=fonte_padrao)
                
                draw.text((x_dir, 430), "Inscrição", fill="black", font=fonte_titulo)
                draw.text((x_dir, 460), categoria, fill=cor_tema, font=fonte_padrao)


                # --- PARTE INFERIOR DA FOLHA A4 (Para ser dobrada para dentro) ---
                texto_comprovante = "Esse documento comprova que sua inscrição\nno evento foi realizada."
                draw.text((400, 750), texto_comprovante, fill="black", font=fonte_padrao, anchor="mm", align="center")
                
                texto_rodape = "Even3\nOrganize eventos com a Even3\nwww.even3.com.br"
                draw.text((400, 950), texto_rodape, fill="gray", font=fonte_padrao, anchor="mm", align="center")

                # 6. Salvar em PDF e disponibilizar para Download
                st.image(img, caption=f"Visualização: Credencial de {nome}", use_column_width=True)
                
                buf = io.BytesIO()
                # Salva no formato PDF mantendo as proporções da folha A4
                img.save(buf, format="PDF", resolution=100.0)
                byte_pdf = buf.getvalue()
                
                st.download_button(
                    label="📄 Fazer Download da Credencial em PDF",
                    data=byte_pdf,
                    file_name=f"credencial_{cpf_limpo}.pdf",
                    mime="application/pdf"
                )
