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
        return 'OUTRAS'

    cor_lower = cor.lower().strip()
    mapeamento_normalizado = {k.lower().strip(): v for k, v in mapeamento_cores.items()}

    # Primeiro tenta pelo mapeamento manual
    if cor_lower in mapeamento_normalizado:
        return mapeamento_normalizado[cor_lower]

    # Depois tenta pelo mapeamento automático
    for palavra, cor_pai in MAPEAMENTO_AUTOMATICO.items():
        if palavra in cor_lower:
            return cor_pai

    return 'OUTRAS'

