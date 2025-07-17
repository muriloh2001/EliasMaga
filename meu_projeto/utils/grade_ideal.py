def obter_grade_ideal(cor_pai, tamanho, sub_grupo):
    grupos_personalizados = [
        'CAMISA SOCIAL M/L P1 R$59,99 A R$99,99',
        'CAMISA SOCIAL M/L P2 R$109,99 A R$159,99',
        'CAMISA SOCIAL M/L P3 R$169,99 A R$199,99',
        'CAMISA SOCIAL M/L P4 R$200,00 +'
    ]

    print(f"Debug: sub_grupo recebido -> '{sub_grupo}'")
    print(f"Grupos válidos: {grupos_personalizados}")

    if sub_grupo not in grupos_personalizados:
        return 0

    try:
        tamanho_num = int(tamanho)
    except ValueError:
        return 0  # Ignora tamanhos não numéricos, mas retorna zero

    # 🎯 Lógica especial para o grupo P4
    if sub_grupo == 'CAMISA SOCIAL M/L P4 R$200,00 +':
        if 1 <= tamanho_num <= 12:
            return 1
        else:
            return 0

    # 🧠 Lógica original para P1, P2, P3
    cores_principais = ['PRETO', 'BRANCO', 'AZUL']

    if cor_pai.upper() in cores_principais:
        return 2 if tamanho_num <= 6 else 1
    else:
        return 1
