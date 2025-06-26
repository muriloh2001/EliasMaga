import os
import pandas as pd
import joblib
from flask import Flask, render_template, request, session, redirect, send_file
import openrouteservice
from urllib.parse import quote
from ia_utils import reclassificar_kmeans, atualizar_modelos_e_rotulos
from datetime import datetime
import logging
from routes.upload import bp_upload
from functools import lru_cache

app = Flask(__name__)
app.secret_key = "secreta"

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

rotulos_path = "cores_para_rotular.xlsx"
modelo = joblib.load("modelo_embeddings_cores.pkl")
kmeans = joblib.load("modelo_kmeans_cores.pkl")

ORS_API_KEY = os.getenv("ORS_API_KEY", "API_KEY_AQUI")
ors_client = openrouteservice.Client(key=ORS_API_KEY)

coordenadas_lojas = {
    1: (-25.5332, -49.2222), 2: (-25.3689, -49.2162), 3: (-25.4427, -49.0623), 4: (-25.3031, -49.0551),
    5: (-25.5912, -49.3533), 6: (-25.6634, -49.3133), 7: (-25.5862, -49.4102), 9: (-25.6612, -49.3074),
    10: (-25.4711, -49.3355), 11: (-25.0921, -50.1634), 12: (-24.9151, -50.0982), 99: (-25.496099, -49.247799)
}

enderecos_lojas = {
    1: "Rua São José dos Pinhais, 107, Curitiba", 2: "Rua Arquimedes, 18, Colombo", 3: "Av. Getúlio Vargas, 894, Piraquara",
    4: "Rua João Trevisan, 959, Campina Grande do Sul", 5: "Rua Enette Dubard, 481, Curitiba",
    6: "Rua Cesar Carelli, 261, Fazenda Rio Grande", 7: "Rua Carlos Cavalcanti, 69, Araucária",
    9: "Rua Jacarandá, 208, Fazenda Rio Grande", 10: "Rua Raul Pompéia, 374, Curitiba",
    11: "Rua Fernandes Pinheiro, 74, Ponta Grossa", 12: "Avenida do Ouro, 128, Carambeí",
    99: "R. Dr. Simão Kossobudski, 1531, Curitiba"
}

app.register_blueprint(bp_upload)


def normalizar_texto(texto):
    return str(texto).strip().lower()


@lru_cache()
def carregar_rotulos_e_grupo():
    rotulos = pd.read_excel(rotulos_path)
    rotulos["cor_normalizada"] = rotulos["cor_normalizada"].apply(normalizar_texto)
    if "grupo_cor" in rotulos.columns:
        grupo_para_cor_pai = rotulos.groupby("grupo_cor")["cor_pai"].agg(
            lambda x: x.mode().iloc[0] if not x.mode().empty else "Não definido"
        ).to_dict()
    else:
        grupo_para_cor_pai = {}
    return rotulos, grupo_para_cor_pai


def mapa(loja):
    endereco = enderecos_lojas.get(loja)
    if endereco:
        return f"https://www.google.com/maps/search/?api=1&query={quote(endereco)}"
    return "#"


def ordena_tamanho(x):
    p = {"PP": 1, "P": 2, "M": 3, "G": 4, "GG": 5, "XG": 6, "XGG": 7}
    return p.get(str(x).upper(), 1000)


def calcular_rota(origem, destino):
    try:
        coords = [coordenadas_lojas[origem], coordenadas_lojas[destino]]
        route = ors_client.directions(coords)
        dist_km = route["routes"][0]["summary"]["distance"] / 1000
        dur_min = route["routes"][0]["summary"]["duration"] / 60
        return dist_km, dur_min
    except Exception as e:
        logging.error(f"Erro ao calcular rota: {e}")
        return None, None


# === Inicializa ===
rotulos, grupo_para_cor_pai = carregar_rotulos_e_grupo()


@app.route("/", methods=["GET", "POST"])
@app.route("/analise", methods=["GET", "POST"])
def analise():
    global rotulos, grupo_para_cor_pai
    rotulos, grupo_para_cor_pai = carregar_rotulos_e_grupo()

    dados = pd.read_excel("Tabela.xlsx")
    dados["cor_normalizada"] = dados["cor_1"].apply(normalizar_texto)

    colunas_merge = ["cor_normalizada"]
    if "cor_pai" in rotulos.columns:
        colunas_merge.append("cor_pai")

    dados = dados.merge(rotulos[colunas_merge], on="cor_normalizada", how="left")

    if "cor_pai" not in dados.columns:
        dados["cor_pai"] = None

    dados["cor_final"] = dados["cor_pai"].fillna(dados["cor_1"])

    if request.method == "POST":
        session["subgrupo"] = request.form.get("subgrupo")
        session["secao"] = request.form.get("secao")

    if session.get("subgrupo"):
        dados = dados[dados["nome_sub_grupo"] == session["subgrupo"]]
    if session.get("secao"):
        dados = dados[dados["nome_secao"] == session["secao"]]

    faltas, sobras, sugestoes = [], [], []
    if not dados.empty:
        lojas = dados["codigo_loja"].unique()
        comb = dados[["cor_final", "tamanho"]].drop_duplicates()
        for _, row in comb.iterrows():
            cor, tam = row["cor_final"], row["tamanho"]
            lojas_com_item = dados[(dados["cor_final"] == cor) & (dados["tamanho"] == tam)]["codigo_loja"].value_counts().to_dict()
            for loja in lojas:
                qtd = lojas_com_item.get(loja, 0)
                if qtd == 0:
                    faltas.append({"cor": cor, "tamanho": tam, "loja": loja})
                elif qtd > 1:
                    sobras.append({"cor": cor, "tamanho": tam, "loja": loja, "quantidade": qtd})
        for falta in faltas:
            for sobra in sobras:
                if falta["cor"] == sobra["cor"] and falta["tamanho"] == sobra["tamanho"] and sobra["quantidade"] > 1:
                    sugestoes.append({
                        "cor": falta["cor"],
                        "tamanho": falta["tamanho"],
                        "loja_origem": sobra["loja"],
                        "loja_destino": falta["loja"],
                        "endereco_origem": mapa(sobra["loja"]),
                        "endereco_destino": mapa(falta["loja"])
                    })
                    sobra["quantidade"] -= 1
                    break

        pd.concat([pd.DataFrame(faltas), pd.DataFrame(sobras)]).to_csv("estoque_falta_sobra.csv", index=False)
        distribuicao = dados["codigo_loja"].value_counts().to_dict()

        return render_template(
            "analise.html",
            subgrupos=sorted(dados["nome_sub_grupo"].dropna().unique()),
            secoes=sorted(dados["nome_secao"].dropna().unique()),
            filtro_subgrupo=session.get("subgrupo"),
            filtro_secao=session.get("secao"),
            sugestao={"faltando": {"total": len(faltas)}, "reposicoes": sugestoes},
            distribuicao=distribuicao  # <-- adicionado aqui!
        )



@app.route("/loja/<int:codigo_loja>")
def detalhes_loja(codigo_loja):
    global rotulos, grupo_para_cor_pai
    rotulos, grupo_para_cor_pai = carregar_rotulos_e_grupo()

    dados = pd.read_excel("Tabela.xlsx")
    dados["cor_normalizada"] = dados["cor_1"].apply(normalizar_texto)

    colunas_merge = ["cor_normalizada"]
    if "cor_pai" in rotulos.columns:
        colunas_merge.append("cor_pai")

    dados = dados.merge(rotulos[colunas_merge], on="cor_normalizada", how="left")

    if "cor_pai" not in dados.columns:
        dados["cor_pai"] = None

    dados["cor_final"] = dados["cor_pai"].fillna(dados["cor_1"])

    if session.get("subgrupo"):
        dados = dados[dados["nome_sub_grupo"] == session["subgrupo"]]
    if session.get("secao"):
        dados = dados[dados["nome_secao"] == session["secao"]]

    loja_dados = dados[dados["codigo_loja"] == codigo_loja]
    tamanhos_ordenados = sorted(loja_dados["tamanho"].dropna().unique(), key=ordena_tamanho)
    cores_ordenadas = sorted(loja_dados["cor_final"].dropna().unique())

    tabela_pivotada = (
        loja_dados.groupby(["cor_final", "tamanho"]).size().reset_index(name="quantidade")
        .pivot(index="cor_final", columns="tamanho", values="quantidade")
        .reindex(index=cores_ordenadas, columns=tamanhos_ordenados)
        .fillna(0).astype(int)
    )

    todas_combinacoes = dados[["cor_final", "tamanho"]].drop_duplicates()
    faltando, sobrando = [], []
    for _, row in todas_combinacoes.iterrows():
        cor, tam = row["cor_final"], row["tamanho"]
        qtd = loja_dados[(loja_dados["cor_final"] == cor) & (loja_dados["tamanho"] == tam)].shape[0]
        if qtd == 0:
            faltando.append({"cor": cor, "tamanho": tam})
        elif qtd > 1:
            sobrando.append({"cor": cor, "tamanho": tam, "quantidade": qtd})

    return render_template("loja.html",
        codigo_loja=codigo_loja,
        tabela=tabela_pivotada.reset_index().to_dict(orient="records"),
        colunas=tamanhos_ordenados,
        faltando=sorted(faltando, key=lambda x: (x["cor"], ordena_tamanho(x["tamanho"]))),
        sobrando=sorted(sobrando, key=lambda x: (x["cor"], ordena_tamanho(x["tamanho"])))
    )


@app.route("/download_csv")
def download_csv():
    path = "estoque_falta_sobra.csv"
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "Arquivo ainda não foi gerado.", 404


@app.route("/index", methods=["GET", "POST"])
def index():
    resultado = None
    if request.method == "POST":
        cor_digitada = request.form["cor"]
        cor_normalizada = normalizar_texto(cor_digitada)
        embedding = modelo.encode([cor_normalizada])
        grupo = kmeans.predict(embedding)[0]

        cor_pai_encontrada = rotulos.loc[rotulos["cor_normalizada"] == cor_normalizada, "cor_pai"]
        cor_pai = cor_pai_encontrada.values[0] if not cor_pai_encontrada.empty else grupo_para_cor_pai.get(grupo, "Não definido")

        resultado = {
            "cor_digitada": cor_digitada,
            "cor_normalizada": cor_normalizada,
            "grupo": grupo,
            "cor_pai": cor_pai
        }

    return render_template("index.html", resultado=resultado)


@app.route("/rotular", methods=["GET", "POST"])
def rotular():
    global rotulos, kmeans, grupo_para_cor_pai

    cores_nao_rotuladas = rotulos[rotulos["cor_pai"].isnull()]["cor_normalizada"].dropna().unique()

    if request.method == "POST":
        cor = request.form["cor"]
        cor_pai = request.form["cor_pai"]
        rotulos.loc[rotulos["cor_normalizada"] == cor, "cor_pai"] = cor_pai
        rotulos.to_excel(rotulos_path, index=False)

        kmeans, rotulos = reclassificar_kmeans(rotulos)
        _, grupo_para_cor_pai = carregar_rotulos_e_grupo()

        with open("feedback_log.csv", "a", encoding="utf-8") as f:
            f.write(f"{cor},{cor_pai},{datetime.now().isoformat()}\n")

        return redirect("/rotular")

    return render_template("rotular.html", cores=sorted(cores_nao_rotuladas))


@app.route("/rota_entrega", methods=["GET", "POST"])
def rota_entrega():
    lojas_selecionadas = []
    rota_calculada = []
    distancia_total = 0
    tempo_total = 0

    if request.method == "POST":
        lojas_input = request.form.getlist("lojas")
        try:
            lojas_selecionadas = list(map(int, lojas_input))
        except ValueError:
            return "Códigos de loja inválidos.", 400

        if len(lojas_selecionadas) < 1:
            return "Selecione pelo menos uma loja para calcular a rota.", 400

        origem = 99
        rota = [origem]
        restantes = [l for l in lojas_selecionadas if l != origem]

        def distancia_segura(o, d):
            dist, _ = calcular_rota(o, d)
            return dist if dist is not None else float("inf")

        while restantes:
            ultima = rota[-1]
            proxima = min(restantes, key=lambda l: distancia_segura(ultima, l))
            rota.append(proxima)
            restantes.remove(proxima)

        for i in range(len(rota) - 1):
            origem = rota[i]
            destino = rota[i + 1]
            distancia, tempo = calcular_rota(origem, destino)
            if distancia is not None:
                rota_calculada.append({
                    "origem": origem,
                    "destino": destino,
                    "distancia_km": distancia,
                    "tempo_min": tempo,
                    "endereco_origem": enderecos_lojas.get(origem, "Desconhecido"),
                    "endereco_destino": enderecos_lojas.get(destino, "Desconhecido")
                })
                distancia_total += distancia
                tempo_total += tempo

    return render_template("rota_entrega.html",
        lojas=coordenadas_lojas,
        enderecos_lojas=enderecos_lojas,
        lojas_selecionadas=lojas_selecionadas,
        rota=rota_calculada,
        distancia_total=round(distancia_total, 2),
        tempo_total=tempo_total
    )


@app.route("/admin/treinar-modelo", methods=["GET"])
def treinar_modelo_interface():
    try:
        from modelo_treino import treinar_modelo_transferencias
        treinar_modelo_transferencias()
        logging.info("Modelo treinado via interface web.")
        return "Modelo treinado com sucesso!"
    except Exception as e:
        logging.error(f"Erro ao treinar modelo: {e}")
        return f"Erro ao treinar modelo: {str(e)}"


@app.route("/reclassificar", methods=["POST"])
def reclassificar():
    global kmeans, rotulos, grupo_para_cor_pai
    kmeans, rotulos, grupo_para_cor_pai = atualizar_modelos_e_rotulos(rotulos_path)
    rotulos.to_excel(rotulos_path, index=False)
    return redirect("/rotular")


@app.route("/limpar_cache")
def limpar_cache():
    carregar_rotulos_e_grupo.cache_clear()
    return redirect(request.referrer or "/")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
