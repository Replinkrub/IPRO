TX_ALIASES = {
    "date": {"data_emissao", "emissao", "data", "dt", "data_venda"},
    "order_id": {"pedido", "order", "n_pedido", "doc"},
    "client": {"cliente", "razao_social", "nome_fantasia"},
    "seller": {"criador", "vendedor", "representante"},
    "price": {"preco", "preco_liquido", "valor_unit", "vl_unit"},
    "qty": {"quantidade", "qtd", "qde", "qtde", "quant"},
    "subtotal": {"total", "vl_total", "valor_total"},
    "product": {"produto", "item", "descricao"},
    "sku": {"sku", "codigo", "cod_prod"},
    "uf": {"uf", "estado", "sigla_uf"},
}

CUSTOMER_ALIASES = {
    "client": {"cliente", "razao_social", "nome_fantasia", "cliente_nome"},
    "cnpj": {"cnpj"},
    "ie": {"insc._estadual", "insc_estadual"},
    "uf": {"uf", "estado", "sigla_uf"},
    "city": {"cidade"},
}


def apply_aliases(df, aliases: dict):
    """
    Mapear colunas de um DataFrame para nomes canônicos de acordo com um dicionário de aliases.

    Esta função usa um mapeamento `aliases` onde cada chave canônica (por exemplo, ``date``) possui
    um conjunto de aliases possíveis (como ``data_emissao``, ``emissao`` etc.). Para cada coluna
    presente no DataFrame, tenta-se encontrar um alias correspondente (insensível a maiúsculas ou
    minúsculas) e, se encontrado, cria-se uma nova coluna com o nome canônico apontando para os
    mesmos dados da coluna original.

    Foi adicionada a conversão de nomes de colunas para ``str`` antes de aplicar ``lower()`` e
    ``strip()``, pois alguns DataFrames podem ter nomes de coluna numéricos (ex.: 0, 1, 2). Sem
    essa conversão, ocorria o erro ``'int' object has no attribute 'lower'`` durante a extração
    de dados.

    Parâmetros
    ----------
    df : pandas.DataFrame
        DataFrame de origem no qual as colunas serão mapeadas.
    aliases : dict
        Dicionário onde cada chave é o nome canônico da coluna e o valor é um conjunto de aliases
        possíveis (todos em minúsculo). Exemplo: ``{"date": {"data_emissao", "emissao"}}``.

    Retorna
    -------
    df : pandas.DataFrame
        O próprio DataFrame com as colunas canônicas adicionadas quando aplicável.
    """
    # Construir mapa de colunas existentes para suas formas normalizadas (lowercase, sem espaços)
    cols = {str(c).lower().strip(): c for c in df.columns}
    out = {}
    # Procurar por aliases e definir mapeamento para colunas canônicas
    for canon, alts in aliases.items():
        for a in alts:
            if a in cols:
                out[canon] = cols[a]
                break
    # Adicionar novas colunas canônicas ao DataFrame
    for canon, src in out.items():
        # Copiar apenas se a coluna original existir
        df[canon] = df[src]
    return df
