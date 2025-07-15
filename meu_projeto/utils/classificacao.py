import pandas as pd
import os
from config import MAPEAMENTO_CSV, MAPEAMENTO_AUTOMATICO

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

    if cor_lower in [k.lower().strip() for k in mapeamento_cores]:
        return mapeamento_cores.get(cor_lower, 'Outras')

    for palavra, cor_pai in MAPEAMENTO_AUTOMATICO.items():
        if palavra in cor_lower:
            return cor_pai

    return 'Outras'
