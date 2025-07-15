from io import BytesIO
import pandas as pd
from .classificacao import classificar_cor_pai

def calcular_sobras_por_loja(df_global, codigo_loja_int, filtro_sub_grupo='', filtro_secao='', filtro_produto=''):
    df_filtrado = df_global.copy()

    if filtro_sub_grupo:
        df_filtrado = df_filtrado[df_filtrado['nome_sub_grupo'] == filtro_sub_grupo]
    if filtro_secao:
        df_filtrado = df_filtrado[df_filtrado['nome_secao'] == filtro_secao]
    if filtro_produto:
        df_filtrado = df_filtrado[df_filtrado['nome_produto'] == filtro_produto]

    df_loja = df_filtrado[df_filtrado['codigo_loja'] == codigo_loja_int].copy()  # <-- copy aqui

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