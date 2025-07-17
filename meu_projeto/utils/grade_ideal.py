def obter_grade_ideal(cor_pai, tamanho, sub_grupo):
    grupos_validos = [
        'CAMISA SOCIAL M/L P1 R$59,99 A R$99,99',
        'CAMISA SOCIAL M/L P2 R$109,99 A R$159,99',
        'CAMISA SOCIAL M/L P3 R$169,99 A R$199,99'
    ]
    print(f"Debug: sub_grupo recebido -> '{sub_grupo}'")
    print(f"Grupos válidos: {grupos_validos}")

    if sub_grupo not in grupos_validos:
        return 0  # Ou algum valor padrão

    try:
        tamanho_num = int(tamanho)
    except ValueError:
        return 0  # Ignora tamanhos não numéricos, mas retorna zero

    cores_principais = ['PRETO', 'BRANCO', 'AZUL']

    if cor_pai.upper() in cores_principais:
        if tamanho_num <= 6:
            return 2
        else:
            return 1
    else:
        return 1
