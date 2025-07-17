from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from io import BytesIO
import os
import pandas as pd
from fpdf import FPDF

from app import app, df_global, mapeamento_cores
from config import COLUNAS_RELEVANTES, TIPOS_COLUNAS
from utils.classificacao import classificar_cor_pai, salvar_mapeamento_csv
from utils.filtros import get_df_filtrado
from utils.estoque import calcular_sobras_por_loja
from utils.relatorios import gerar_pdf_sobras_grade, gerar_pdf_faltas_grade
from utils.grade_ideal import obter_grade_ideal

routes_bp = Blueprint('routes_bp', __name__)

@routes_bp.route('/', methods=['GET', 'POST'])
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

            df_global['cor_pai'] = df_global['cor_1'].apply(classificar_cor_pai).str.strip().str.upper()
            df_global['tamanho'] = df_global['tamanho'].astype(str).str.upper().str.strip()
            df_global['tamanho_num'] = pd.to_numeric(df_global['tamanho'], errors='coerce')

            # Verifica se há cores novas
            cores_planilha = df_global['cor_1'].dropna().unique()
            cores_mapeadas = [k.lower().strip() for k in mapeamento_cores.keys()]
            cores_novas = [c for c in cores_planilha if c.lower().strip() not in cores_mapeadas]

            if cores_novas:
                flash(f"Atenção! Existem {len(cores_novas)} cores ainda não classificadas. Você pode classificá-las agora ou continuar.", "warning")

            flash("Arquivo carregado com sucesso!", "success")
            return redirect(url_for('routes_bp.analise'))  # Sempre segue para análise

    return render_template('index.html')




@routes_bp.route('/classificar_cores', methods=['GET'])
def classificar_cores():
    global df_global

    if df_global is None or 'cor_1' not in df_global.columns:
        return "Nenhum arquivo carregado ou coluna 'cor_1' ausente."

    cores_planilha = df_global['cor_1'].dropna().unique()
    cores_mapeadas = [k.lower().strip() for k in mapeamento_cores.keys()]
    cores_novas = [c for c in cores_planilha if c.lower().strip() not in cores_mapeadas]

    sugestoes = [{'cor_1': cor, 'cor_pai_sugerida': classificar_cor_pai(cor)} for cor in cores_novas]

    return render_template('classificar_cores.html', sugestoes=sugestoes)

@routes_bp.route('/atualizar_cores', methods=['POST'])
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

@routes_bp.route('/analise', methods=['GET', 'POST'])
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

    df_filtrado = get_df_filtrado(df_global, filtro_sub_grupo, filtro_secao, filtro_produto)
    
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

@routes_bp.route('/analise_detalhada/<codigo_loja>')
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

    df_loja = df_filtrado[df_filtrado['codigo_loja'] == codigo_loja_int].copy()

    if df_loja.empty:
        return f"Nenhum dado encontrado para a loja {codigo_loja} com os filtros aplicados."

    # Normaliza colunas
    df_filtrado['cor_pai'] = df_filtrado['cor_1'].apply(classificar_cor_pai).str.strip().str.upper()
    df_filtrado['tamanho'] = df_filtrado['tamanho'].astype(str).str.strip().str.upper()
    df_loja['cor_pai'] = df_loja['cor_1'].apply(classificar_cor_pai).str.strip().str.upper()
    df_loja['tamanho'] = df_loja['tamanho'].astype(str).str.strip().str.upper()

    # Estoque da loja
    agrupado_loja = df_loja.groupby(['cor_pai', 'tamanho'])['Estoque'].sum().reset_index()

    tamanhos_unicos = sorted(df_filtrado['tamanho'].unique())
    cores_unicas = sorted(df_filtrado['cor_pai'].unique())
    combinacoes_todas = [(cor, tam) for cor in cores_unicas for tam in tamanhos_unicos]

    df_completo = pd.DataFrame(combinacoes_todas, columns=['cor_pai', 'tamanho'])
    agrupado_loja['cor_pai'] = agrupado_loja['cor_pai'].str.strip().str.upper()
    agrupado_loja['tamanho'] = agrupado_loja['tamanho'].astype(str).str.strip().str.upper()
    df_completo = df_completo.merge(agrupado_loja, on=['cor_pai', 'tamanho'], how='left')
    df_completo['Estoque'] = df_completo['Estoque'].fillna(0).astype(int)
    df_completo['Estoque'] = df_completo['Estoque'].apply(lambda x: max(0, x))

    # 🔢 Ordenação dos tamanhos
    ordem_tamanhos_personalizada = ['PP', 'P', 'M', 'G', 'GG', 'XGG', 'G1', 'G2', 'G3', 'G4']
    tamanhos_unicos = df_completo['tamanho'].unique().tolist()
    tamanhos_letras = [t for t in tamanhos_unicos if not t.isdigit()]
    tamanhos_numericos = [t for t in tamanhos_unicos if t.isdigit()]

    def chave_tamanho(x):
        try:
            return ordem_tamanhos_personalizada.index(x)
        except ValueError:
            return len(ordem_tamanhos_personalizada) + int(x) if x.isdigit() else 9999

    tamanhos_letras_ordenados = sorted(tamanhos_letras, key=chave_tamanho)
    tamanhos_numericos_ordenados = sorted(tamanhos_numericos, key=lambda x: int(x))
    todos_tamanhos = tamanhos_letras_ordenados + tamanhos_numericos_ordenados

    # 🧠 Grade ideal
    df_completo['qtd_ideal'] = df_completo.apply(
        lambda row: obter_grade_ideal(row['cor_pai'], row['tamanho'], filtro_sub_grupo),
        axis=1
    )

    df_completo['diferenca'] = df_completo['Estoque'] - df_completo['qtd_ideal']

    # 🔄 Pivot para tabelas
    df_completo_pivot = df_completo.pivot_table(
        index='cor_pai', columns='tamanho', values='Estoque', aggfunc='sum', fill_value=0
    ).reindex(columns=todos_tamanhos, fill_value=0)

    pivot_ideal = df_completo.pivot_table(
        index='cor_pai', columns='tamanho', values='qtd_ideal', aggfunc='sum', fill_value=0
    ).reindex(columns=todos_tamanhos, fill_value=0)

    pivot_sobras = df_completo[df_completo['diferenca'] > 0].pivot_table(
        index='cor_pai', columns='tamanho', values='diferenca', aggfunc='sum', fill_value=0
    ).reindex(columns=todos_tamanhos, fill_value=0)

    pivot_faltas = df_completo[df_completo['diferenca'] < 0].pivot_table(
        index='cor_pai', columns='tamanho', values='diferenca',
        aggfunc=lambda x: 'X' if len(x) else '', fill_value=''
    ).reindex(columns=todos_tamanhos, fill_value='')

    # 🎯 Dicionários para o template
    grade = df_completo_pivot.to_dict(orient='index')
    grade_ideal = pivot_ideal.to_dict(orient='index')
    grade_sobras = pivot_sobras.to_dict(orient='index')
    grade_faltas = pivot_faltas.to_dict(orient='index')

    # Listas auxiliares simples
    sobras = df_completo[df_completo['diferenca'] > 0].to_dict(orient='records')
    faltas = df_completo[df_completo['diferenca'] < 0].to_dict(orient='records')

    return render_template(
        'analise_detalhada.html',
        codigo_loja=codigo_loja,
        filtro_sub_grupo=filtro_sub_grupo,
        filtro_secao=filtro_secao,
        filtro_produto=filtro_produto,
        grade=grade,
        grade_ideal=grade_ideal,
        grade_sobras=grade_sobras,
        grade_faltas=grade_faltas,
        todos_tamanhos=todos_tamanhos,
        sobras=sobras,
        faltas=faltas
    )


# Ajuste para o código que gera as sobras
@routes_bp.route('/download_pdf_sobras/<codigo_loja>', methods=['GET'])
def download_pdf_sobras(codigo_loja):
    global df_global

    if df_global is None:
        return "Nenhum arquivo carregado ainda."

    try:
        codigo_loja_int = int(codigo_loja)
    except ValueError:
        return "Código de loja inválido."

    # Filtros
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
    df_completo = df_completo.merge(agrupado_loja, on=['cor_pai', 'tamanho'], how='left')
    df_completo['Estoque'] = df_completo['Estoque'].fillna(0).astype(int)
    df_completo['Estoque'] = df_completo['Estoque'].apply(lambda x: max(0, x))

    # GRADE DE SOBRAS
    df_sobras = df_completo[df_completo['Estoque'] > 1]

    ordem_tamanhos_personalizada = ['PP', 'P', 'M', 'G', 'GG', 'XGG', 'G1', 'G2', 'G3', 'G4']
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

    pivot_sobras = df_sobras.pivot_table(
        index='cor_pai', columns='tamanho', values='Estoque', aggfunc='sum', fill_value=0
    )
    pivot_sobras = pivot_sobras.reindex(columns=todos_tamanhos, fill_value=0)
    grade_sobras = pivot_sobras.to_dict(orient='index')

    from utils.relatorios import gerar_pdf_sobras_grade
    pdf_buffer = gerar_pdf_sobras_grade(grade_sobras, todos_tamanhos, codigo_loja_int, nome_grupo=filtro_sub_grupo)


    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"relatorio_sobras_{codigo_loja}.pdf",
        mimetype='application/pdf'
    )


    
@routes_bp.route('/download_pdf_faltas/<codigo_loja>', methods=['GET'])
def download_pdf_faltas(codigo_loja):
    global df_global

    if df_global is None:
        return "Nenhum arquivo carregado ainda."

    try:
        codigo_loja_int = int(codigo_loja)
    except ValueError:
        return "Código de loja inválido."

    # Filtros
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
    df_completo = df_completo.merge(agrupado_loja, on=['cor_pai', 'tamanho'], how='left')
    df_completo['Estoque'] = df_completo['Estoque'].fillna(0).astype(int)

    df_faltas = df_completo[df_completo['Estoque'] == 0]

    # Ordenar tamanhos personalizados
    ordem_tamanhos_personalizada = ['PP', 'P', 'M', 'G', 'GG', 'XGG', 'G1', 'G2', 'G3', 'G4']
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

    # GRADE de faltas
    pivot_faltas = df_faltas.pivot_table(
        index='cor_pai', columns='tamanho', values='Estoque',
        aggfunc=lambda x: '❌' if len(x) else '', fill_value=''
    )
    pivot_faltas = pivot_faltas.reindex(columns=todos_tamanhos, fill_value='')

    grade_faltas = pivot_faltas.to_dict(orient='index')

    # Substituir ❌ por 'X' só no PDF para evitar erro de codificação latin1
    for cor, tamanhos in grade_faltas.items():
        for t in tamanhos:
            if tamanhos[t] == '❌':
                tamanhos[t] = 'X'

    from utils.relatorios import gerar_pdf_faltas_grade
    pdf_buffer = gerar_pdf_faltas_grade(grade_faltas, todos_tamanhos, codigo_loja_int, nome_grupo=filtro_sub_grupo)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"relatorio_faltas_{codigo_loja}.pdf",
        mimetype='application/pdf'
    )

@routes_bp.route('/carregar_recomendacoes', methods=['GET'])
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