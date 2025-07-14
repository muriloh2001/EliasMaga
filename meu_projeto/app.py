from flask import Flask, request, render_template
import pandas as pd
import os
from flask import redirect, url_for, flash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from flask import send_file
from flask import jsonify
from fpdf import FPDF
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

df_global = None
MAPEAMENTO_CSV = 'mapeamento_cores.csv'

MAPEAMENTO_AUTOMATICO = {
    'azul': 'Azul',
    'marinho': 'Marinho',
    'verde': 'Verde',
    'militar': 'Verde',
    'preto': 'Preto',
    'branco': 'Branco',
    'vermelho': 'Vermelho',
    'rosa': 'Rosa',
    'cinza': 'Cinza',
    'amarelo': 'Amarelo',
    'bege': 'Bege',
    'laranja': 'Laranja',
    'roxo': 'Roxo',
    'bordô': 'Vermelho',
    'marrom': 'Marrom'
}

def carregar_mapeamento_csv():
    if os.path.exists(MAPEAMENTO_CSV):
        return pd.read_csv(MAPEAMENTO_CSV).set_index('cor_1')['cor_pai'].to_dict()
    return {}

def salvar_mapeamento_csv(dicionario):
    df = pd.DataFrame(list(dicionario.items()), columns=['cor_1', 'cor_pai'])
    df.to_csv(MAPEAMENTO_CSV, index=False)

mapeamento_cores = carregar_mapeamento_csv()

def classificar_cor_pai(cor):
    if pd.isna(cor):
        return 'Desconhecido'

    cor_lower = cor.lower().strip()

    for key in mapeamento_cores:
        if key.lower().strip() == cor_lower:
            return mapeamento_cores[key]

    for palavra, cor_pai in MAPEAMENTO_AUTOMATICO.items():
        if palavra in cor_lower:
            return cor_pai

    return 'Outras'

def calcular_sobras_por_loja(df_global, codigo_loja_int, filtro_sub_grupo='', filtro_secao='', filtro_produto=''):
    df_filtrado = df_global.copy()

    if filtro_sub_grupo:
        df_filtrado = df_filtrado[df_filtrado['nome_sub_grupo'] == filtro_sub_grupo]
    if filtro_secao:
        df_filtrado = df_filtrado[df_filtrado['nome_secao'] == filtro_secao]
    if filtro_produto:
        df_filtrado = df_filtrado[df_filtrado['nome_produto'] == filtro_produto]

    df_loja = df_filtrado[df_filtrado['codigo_loja'] == codigo_loja_int].copy()  # <-- copy aqui
    df_loja['cor_pai'] = df_loja['cor_1'].apply(classificar_cor_pai).str.strip().str.upper()

    agrupado_loja = df_loja.groupby(['cor_pai', 'tamanho'], observed=False)['Estoque'].sum().reset_index()

    # Padronizar tamanho
    agrupado_loja['tamanho'] = agrupado_loja['tamanho'].str.strip().str.upper()

    cores_tamanhos_por_cor = df_filtrado.groupby('cor_pai', observed=False)['tamanho'].unique().to_dict()

    combinacoes = [(cor, tam) for cor, tamanhos in cores_tamanhos_por_cor.items() for tam in tamanhos]

    df_completo = pd.DataFrame(combinacoes, columns=['cor_pai', 'tamanho'])
    df_completo['tamanho'] = df_completo['tamanho'].str.strip().str.upper()
    df_completo['cor_pai'] = df_completo['cor_pai'].str.strip().str.upper()

    df_completo = df_completo.merge(agrupado_loja, on=['cor_pai', 'tamanho'], how='left')
    df_completo['Estoque'] = df_completo['Estoque'].fillna(0).astype(int)

    sobras = df_completo[df_completo['Estoque'] > 1].to_dict(orient='records')
    return sobras

def gerar_pdf_sobras(sobras):
    # Criar um buffer em memória
    buffer = BytesIO()

    # Criar o objeto PDF
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)

    # Título
    c.drawString(200, 750, "Relatório de Sobras")

    # Sobras
    c.drawString(30, 730, "Sobras (mais de 1 peça):")
    y_position = 710
    for sobra in sobras:
        cor_pai = sobra['cor_pai']
        tamanho = sobra['tamanho']
        estoque = sobra['Estoque']

        # Adiciona as sobras no PDF
        c.drawString(30, y_position, f"Cor: {cor_pai}, Tamanho: {tamanho}, Estoque: {estoque}")
        y_position -= 20

    # Finalizar e gerar o PDF
    c.showPage()
    c.save()

    buffer.seek(0)  # Voltar para o início do buffer

    return buffer

def gerar_faltas(df_filtrado, codigo_loja_int):
    print("🔍 Início da função gerar_faltas")

    # Padroniza
    df_filtrado['cor_pai'] = df_filtrado['cor_1'].apply(classificar_cor_pai).str.strip().str.upper()
    df_filtrado['tamanho'] = df_filtrado['tamanho'].astype(str).str.strip().str.upper()

    print("✅ Primeiras linhas de df_filtrado:")
    print(df_filtrado[['codigo_loja', 'cor_pai', 'tamanho', 'Estoque']].head())

    # Filtra apenas a loja desejada
    df_loja = df_filtrado[df_filtrado['codigo_loja'] == codigo_loja_int].copy()
    print(f"🛒 Estoque da loja {codigo_loja_int}:")
    print(df_loja[['cor_pai', 'tamanho', 'Estoque']].head())

    # Agrupa estoque da loja
    agrupado_loja = df_loja.groupby(['cor_pai', 'tamanho'], observed=False)['Estoque'].sum().reset_index()
    print("📦 Estoque agrupado da loja:")
    print(agrupado_loja)

    # Gera combinações com base no universo filtrado
    cores_tamanhos_por_cor = df_filtrado.groupby('cor_pai')['tamanho'].unique().to_dict()
    combinacoes = [(cor, tam) for cor, tamanhos in cores_tamanhos_por_cor.items() for tam in tamanhos]

    print("🧩 Combinações possíveis baseadas na grade geral:")
    print(combinacoes[:10])  # mostra só as primeiras 10

    df_completo = pd.DataFrame(combinacoes, columns=['cor_pai', 'tamanho'])
    df_completo['tamanho'] = df_completo['tamanho'].str.strip().str.upper()
    df_completo['cor_pai'] = df_completo['cor_pai'].str.strip().str.upper()
    agrupado_loja['tamanho'] = agrupado_loja['tamanho'].str.strip().str.upper()
    agrupado_loja['cor_pai'] = agrupado_loja['cor_pai'].str.strip().str.upper()

    df_completo = df_completo.merge(agrupado_loja, on=['cor_pai', 'tamanho'], how='left')

    print("🔄 Resultado após merge com agrupado_loja:")
    print(df_completo.head(10))

    df_completo['Estoque'] = df_completo['Estoque'].fillna(0).astype(int)

    # Filtros finais
    faltas = df_completo[df_completo['Estoque'] == 0].sort_values(by=['cor_pai', 'tamanho'])

    print("🚨 Faltas identificadas:")
    print(faltas)

    return faltas.to_dict(orient='records')


def gerar_pdf_faltas(faltas):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Relatório de Faltas", ln=True, align="C")
    pdf.ln(10)

    for falta in faltas:
        linha = f"Cor: {falta['cor_pai']}, Tamanho: {falta['tamanho']}"
        pdf.cell(200, 10, txt=linha, ln=True)

    # Gera o conteúdo do PDF como string Latin1
    pdf_bytes = pdf.output(dest='S').encode('latin1')

    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer

# =================== Configurações de Leitura ===================
COLUNAS_RELEVANTES = [
    'codigo_produto', 'nome_produto', 'codigo_loja', 'fornecedor',
    'nome_grupo', 'nome_sub_grupo', 'nome_departamento', 'nome_secao',
    'cor_1', 'cor_2', 'cor_3', 'tamanho', 'Estoque', 'Venda', 'Total', '%Total'
]

TIPOS_COLUNAS = {
    'codigo_produto': 'str',
    'nome_produto': 'category',
    'codigo_loja': 'int32',
    'fornecedor': 'category',
    'nome_grupo': 'category',
    'nome_sub_grupo': 'category',
    'nome_departamento': 'category',
    'nome_secao': 'category',
    'cor_1': 'category',
    'cor_2': 'category',
    'cor_3': 'category',
    'tamanho': 'category',
    'Estoque': 'int16',
    'Venda': 'float32',
    'Total': 'float32',
    '%Total': 'float32'
}

@app.route('/', methods=['GET', 'POST'])
def index():
    global df_global

    if request.method == 'POST' and 'file' in request.files:
        arquivo = request.files['file']
        if arquivo:
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], arquivo.filename)
            arquivo.save(caminho)

            if arquivo.filename.endswith('.csv'):
                df_global = pd.read_csv(
                    caminho,
                    usecols=COLUNAS_RELEVANTES,
                    dtype=TIPOS_COLUNAS
                )
            elif arquivo.filename.endswith(('.xls', '.xlsx')):
                df_global = pd.read_excel(
                    caminho,
                    usecols=COLUNAS_RELEVANTES,
                    dtype=TIPOS_COLUNAS
                )
            else:
                flash("Formato de arquivo não suportado!", "error")
                return redirect(url_for('index'))

            df_global['cor_pai'] = df_global['cor_1'].apply(classificar_cor_pai)
            flash("Arquivo carregado com sucesso! Você pode ir para a página de análise.", "success")
            return redirect(url_for('analise'))

    return render_template('index.html')

@app.route('/classificar_cores', methods=['GET'])
def classificar_cores():
    global df_global

    if df_global is None or 'cor_1' not in df_global.columns:
        return "Nenhum arquivo carregado ou coluna 'cor_1' ausente."

    cores_planilha = df_global['cor_1'].dropna().unique()
    cores_mapeadas = [k.lower().strip() for k in mapeamento_cores.keys()]
    cores_novas = [c for c in cores_planilha if c.lower().strip() not in cores_mapeadas]

    sugestoes = [{'cor_1': cor, 'cor_pai_sugerida': classificar_cor_pai(cor)} for cor in cores_novas]

    return render_template('classificar_cores.html', sugestoes=sugestoes)

@app.route('/atualizar_cores', methods=['POST'])
def atualizar_cores():
    global df_global, mapeamento_cores

    if df_global is None:
        return "Nenhum arquivo carregado."

    novas_classificacoes = {}
    for key in request.form:
        if key.startswith('cor_'):
            cor_original = key[4:]
            nova_cor_pai = request.form[key]
            novas_classificacoes[cor_original] = nova_cor_pai

    # Atualiza dicionário manual
    mapeamento_cores.update(novas_classificacoes)
    salvar_mapeamento_csv(mapeamento_cores)

    # Reclassifica com novos dados
    df_global['cor_pai'] = df_global['cor_1'].apply(classificar_cor_pai)

    return redirect(url_for('index'))

@app.route('/analise', methods=['GET', 'POST'])
def analise():
    global df_global

    df_completo = None

    if df_global is None:
        return "Nenhum arquivo foi carregado ainda."

    sub_grupos = sorted(df_global['nome_sub_grupo'].dropna().unique())
    secoes = sorted(df_global['nome_secao'].dropna().unique())
    produtos = sorted(df_global['nome_produto'].dropna().unique())

    filtro_sub_grupo = request.form.get('nome_sub_grupo') or request.args.get('nome_sub_grupo', '')
    filtro_secao = request.form.get('nome_secao') or request.args.get('nome_secao', '')
    filtro_produto = request.form.get('nome_produto') or request.args.get('nome_produto', '')

    df_filtrado = df_global.copy()

    if filtro_sub_grupo:
        df_filtrado = df_filtrado[df_filtrado['nome_sub_grupo'] == filtro_sub_grupo]
    if filtro_secao:
        df_filtrado = df_filtrado[df_filtrado['nome_secao'] == filtro_secao]
    if filtro_produto:
        df_filtrado = df_filtrado[df_filtrado['nome_produto'] == filtro_produto]

    if not df_filtrado.empty:
        total_por_loja = df_filtrado.groupby('codigo_loja')['Estoque'].sum().reset_index()
        tem_dados = True
    else:
        total_por_loja = None
        tem_dados = False

    if not df_filtrado.empty:
        df_comparativo = df_filtrado.groupby(['codigo_loja', 'cor_pai', 'tamanho'], observed=True)['Estoque'].sum().reset_index()
        todas_lojas = df_filtrado['codigo_loja'].unique()
        todas_cores = df_filtrado['cor_pai'].unique()
        todos_tamanhos = df_filtrado['tamanho'].unique()

        combinacoes = pd.MultiIndex.from_product(
            [todas_lojas, todas_cores, todos_tamanhos],
            names=['codigo_loja', 'cor_pai', 'tamanho']
        )

        df_completo = df_comparativo.set_index(['codigo_loja', 'cor_pai', 'tamanho']) \
            .reindex(combinacoes, fill_value=0) \
            .reset_index()

        df_completo['status'] = df_completo['Estoque'].apply(
            lambda x: 'sobra' if x > 1 else ('falta' if x == 0 else 'ok')
        )

        recomendacoes = []

        for cor in todas_cores:
            for tam in todos_tamanhos:
                sobras_deposito = df_completo[(
                    df_completo['cor_pai'] == cor) &
                    (df_completo['tamanho'] == tam) &
                    (df_completo['status'] == 'sobra') &
                    (df_completo['codigo_loja'] == 99)
                ]

                sobras_lojas = df_completo[(
                    df_completo['cor_pai'] == cor) &
                    (df_completo['tamanho'] == tam) &
                    (df_completo['status'] == 'sobra') &
                    (df_completo['codigo_loja'] != 99) &
                    (df_completo['codigo_loja'] != 98)
                ]

                faltas = df_completo[(
                    df_completo['cor_pai'] == cor) &
                    (df_completo['tamanho'] == tam) &
                    (df_completo['status'] == 'falta') &
                    (df_completo['codigo_loja'] != 98)
                ]

                for _, row_falta in faltas.iterrows():
                    if not sobras_deposito.empty:
                        row_sobra = sobras_deposito.iloc[0]
                        recomendacoes.append({
                            'cor_pai': cor,
                            'tamanho': tam,
                            'loja_origem': row_sobra['codigo_loja'],
                            'loja_destino': row_falta['codigo_loja'],
                            'quantidade': 1
                        })
                        df_completo.loc[
                            (df_completo['codigo_loja'] == row_sobra['codigo_loja']) &
                            (df_completo['cor_pai'] == cor) &
                            (df_completo['tamanho'] == tam),
                            'Estoque'
                        ] -= 1
                        estoque_atual = df_completo.loc[
                            (df_completo['codigo_loja'] == row_sobra['codigo_loja']) &
                            (df_completo['cor_pai'] == cor) &
                            (df_completo['tamanho'] == tam),
                            'Estoque'
                        ].values[0]
                        if estoque_atual <= 1:
                            sobras_deposito = sobras_deposito.iloc[1:]

                    elif not sobras_lojas.empty:
                        row_sobra = sobras_lojas.iloc[0]
                        recomendacoes.append({
                            'cor_pai': cor,
                            'tamanho': tam,
                            'loja_origem': row_sobra['codigo_loja'],
                            'loja_destino': row_falta['codigo_loja'],
                            'quantidade': 1
                        })
                        df_completo.loc[
                            (df_completo['codigo_loja'] == row_sobra['codigo_loja']) &
                            (df_completo['cor_pai'] == cor) &
                            (df_completo['tamanho'] == tam),
                            'Estoque'
                        ] -= 1
                        estoque_atual = df_completo.loc[
                            (df_completo['codigo_loja'] == row_sobra['codigo_loja']) &
                            (df_completo['cor_pai'] == cor) &
                            (df_completo['tamanho'] == tam),
                            'Estoque'
                        ].values[0]
                        if estoque_atual <= 1:
                            sobras_lojas = sobras_lojas.iloc[1:]
    else:
        recomendacoes = []

    if df_completo is not None and not df_completo.empty:
        df_completo_html = df_completo.to_dict(orient='records')
    else:
        df_completo_html = None

    # AQUI: total correto ANTES da paginação
    total_recomendacoes = len(recomendacoes)

    recomendacoes_paginadas = recomendacoes[:20]

    return render_template(
        'analise.html',
        sub_grupos=sub_grupos,
        secoes=secoes,
        produtos=produtos,
        filtro_sub_grupo=filtro_sub_grupo,
        filtro_secao=filtro_secao,
        filtro_produto=filtro_produto,
        total_por_loja=total_por_loja,
        tem_dados=tem_dados,
        recomendacoes=recomendacoes_paginadas,
        total_recomendacoes=total_recomendacoes,
        df_completo=df_completo_html
    )

@app.route('/analise_detalhada/<codigo_loja>') 
def analise_detalhada(codigo_loja):
    global df_global

    if df_global is None:
        return "Nenhum arquivo carregado ainda."

    try:
        codigo_loja_int = int(codigo_loja)
    except ValueError:
        return "Código de loja inválido."

    filtro_sub_grupo = request.args.get('nome_sub_grupo', '')
    filtro_secao = request.args.get('nome_secao', '')
    filtro_produto = request.args.get('nome_produto', '')

    df_filtrado = df_global.copy()

    if filtro_sub_grupo:
        df_filtrado = df_filtrado[df_filtrado['nome_sub_grupo'] == filtro_sub_grupo]
    if filtro_secao:
        df_filtrado = df_filtrado[df_filtrado['nome_secao'] == filtro_secao]
    if filtro_produto:
        df_filtrado = df_filtrado[df_filtrado['nome_produto'] == filtro_produto]

    if df_filtrado.empty:
        return f"Nenhum dado encontrado para os filtros aplicados."

    df_loja = df_filtrado[df_filtrado['codigo_loja'] == codigo_loja_int]

    if df_loja.empty:
        return f"Nenhum dado encontrado para a loja {codigo_loja} com os filtros aplicados."

    df_filtrado['cor_pai'] = df_filtrado['cor_1'].apply(classificar_cor_pai)
    df_filtrado['tamanho'] = df_filtrado['tamanho'].astype(str).str.strip().str.upper()
    df_loja.loc[:, 'cor_pai'] = df_loja['cor_1'].apply(classificar_cor_pai).str.strip().str.upper()
    df_loja['tamanho'] = df_loja['tamanho'].astype(str).str.strip().str.upper()

    agrupado_loja = df_loja.groupby(['cor_pai', 'tamanho'])['Estoque'].sum().reset_index()

    tamanhos_unicos = sorted(df_filtrado['tamanho'].unique())
    cores_unicas = sorted(df_filtrado['cor_pai'].unique())
    combinacoes_todas = [(cor, tam) for cor in cores_unicas for tam in tamanhos_unicos]

    df_completo = pd.DataFrame(combinacoes_todas, columns=['cor_pai', 'tamanho'])
    df_completo['cor_pai'] = df_completo['cor_pai'].str.strip().str.upper()
    df_completo['tamanho'] = df_completo['tamanho'].astype(str).str.strip().str.upper()
    agrupado_loja['cor_pai'] = agrupado_loja['cor_pai'].str.strip().str.upper()
    agrupado_loja['tamanho'] = agrupado_loja['tamanho'].astype(str).str.strip().str.upper()

    df_completo = df_completo.merge(agrupado_loja, on=['cor_pai', 'tamanho'], how='left')
    df_completo['Estoque'] = df_completo['Estoque'].fillna(0).astype(int)
    df_completo['Estoque'] = df_completo['Estoque'].apply(lambda x: max(0, x))

    df_completo_pivot = df_completo.pivot_table(index='cor_pai', columns='tamanho', values='Estoque', aggfunc='sum', fill_value=0)

    sobras = df_completo[df_completo['Estoque'] > 1].to_dict(orient='records')
    faltas = df_completo[df_completo['Estoque'] == 0].to_dict(orient='records')

    ordem_tamanhos_personalizada = ['PP', 'P', 'M', 'G', 'GG', 'XGG', 'G1', 'G2', 'G3', 'G4']
    tamanhos_unicos = df_completo['tamanho'].unique().tolist()
    tamanhos_letras = [t for t in tamanhos_unicos if not t.isdigit()]
    tamanhos_numericos = [t for t in tamanhos_unicos if t.isdigit()]

    def chave_tamanho(x):
        try:
            return ordem_tamanhos_personalizada.index(x)
        except ValueError:
            return len(ordem_tamanhos_personalizada) + ord(x[0]) if x else 9999

    tamanhos_letras_ordenados = sorted(tamanhos_letras, key=chave_tamanho)
    tamanhos_numericos_ordenados = sorted(tamanhos_numericos, key=lambda x: int(x))

    todos_tamanhos = tamanhos_letras_ordenados + tamanhos_numericos_ordenados
    grade = df_completo_pivot.to_dict(orient='index')

    return render_template(
        'analise_detalhada.html',
        codigo_loja=codigo_loja,
        filtro_sub_grupo=filtro_sub_grupo,
        filtro_secao=filtro_secao,
        filtro_produto=filtro_produto,
        grade=grade,
        sobras=sobras,
        faltas=faltas,
        todos_tamanhos=todos_tamanhos,
    )

def gerar_pdf_sobras(sobras, codigo_loja=None):
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", 'B', 14)
            title = "Relatório de Sobras"
            if codigo_loja:
                title += f" - Loja {codigo_loja}"
            self.cell(0, 10, title, ln=True, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', align='C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    
    # Cabeçalho da tabela com cor de fundo
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0)
    pdf.set_draw_color(200, 200, 200)
    
    pdf.cell(83, 10, "Cor Pai", 1, 0, 'C', True)
    pdf.cell(71, 10, "Tamanho", 1, 0, 'C', True)
    pdf.cell(36, 10, "Estoque", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 11)
    for sobra in sobras:
        pdf.cell(83, 8, sobra['cor_pai'], 1, 0, 'C')
        pdf.cell(71, 8, sobra['tamanho'], 1, 0, 'C')
        pdf.cell(36, 8, str(sobra['Estoque']), 1, 1, 'C')


    pdf_bytes = pdf.output(dest='S').encode('latin1')
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer

# Ajuste para o código que gera as sobras
@app.route('/download_pdf_sobras/<codigo_loja>', methods=['GET'])
def download_pdf_sobras(codigo_loja):
    global df_global

    if df_global is None:
        return "Nenhum arquivo carregado ainda."

    try:
        codigo_loja_int = int(codigo_loja)
    except ValueError:
        return "Código de loja inválido."

    filtro_sub_grupo = request.args.get('nome_sub_grupo', '')
    filtro_secao = request.args.get('nome_secao', '')
    filtro_produto = request.args.get('nome_produto', '')

    sobras = calcular_sobras_por_loja(df_global, codigo_loja_int, filtro_sub_grupo, filtro_secao, filtro_produto)

    pdf_buffer = gerar_pdf_sobras(sobras, codigo_loja_int)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"relatorio_sobras_{codigo_loja}.pdf",
        mimetype='application/pdf'
    )

    
@app.route('/download_pdf_faltas/<codigo_loja>', methods=['GET'])
def download_pdf_faltas(codigo_loja):
    global df_global

    if df_global is None:
        return "Nenhum arquivo carregado ainda."

    try:
        codigo_loja_int = int(codigo_loja)
    except ValueError:
        return "Código de loja inválido."

    # Filtros opcionais
    filtro_sub_grupo = request.args.get('nome_sub_grupo', '')
    filtro_secao = request.args.get('nome_secao', '')
    filtro_produto = request.args.get('nome_produto', '')

    df_filtrado = df_global.copy()

    if filtro_sub_grupo:
        df_filtrado = df_filtrado[df_filtrado['nome_sub_grupo'] == filtro_sub_grupo]
    if filtro_secao:
        df_filtrado = df_filtrado[df_filtrado['nome_secao'] == filtro_secao]
    if filtro_produto:
        df_filtrado = df_filtrado[df_filtrado['nome_produto'] == filtro_produto]

    if df_filtrado.empty:
        return "Nenhum dado encontrado para os filtros aplicados."

    df_filtrado['cor_pai'] = df_filtrado['cor_1'].apply(classificar_cor_pai).str.strip().str.upper()
    df_filtrado['tamanho'] = df_filtrado['tamanho'].astype(str).str.strip().str.upper()

    df_loja = df_filtrado[df_filtrado['codigo_loja'] == codigo_loja_int].copy()
    df_loja['cor_pai'] = df_loja['cor_pai'].str.strip().str.upper()
    df_loja['tamanho'] = df_loja['tamanho'].astype(str).str.strip().str.upper()

    agrupado_loja = df_loja.groupby(['cor_pai', 'tamanho'])['Estoque'].sum().reset_index()

    tamanhos_unicos = sorted(df_filtrado['tamanho'].unique())
    cores_unicas = sorted(df_filtrado['cor_pai'].unique())
    combinacoes_todas = [(cor, tam) for cor in cores_unicas for tam in tamanhos_unicos]

    df_completo = pd.DataFrame(combinacoes_todas, columns=['cor_pai', 'tamanho'])
    df_completo['cor_pai'] = df_completo['cor_pai'].str.strip().str.upper()
    df_completo['tamanho'] = df_completo['tamanho'].astype(str).str.strip().str.upper()
    agrupado_loja['cor_pai'] = agrupado_loja['cor_pai'].str.strip().str.upper()
    agrupado_loja['tamanho'] = agrupado_loja['tamanho'].astype(str).str.strip().str.upper()

    df_completo = df_completo.merge(agrupado_loja, on=['cor_pai', 'tamanho'], how='left')
    df_completo['Estoque'] = df_completo['Estoque'].fillna(0).astype(int)

    faltas = df_completo[df_completo['Estoque'] == 0].sort_values(by=['cor_pai', 'tamanho'])

    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", 'B', 14)
            self.cell(0, 10, f"Relatório de Faltas - Loja {codigo_loja}", ln=True, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', align='C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0)
    pdf.set_draw_color(200, 200, 200)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(95, 10, "Cor Pai", 1, 0, 'C', True)
    pdf.cell(95, 10, "Tamanho", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 11)
    for falta in faltas.to_dict(orient='records'):
        pdf.cell(95, 8, falta['cor_pai'], 1, 0, 'C')
        pdf.cell(95, 8, falta['tamanho'], 1, 1, 'C')

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"relatorio_faltas_{codigo_loja}.pdf",
        mimetype='application/pdf'
    )

@app.route('/carregar_recomendacoes', methods=['GET'])
def carregar_recomendacoes():
    global df_global

    pagina = int(request.args.get('pagina', 1))
    por_pagina = int(request.args.get('por_pagina', 30))

    if df_global is None:
        return jsonify({'recomendacoes': [], 'pagina': pagina, 'total_paginas': 0})

    filtro_sub_grupo = request.args.get('nome_sub_grupo', '')
    filtro_secao = request.args.get('nome_secao', '')
    filtro_produto = request.args.get('nome_produto', '')

    df_filtrado = df_global.copy()

    if filtro_sub_grupo:
        df_filtrado = df_filtrado[df_filtrado['nome_sub_grupo'] == filtro_sub_grupo]
    if filtro_secao:
        df_filtrado = df_filtrado[df_filtrado['nome_secao'] == filtro_secao]
    if filtro_produto:
        df_filtrado = df_filtrado[df_filtrado['nome_produto'] == filtro_produto]

    df_comparativo = df_filtrado.groupby(['codigo_loja', 'cor_pai', 'tamanho'])['Estoque'].sum().reset_index()
    todas_lojas = df_filtrado['codigo_loja'].unique()
    todas_cores = df_filtrado['cor_pai'].unique()
    todos_tamanhos = df_filtrado['tamanho'].unique()

    combinacoes = pd.MultiIndex.from_product(
        [todas_lojas, todas_cores, todos_tamanhos],
        names=['codigo_loja', 'cor_pai', 'tamanho']
    )

    df_completo = df_comparativo.set_index(['codigo_loja', 'cor_pai', 'tamanho']) \
        .reindex(combinacoes, fill_value=0) \
        .reset_index()

    df_completo['status'] = df_completo['Estoque'].apply(
        lambda x: 'sobra' if x > 1 else ('falta' if x == 0 else 'ok')
    )

    recomendacoes = []

    for cor in todas_cores:
        for tam in todos_tamanhos:
            sobras_deposito = df_completo[(df_completo['cor_pai'] == cor) & (df_completo['tamanho'] == tam) & (df_completo['status'] == 'sobra') & (df_completo['codigo_loja'] == 99)]
            sobras_lojas = df_completo[(df_completo['cor_pai'] == cor) & (df_completo['tamanho'] == tam) & (df_completo['status'] == 'sobra') & (df_completo['codigo_loja'] != 99) & (df_completo['codigo_loja'] != 98)]
            faltas = df_completo[(df_completo['cor_pai'] == cor) & (df_completo['tamanho'] == tam) & (df_completo['status'] == 'falta') & (df_completo['codigo_loja'] != 98)]

            for _, row_falta in faltas.iterrows():
                if not sobras_deposito.empty:
                    row_sobra = sobras_deposito.iloc[0]
                    recomendacoes.append({
                        'cor_pai': str(cor),
                        'tamanho': str(tam),
                        'loja_origem': int(row_sobra['codigo_loja']),
                        'loja_destino': int(row_falta['codigo_loja']),
                        'quantidade': 1
                    })
                    df_completo.loc[(df_completo['codigo_loja'] == row_sobra['codigo_loja']) & (df_completo['cor_pai'] == cor) & (df_completo['tamanho'] == tam), 'Estoque'] -= 1
                    estoque_atual = df_completo.loc[(df_completo['codigo_loja'] == row_sobra['codigo_loja']) & (df_completo['cor_pai'] == cor) & (df_completo['tamanho'] == tam), 'Estoque'].values[0]
                    if estoque_atual <= 1:
                        sobras_deposito = sobras_deposito.iloc[1:]
                elif not sobras_lojas.empty:
                    row_sobra = sobras_lojas.iloc[0]
                    recomendacoes.append({
                        'cor_pai': str(cor),
                        'tamanho': str(tam),
                        'loja_origem': int(row_sobra['codigo_loja']),
                        'loja_destino': int(row_falta['codigo_loja']),
                        'quantidade': 1
                    })
                    df_completo.loc[(df_completo['codigo_loja'] == row_sobra['codigo_loja']) & (df_completo['cor_pai'] == cor) & (df_completo['tamanho'] == tam), 'Estoque'] -= 1
                    estoque_atual = df_completo.loc[(df_completo['codigo_loja'] == row_sobra['codigo_loja']) & (df_completo['cor_pai'] == cor) & (df_completo['tamanho'] == tam), 'Estoque'].values[0]
                    if estoque_atual <= 1:
                        sobras_lojas = sobras_lojas.iloc[1:]

    total_paginas = (len(recomendacoes) + por_pagina - 1) // por_pagina
    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina
    paginadas = recomendacoes[inicio:fim]

    return jsonify({
        'recomendacoes': paginadas,
        'pagina': pagina,
        'total_paginas': total_paginas
    })

if __name__ == '__main__':
    app.run(debug=True)