from flask import Flask, render_template, request
import locale

app = Flask(__name__)

# -----------------------------------------------------------
# Configurações de locale (para formatação PT-BR, se desejado)
# -----------------------------------------------------------
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

# -----------------------------------------------------------
# Funções de Conversão e Formatação
# -----------------------------------------------------------
def convert_brazilian_to_float(value_str):
    """
    Converte uma string no formato brasileiro para float.
    Ex.: "1.234,56" -> 1234.56
    """
    if not value_str or value_str.strip() == "":
        return 0.0
    value_str = value_str.strip().replace('.', '').replace(',', '.')
    return float(value_str)

def format_currency(value):
    """
    Formata número no padrão monetário brasileiro (R$ 1.234,56).
    """
    try:
        return locale.currency(value, grouping=True)
    except:
        return f"R$ {value:,.2f}"

# -----------------------------------------------------------
# Dicionários e Constantes para o Cálculo do VVT
# -----------------------------------------------------------

# Coeficientes de Situação do Terreno (Cs)
CS_VALUES = {
    "meio_quadra_uma_frente": 1.00,
    "mais_de_uma_frente": 1.10,
    "encravado": 0.50,
    "situado_em_vila": 0.80,
    "abrange_propria_quadra": 1.20
}

# Fatores de Topografia (Ft)
FT_VALUES = {
    "plano": 1.00,
    "aclive": 0.95,
    "declive": 0.90,
    "irregular": 0.80
}

# Fatores de Pedologia (Fe)
FE_VALUES = {
    "seco_normal": 1.00,
    "inundavel": 0.70,
    "alagado": 0.50
}

# Parâmetros da zona homogênea
Pmin = 25   # Profundidade mínima
Pmax = 50   # Profundidade máxima
Fr   = 10   # Frente de Referência

# -----------------------------------------------------------
# Funções para Cálculo do VVT
# -----------------------------------------------------------
def calcular_si(area_construida_unidade, area_total_construida, area_terreno):
    """
    Fração Ideal da Área (Si) = (Su/St) * Área do Terreno.
    Se St = 0, assumimos Si = área_terreno.
    """
    if area_total_construida > 0:
        return (area_construida_unidade / area_total_construida) * area_terreno
    else:
        return area_terreno

def calcular_cf(testada):
    """
    Cf = (Fp / Fr)^(1/4).
    Fp depende da testada:
      - < 5 => Fp=5
      - 5 <= testada <= 20 => Fp=testada
      - >20 => Fp=20
    Fr=10
    """
    if testada < 5:
        Fp = 5
    elif testada > 20:
        Fp = 20
    else:
        Fp = testada
    return (Fp / Fr) ** 0.25

def calcular_cp(pe, pmin=25, pmax=50):
    """
    Cp (Coef. de Profundidade):
      1) Se pmin <= pe <= pmax => Cp=1.0
      2) Se pe <= pmin/2 ou pe >= 2*pmax => Cp=0.71
      3) Se pmin/2 < pe < pmin => Cp = sqrt(pe/pmin)
      4) Se pmax < pe < 2*pmax => Cp = sqrt(pmax/pe)
    """
    if pmin <= pe <= pmax:
        return 1.0
    elif pe <= (pmin / 2) or pe >= (2 * pmax):
        return 0.71
    elif (pmin / 2) < pe < pmin:
        return (pe / pmin) ** 0.5
    elif pmax < pe < (2 * pmax):
        return (pmax / pe) ** 0.5
    else:
        return 1.0

def calcular_fpond(ft, fe):
    """
    Fator de Ponderação = (Ft + Fe - 1)
    """
    return ft + fe - 1

def calcular_vvt(
    area_construida_unidade,
    area_total_construida,
    area_terreno,
    valor_m2_terreno,
    testada,
    situacao_terreno,
    topografia_terreno,
    pedologia_terreno
):
    """
    VVT = Si * Vm² * Cf * Cp * Cs * Fpond
    """
    # Fração Ideal
    si = calcular_si(area_construida_unidade, area_total_construida, area_terreno)

    # Cf
    cf = calcular_cf(testada)

    # Profundidade efetiva
    pe = area_terreno / testada if testada != 0 else 0
    cp = calcular_cp(pe, pmin=Pmin, pmax=Pmax)

    # Cs
    cs = CS_VALUES.get(situacao_terreno, 1.0)

    # Ft, Fe
    ft = FT_VALUES.get(topografia_terreno, 1.0)
    fe = FE_VALUES.get(pedologia_terreno, 1.0)

    # Fpond
    fpond = calcular_fpond(ft, fe)

    # VVT
    vvt = si * valor_m2_terreno * cf * cp * cs * fpond

    return vvt

# -----------------------------------------------------------
# Dicionários e Funções para Cálculo do VVE
# -----------------------------------------------------------

# Valor unitário por tipo de edificação
TIPOS_EDIFICACAO = {
    "casa": 120.00,
    "apartamento": 205.00,
    "loja": 215.00,
    "sala_comercial": 200.00,
    "barraco_favela": 0.00,
    "galpao": 80.00,
    "industria": 165.00,
    "telheiro": 40.00,
    "posto_gasolina": 100.00,
    "arquitetura_especial": 180.00
}

# Fator de Situação da Edificação (Fs)
FS_VALUES = {
    "isolada": 1.00,
    "conjugada": 0.90,
    "geminada": 0.80
}

# Fator de Posição do Terreno (Fp) - Exemplo
FP_VALUES = {
    "frente": 1.00,
    "fundos": 0.95,
    "superposta_frente": 0.90,
    "superposta_fundo": 0.85,
    "galeria": 0.80
}

# Fator de Alinhamento (Fa)
FA_VALUES = {
    "alinhada": 0.90,
    "recuada": 1.00
}

# Fator de Conservação (Fc)
FC_VALUES = {
    "bom": 1.00,
    "regular": 0.80,
    "ruim": 0.60
}

# Coeficientes de Estrutura (Cest)
CEST_VALUES = {
    "alvenaria": 1.00,
    "concreto": 1.20,
    "madeira": 0.60,
    "metalica": 1.10,
    "taipa": 0.50
}

# Coeficientes de Cobertura (Ccob)
CCOB_VALUES = {
    "telha_fibro_cimento": 1.00,
    "telha_barro": 1.20,
    "laje": 1.30,
    "palha": 0.50,
    "aluminio": 1.30,
    "plastico_sintetico": 1.50,
    "madeira_cavaco": 1.00,
    "especial": 2.00
}

# Coeficientes de Piso (Cpis)
CPIS_VALUES = {
    "precario_cimentado": 1.00,
    "ardosia_taco_carpete": 1.10,
    "ceramica_carpete_especial": 1.20,
    "tabua_corrida_borracha": 1.20,
    "marmore_granito": 1.50
}

# Coeficientes de Revestimento Externo (Crex)
CREX_VALUES = {
    "precario_ausente": 1.00,
    "pintura_oleo_madeira": 1.05,
    "tijolo_vista": 1.20,
    "ceramica_pedra_concreto": 1.50,
    "marmore_granito": 2.00
}

# Coeficientes de Revestimento Interno (Crin)
CRIN_VALUES = {
    "ausente_precario": 1.00,
    "pintura_papel_oleo": 1.05,
    "ceramica_pedra_concreto": 1.20,
    "espelho_marmore_granito": 1.50
}

# Coeficientes de Forro (Cfor)
CFOR_VALUES = {
    "ausente_precario": 1.00,
    "plastico_gesso_formica": 1.10,
    "metalica_madeira_aluminio": 1.15,
    "laje": 1.20
}

def calcular_vm2(tipo_edificacao):
    """
    Vm² = (valor_unitario / 35.08) * 103.67
    """
    valor_unitario = TIPOS_EDIFICACAO.get(tipo_edificacao, 0.0)
    return (valor_unitario / 35.08) * 103.67

def calcular_fpad(estrutura, cobertura, piso, rev_externo, rev_interno, forro):
    """
    Fpad = (Cest + Ccob + Cpis + Crex + Crin + Cfor) - 5
    """
    cest = CEST_VALUES.get(estrutura, 1.0)
    ccob = CCOB_VALUES.get(cobertura, 1.0)
    cpis = CPIS_VALUES.get(piso, 1.0)
    crex = CREX_VALUES.get(rev_externo, 1.0)
    crin = CRIN_VALUES.get(rev_interno, 1.0)
    cfor = CFOR_VALUES.get(forro, 1.0)
    soma = cest + ccob + cpis + crex + crin + cfor
    return soma - 5.0

def calcular_vve(
    su,
    tipo_edificacao,
    fs_key,
    fp_key,
    fa_key,
    estrutura_key,
    cobertura_key,
    piso_key,
    rev_externo_key,
    rev_interno_key,
    forro_key,
    fc_key
):
    """
    VVE = Su * Vm² * Fs * Fp * Fa * Fpad * Fc
    """
    vm2 = calcular_vm2(tipo_edificacao)
    fs = FS_VALUES.get(fs_key, 1.0)
    fp = FP_VALUES.get(fp_key, 1.0)
    fa = FA_VALUES.get(fa_key, 1.0)
    fc = FC_VALUES.get(fc_key, 1.0)

    fpad = calcular_fpad(estrutura_key, cobertura_key, piso_key, rev_externo_key, rev_interno_key, forro_key)

    vve = su * vm2 * fs * fp * fa * fpad * fc
    return vve

# -----------------------------------------------------------
# Rota Principal
# -----------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# -----------------------------------------------------------
# Rota de Cálculo
# -----------------------------------------------------------
@app.route('/calcular', methods=['POST'])
def calcular():
    try:
        form_data = request.form

        # Lista de dropdowns obrigatórios
        dropdowns_obrigatorios = [
            'imovel_edificado',
            'topografia_terreno',
            'pedologia_terreno',
            'situacao_terreno'
        ]

        # Dropdowns condicionais (apenas se imovel_edificado for 'sim' ou 'nao')
        dropdowns_edificacao = [
            'tipo_construcao',
            'situacao_edificacao',
            'posicao_terreno',
            'alinhamento',
            'estrutura',
            'cobertura',
            'piso',
            'revestimento_externo',
            'revestimento_interno',
            'forro',
            'conservacao'
        ]
        dropdowns_nao_edificado = ['muro', 'calcada']

        # Verificar campos obrigatórios
        campos_vazios = []
        for campo in dropdowns_obrigatorios:
            valor = form_data.get(campo, '')
            if not valor:
                campos_vazios.append(campo)

        # Verificar imovel_edificado antes de prosseguir
        imovel_edificado = form_data.get('imovel_edificado', '')
        if not imovel_edificado:
            return render_template('index.html', erro="Por favor, selecione se o imóvel é edificado.")

        # Verificar campos condicionais
        if imovel_edificado == 'sim':
            for campo in dropdowns_edificacao:
                valor = form_data.get(campo, '')
                if not valor:
                    campos_vazios.append(campo)
        elif imovel_edificado == 'nao':
            for campo in dropdowns_nao_edificado:
                valor = form_data.get(campo, '')
                if not valor:
                    campos_vazios.append(campo)

        if campos_vazios:
            return render_template('index.html', erro="Por favor, selecione uma opção válida para todos os campos obrigatórios.")

        # Coleta dos dados de entrada (agora sem valores padrão que assumam escolhas)
        imovel_edificado = imovel_edificado.lower()
        muro = form_data.get('muro', '').lower()
        calcada = form_data.get('calcada', '').lower()

        area_terreno = convert_brazilian_to_float(form_data.get('area_terreno', '0'))
        testada = convert_brazilian_to_float(form_data.get('testada', '0'))
        valor_m2_terreno = convert_brazilian_to_float(form_data.get('valor_metro_quadrado', '0'))
        topografia_terreno = form_data.get('topografia_terreno', '')
        pedologia_terreno = form_data.get('pedologia_terreno', '')
        situacao_terreno = form_data.get('situacao_terreno', '')

        # Verifica se os valores estão nos dicionários (opcional, para garantir consistência)
        if topografia_terreno not in FT_VALUES or pedologia_terreno not in FE_VALUES or situacao_terreno not in CS_VALUES:
            return render_template('index.html', erro="Um ou mais valores selecionados são inválidos.")

        # Cálculo do VVT
        if imovel_edificado == 'sim':
            area_construida_unidade = convert_brazilian_to_float(form_data.get('area_construida_unidade', '0'))
            area_total_construida = convert_brazilian_to_float(form_data.get('area_total_construida', '0'))
        else:
            area_construida_unidade = 0.0
            area_total_construida = 0.0

        vvt = calcular_vvt(
            area_construida_unidade,
            area_total_construida,
            area_terreno,
            valor_m2_terreno,
            testada,
            situacao_terreno,
            topografia_terreno,
            pedologia_terreno
        )

        # Cálculo do VVE (se edificado)
        vve = 0.0
        if imovel_edificado == 'sim':
            su = area_construida_unidade
            tipo_edificacao = form_data.get('tipo_construcao', '')
            fs_key = form_data.get('situacao_edificacao', '')
            fp_key = form_data.get('posicao_terreno', '')
            fa_key = form_data.get('alinhamento', '')
            estrutura_key = form_data.get('estrutura', '')
            cobertura_key = form_data.get('cobertura', '')
            piso_key = form_data.get('piso', '')
            rev_externo_key = form_data.get('revestimento_externo', '')
            rev_interno_key = form_data.get('revestimento_interno', '')
            forro_key = form_data.get('forro', '')
            fc_key = form_data.get('conservacao', '')

            # Verifica se os valores estão nos dicionários
            if (tipo_edificacao not in TIPOS_EDIFICACAO or fs_key not in FS_VALUES or fp_key not in FP_VALUES or
                fa_key not in FA_VALUES or estrutura_key not in CEST_VALUES or cobertura_key not in CCOB_VALUES or
                piso_key not in CPIS_VALUES or rev_externo_key not in CREX_VALUES or rev_interno_key not in CRIN_VALUES or
                forro_key not in CFOR_VALUES or fc_key not in FC_VALUES):
                return render_template('index.html', erro="Um ou mais valores selecionados são inválidos.")

            vve = calcular_vve(
                su,
                tipo_edificacao,
                fs_key,
                fp_key,
                fa_key,
                estrutura_key,
                cobertura_key,
                piso_key,
                rev_externo_key,
                rev_interno_key,
                forro_key,
                fc_key
            )

        # Restante do código (VVI, alíquota, IPTU) permanece igual
        vvi = vvt + vve

        if imovel_edificado == 'sim':
            aliquota = 0.005  # 0,5%
        else:
            muro_bool = (muro == 'sim')
            calcada_bool = (calcada == 'sim')
            if muro_bool and calcada_bool:
                aliquota = 0.0125  # 1,25%
            elif muro_bool or calcada_bool:
                aliquota = 0.025   # 2,50%
            else:
                aliquota = 0.085   # 8,5%

        iptu = vvi * aliquota

        resultado = {
            "imovel_edificado": imovel_edificado,
            "muro": muro,
            "calcada": calcada,
            "VVT": format_currency(vvt),
            "VVE": format_currency(vve),
            "VVI": format_currency(vvi),
            "aliquota": f"{aliquota * 100:.2f}%",
            "IPTU": format_currency(iptu)
        }

        return render_template('index.html', resultado=resultado)

    except Exception as e:
        print("Erro no cálculo:", e)
        return render_template('index.html', erro="Ocorreu um erro ao processar os dados. Verifique as informações e tente novamente.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
else:
    # Para o Vercel
    # O aplicativo será servido pelo Vercel, não precisamos chamar app.run()
    # Apenas garantimos que 'app' está disponível para importação
    pass
