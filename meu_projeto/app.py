from flask import Flask, request, render_template
import pandas as pd
import os
from flask import redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

df_global = None  # Armazena o DataFrame carregado
MAPEAMENTO_CSV = 'mapeamento_cores.csv'  # Arquivo persistente

# Dicionário automático de fallback
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

# =================== Funções de persistência ===================
def carregar_mapeamento_csv():
    if os.path.exists(MAPEAMENTO_CSV):
        return pd.read_csv(MAPEAMENTO_CSV).set_index('cor_1')['cor_pai'].to_dict()
    return {}

def salvar_mapeamento_csv(dicionario):
    df = pd.DataFrame(list(dicionario.items()), columns=['cor_1', 'cor_pai'])
    df.to_csv(MAPEAMENTO_CSV, index=False)

mapeamento_cores = carregar_mapeamento_csv()

# =================== Classificação de cor ===================
def classificar_cor_pai(cor):
    if pd.isna(cor):
        return 'Desconhecido'

    cor_lower = cor.lower().strip()

    # Mapeamento manual
    for key in mapeamento_cores:
        if key.lower().strip() == cor_lower:
            return mapeamento_cores[key]

    # Fallback automático
    for palavra, cor_pai in MAPEAMENTO_AUTOMATICO.items():
        if palavra in cor_lower:
            return cor_pai

    return 'Outras'

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
        recomendacoes=recomendacoes,
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

    # Recebe filtros da query string
    filtro_sub_grupo = request.args.get('nome_sub_grupo', '')
    filtro_secao = request.args.get('nome_secao', '')
    filtro_produto = request.args.get('nome_produto', '')

    # Filtra o DataFrame conforme filtros escolhidos
    df_filtrado = df_global.copy()

    if filtro_sub_grupo:
        df_filtrado = df_filtrado[df_filtrado['nome_sub_grupo'] == filtro_sub_grupo]
    if filtro_secao:
        df_filtrado = df_filtrado[df_filtrado['nome_secao'] == filtro_secao]
    if filtro_produto:
        df_filtrado = df_filtrado[df_filtrado['nome_produto'] == filtro_produto]

    if df_filtrado.empty:
        return f"Nenhum dado encontrado para os filtros aplicados."

    # Agora filtra somente a loja escolhida
    df_loja = df_filtrado[df_filtrado['codigo_loja'] == codigo_loja_int]

    if df_loja.empty:
        return f"Nenhum dado encontrado para a loja {codigo_loja} com os filtros aplicados."

    # Atualiza cor_pai
    df_loja['cor_pai'] = df_loja['cor_1'].apply(classificar_cor_pai)

    # Agrupa por cor_pai e tamanho para somar estoque na loja
    agrupado_loja = df_loja.groupby(['cor_pai', 'tamanho'])['Estoque'].sum().reset_index()

    # Para montar a grade completa: para cada cor_pai, pegar os tamanhos existentes no grupo filtrado (independente da loja)
    cores_tamanhos_por_cor = df_filtrado.groupby('cor_pai')['tamanho'].unique().to_dict()

    # Monta lista de tuplas cor_pai x tamanho baseado na combinação real por cor
    combinacoes = []
    for cor, tamanhos in cores_tamanhos_por_cor.items():
        for tam in tamanhos:
            combinacoes.append((cor, tam))

    # Cria DataFrame com todas as combinações possíveis para o grupo filtrado
    df_completo = pd.DataFrame(combinacoes, columns=['cor_pai', 'tamanho'])

    # Padroniza tamanho para evitar espaços e letras minúsculas
    df_completo['tamanho'] = df_completo['tamanho'].str.strip().str.upper()
    agrupado_loja['tamanho'] = agrupado_loja['tamanho'].str.strip().str.upper()

    # Junta o estoque da loja, se existir, senão preenche com zero
    df_completo = df_completo.merge(agrupado_loja, on=['cor_pai', 'tamanho'], how='left')
    df_completo['Estoque'] = df_completo['Estoque'].fillna(0).astype(int)

    # Convertendo para formato pivô (tamanhos como colunas)
    df_completo_pivot = df_completo.pivot_table(index='cor_pai', columns='tamanho', values='Estoque', aggfunc='sum', fill_value=0)

    # Sobras e faltas para exibir separadamente
    sobras = df_completo[df_completo['Estoque'] > 1].to_dict(orient='records')  # Estoque > 1
    faltas = df_completo[df_completo['Estoque'] == 0].to_dict(orient='records')  # Estoque == 0

    # Ordem desejada (você pode adicionar mais se quiser)
    ordem_tamanhos_personalizada = ['PP', 'P', 'M', 'G', 'GG', 'XGG', 'G1', 'G2', 'G3', 'G4']

    # Obtém tamanhos únicos já padronizados
    tamanhos_unicos = df_completo['tamanho'].unique().tolist()

    # Separa tamanhos alfabéticos e numéricos
    tamanhos_letras = [t for t in tamanhos_unicos if not t.isdigit()]
    tamanhos_numericos = [t for t in tamanhos_unicos if t.isdigit()]

    # Função para chave de ordenação usando a ordem personalizada
    def chave_tamanho(x):
        try:
            return ordem_tamanhos_personalizada.index(x)
        except ValueError:
            # Se não estiver na lista, colocar após os listados e ordenar alfabeticamente
            return len(ordem_tamanhos_personalizada) + ord(x[0]) if x else 9999

    # Ordena os tamanhos
    tamanhos_letras_ordenados = sorted(tamanhos_letras, key=chave_tamanho)
    tamanhos_numericos_ordenados = sorted(tamanhos_numericos, key=lambda x: int(x))

    todos_tamanhos = tamanhos_letras_ordenados + tamanhos_numericos_ordenados

    # Converter a grade para dicionário para enviar para o template
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
        todos_tamanhos=todos_tamanhos,  # Passando todos os tamanhos para o template
    )


if __name__ == '__main__':
    app.run(debug=True)