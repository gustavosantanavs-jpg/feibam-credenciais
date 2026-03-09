import streamlit as st
import pandas as pd
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import io


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
                
                # 3. Extraindo os dados usando os cabeçalhos exatos da sua planilha
                dados = participante.iloc[0]
                
                # Puxa o Nome Crachá. Se estiver vazio, puxa o Nome completo
                nome_cracha = str(dados.get('Nome Crachá', ''))
                nome_completo = str(dados.get('Nome', 'NOME NÃO ENCONTRADO'))
                if nome_cracha != 'nan' and nome_cracha.strip() != '':
                    nome = nome_cracha.upper()
                else:
                    nome = nome_completo.upper()
                
                empresa = str(dados.get('Nome Fantasia da Empresa', '')).upper()
                funcao = str(dados.get('Seu cargo na empresa:', '')).upper()
                
                codigo_even3 = str(dados.get('Número de Inscrição', '00000000')) 
                categoria = str(dados.get('Categoria', 'VISITANTE')).strip().upper()


                # 4. Lógica de Cores por Categoria
                cores = {
                    "LOJISTA": "#005bb5",      # Azul
                    "DISTRIBUIDOR": "#008a00", # Verde
                    "EXPOSITOR": "#d11141",    # Vermelho
                    "VISITANTE": "#333333",    # Cinza Escuro
                    "EMPRESARIAL": "#ff9900"   # Laranja (encontrado na sua lista)
                }
                cor_tema = cores.get(categoria, "#333333") 


                # 5. Desenhando a Credencial (800x500 pixels)
                img = Image.new('RGB', (800, 500), color='white')
                draw = ImageDraw.Draw(img)
                
                try:
                    fonte_titulo = ImageFont.truetype("arialbd.ttf", 26)
                    fonte_padrao = ImageFont.truetype("arial.ttf", 18)
                    fonte_pequena = ImageFont.truetype("arial.ttf", 14)
                except:
                    fonte_titulo = ImageFont.load_default()
                    fonte_padrao = ImageFont.load_default()
                    fonte_pequena = ImageFont.load_default()


                # Tarja superior
                draw.rectangle([0, 0, 800, 50], fill=cor_tema)
                draw.text((400, 25), f"FEIBAM - {categoria}", fill="white", font=fonte_titulo, anchor="mm")


                # Linha divisória central
                for y in range(60, 480, 15):
                    draw.line([(400, y), (400, y+8)], fill="lightgray", width=2)


                # Lado Esquerdo (Identificação e Códigos)
                draw.text((200, 90), nome, fill="black", font=fonte_titulo, anchor="mm")
                
                if empresa != 'NAN' and empresa != '':
                    draw.text((200, 125), f"Empresa: {empresa}", fill=cor_tema, font=fonte_padrao, anchor="mm")
                if funcao != 'NAN' and funcao != '':
                    draw.text((200, 150), f"Cargo: {funcao}", fill="black", font=fonte_padrao, anchor="mm")


                # QR Code
                qr = qrcode.make(codigo_even3)
                qr = qr.resize((160, 160))
                img.paste(qr, (120, 180)) 
                
                draw.text((200, 355), codigo_even3, fill="black", font=fonte_padrao, anchor="mm")


                # Código de Barras
                try:
                    codigo_barras = Code128(codigo_even3, writer=ImageWriter())
                    arquivo_temp = io.BytesIO()
                    codigo_barras.write(arquivo_temp)
                    img_barras = Image.open(arquivo_temp).resize((260, 70))
                    img.paste(img_barras, (70, 380))
                except:
                    draw.text((200, 400), "[Erro ao gerar Cód. Barras]", fill="red", font=fonte_pequena, anchor="mm")


                # Lado Direito (Informações Fixas do Evento)
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