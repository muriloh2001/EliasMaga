from flask_caching import Cache

def setup_cache(app):
    cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})
    return cache

def get_df_filtrado(df_global, filtro_sub_grupo, filtro_secao, filtro_produto):
    df = df_global.copy()
    if filtro_sub_grupo:
        df = df[df['nome_sub_grupo'] == filtro_sub_grupo]
    if filtro_secao:
        df = df[df['nome_secao'] == filtro_secao]
    if filtro_produto:
        df = df[df['nome_produto'] == filtro_produto]
    return df
