import bpy
import math
from mathutils import Vector, Euler, Matrix
from mathutils.geometry import interpolate_bezier

# AP2 - "Ibmec Stars: uma ideia vira estrela". Blender 4.5 LTS.
# Abra AC5/AC05_MarceuFilho.blend e execute este script (Scripting > Run Script).
# Ele salva uma copia em AP2/AP2_MarceuFilho.blend; a AC05 nao e alterada.

cena = bpy.context.scene
obj = bpy.data.objects
cena.frame_start, cena.frame_end = 1, 360          # 15 s a 24 fps
cena.render.fps = 24


# ---------------------------------------------------------------- ferramentas
def chave(dono, caminho, frame, valor, indice=-1, interp=None, easing=None):
    """Grava um keyframe e, se pedido, a interpolacao do trecho que comeca nele."""
    if indice >= 0:
        getattr(dono, caminho)[indice] = valor
    else:
        setattr(dono, caminho, valor)
    dono.keyframe_insert(caminho, index=indice, frame=frame)
    if interp:
        for curva in dono.id_data.animation_data.action.fcurves:
            if curva.data_path.endswith(caminho) and indice in (-1, curva.array_index):
                for ponto in curva.keyframe_points:
                    if ponto.co.x == frame:
                        ponto.interpolation = interp
                        ponto.easing = easing or 'AUTO'


def key(objeto, frame, loc=None, rot=None, scale=None, interp=None, easing=None):
    """Keyframe de posicao, rotacao (em graus) e/ou escala."""
    if loc is not None:
        chave(objeto, "location", frame, loc, interp=interp, easing=easing)
    if rot is not None:
        chave(objeto, "rotation_euler", frame, [math.radians(g) for g in rot], interp=interp, easing=easing)
    if scale is not None:
        chave(objeto, "scale", frame, scale, interp=interp, easing=easing)


def salto(objeto, f0, f1, p0, p1, altura):
    """Arco de salto: X e Y lineares; Z sobe desacelerando e desce acelerando."""
    meio = (f0 + f1) // 2
    for i in (0, 1):
        chave(objeto, "location", f0, p0[i], i, 'LINEAR')
        chave(objeto, "location", f1, p1[i], i, 'LINEAR')
    chave(objeto, "location", f0, p0[2], 2, 'QUAD', 'EASE_OUT')
    chave(objeto, "location", meio, max(p0[2], p1[2]) + altura, 2, 'QUAD', 'EASE_IN')
    chave(objeto, "location", f1, p1[2], 2)


def colecao(nome):
    col = bpy.data.collections.get(nome) or bpy.data.collections.new(nome)
    if col.name not in cena.collection.children:
        cena.collection.children.link(col)
    return col


def vazio(nome, tamanho=0.1):
    objeto = obj.new(nome, None)
    objeto.empty_display_size = tamanho
    colecao("AP2_controles").objects.link(objeto)
    return objeto


def filho(objeto, pai, modo='XYZ'):
    """Liga ao pai sem mover o objeto e passa a rotacao para Euler (curvas legiveis)."""
    bpy.context.view_layer.update()
    mundo = objeto.matrix_world.copy()
    objeto.parent = pai
    objeto.matrix_parent_inverse = Matrix.Identity(4)
    objeto.matrix_world = mundo
    angulos = objeto.matrix_basis.to_euler(modo)
    objeto.rotation_mode = modo
    objeto.rotation_euler = angulos


# ------------------------------------------------------------------- 1. palco
# O "Palco" e um vazio alinhado com a palavra. Dentro dele as coordenadas sao simples:
# X = ao longo da palavra, Y = profundidade (negativo = perto da camera), Z = altura.
marca = obj["Marca_Ibmec"]
direcao = marca.matrix_world.to_3x3() @ Vector((1, 0, 0))
palco = vazio("Palco", 0.3)
palco.rotation_euler.z = math.atan2(direcao.y, direcao.x)
bpy.context.view_layer.update()
para_palco = palco.matrix_world.inverted()

estrela, pingo, borracha = obj["Obj_Estrela"], obj["Marca_Pingo"], obj["Borracha_Corpo"]
deco1, deco2 = obj["Estrela_Decorativa_01"], obj["Estrela_Decorativa_02"]
camera = obj["CAM_Principal"]
for objeto in (pingo, borracha, camera):
    filho(objeto, palco)
for objeto in (estrela, deco1, deco2):
    filho(objeto, palco, 'ZYX')        # ordem ZYX: o eixo Z gira a estrela como um cata-vento

# Controle do lapis: vazio na ponta da borracha, com o eixo Z ao longo do lapis.
corpo = obj["Lapis_Corpo"]
eixo = (corpo.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
alcance = [(o.matrix_world @ Vector(canto) - corpo.matrix_world.translation).dot(eixo)
           for o in [corpo] + list(corpo.children) for canto in o.bound_box]
COMPRIMENTO = max(alcance) - min(alcance)
base = para_palco @ (corpo.matrix_world.translation + eixo * min(alcance))
eixo_palco = para_palco.to_3x3() @ eixo
GIRO = math.degrees(math.atan2(eixo_palco.x, -eixo_palco.y))   # rotacao Z do lapis deitado

lapis = vazio("CTRL_Lapis", 0.08)
lapis.parent = palco
lapis.location = base
lapis.rotation_euler = (math.radians(90), 0, math.radians(GIRO))
filho(corpo, lapis)
ESPESSURA = (1.4, 1.4, 1)                        # lapis mais "gordinho", estilo cartum
lapis.scale = ESPESSURA
RAIO = 0.028

# Alvo da camera (Track To) e foco.
alvo = vazio("CAM_Alvo", 0.1)
alvo.parent = palco
rastrear = camera.constraints.new('TRACK_TO')
rastrear.target = alvo
rastrear.track_axis, rastrear.up_axis = 'TRACK_NEGATIVE_Z', 'UP_Y'
camera.data.dof.use_dof = True
camera.data.dof.focus_object = alvo
camera.data.dof.aperture_fstop = 2.8

# ------------------------------------------------------- 2. letreiro "stars"
# A curva original tem tres tracos. Cada um vira um objeto para ser escrito em ordem.
ouro = bpy.data.materials["MAT_Ouro_PBR"]
brilho = ouro.copy()
brilho.name = "MAT_Stars_Ouro"
shader = brilho.node_tree.nodes["Principled BSDF"]
shader.inputs["Base Color"].default_value = (0.913, 0.413, 0.0, 1)     # amarelo Ibmec #F5AC00
shader.inputs["Metallic"].default_value = 0.0
shader.inputs["Emission Color"].default_value = (1.0, 0.45, 0.03, 1)
emissao = shader.inputs["Emission Strength"]

original = obj["Texto_Stars"]
tracos = []
for i, nome in enumerate(["Texto_Stars_1_st", "Texto_Stars_2_traco", "Texto_Stars_3_ars"]):
    traco = original.copy()
    traco.data = original.data.copy()
    traco.name = traco.data.name = nome
    for j in reversed(range(3)):
        if j != i:
            traco.data.splines.remove(traco.data.splines[j])
    traco.data.bevel_depth = 0.014
    traco.data.use_fill_caps = True
    traco.data.bevel_factor_mapping_end = 'SPLINE'      # fator = fracao do comprimento
    traco.data.materials.clear()
    traco.data.materials.append(brilho)
    original.users_collection[0].objects.link(traco)
    tracos.append(traco)
bpy.data.objects.remove(original)
bpy.context.view_layer.update()


def pontos_do_traco(traco, passos):
    """Pontos igualmente espacados ao longo da curva, em coordenadas do Palco."""
    linha = []
    bez = traco.data.splines[0].bezier_points
    for a, b in zip(bez[:-1], bez[1:]):
        linha += interpolate_bezier(a.co, a.handle_right, b.handle_left, b.co, 16)[:-1]
    linha.append(bez[-1].co)
    linha = [para_palco @ (traco.matrix_world @ p) for p in linha]
    dist = [0.0]
    for a, b in zip(linha[:-1], linha[1:]):
        dist.append(dist[-1] + (b - a).length)
    saida, k = [], 0
    for n in range(passos + 1):
        d = dist[-1] * n / passos
        while k < len(dist) - 2 and dist[k + 1] < d:
            k += 1
        t = (d - dist[k]) / max(dist[k + 1] - dist[k], 1e-9)
        saida.append(linha[k].lerp(linha[k + 1], t))
    return saida


# ------------------------------------------------ 2b. do desenho para a cor
# No inicio so a estrela tem cor. O resto e um "desenho a lapis": branco de papel com
# hachuras de grafite. Cada material ganha uma mistura entre o desenho e o material PBR
# da AC05. Quem decide a mistura e a posicao de um vazio: tudo que esta a esquerda dele
# (X local negativo) fica colorido. Na fronteira ha uma faixa dourada que brilha.
def magia(nome_material, frente):
    mat = bpy.data.materials[nome_material]
    nos, ligar = mat.node_tree.nodes, mat.node_tree.links.new
    pbr = nos["Principled BSDF"]
    saida = nos["Material Output"]

    # Desenho: papel branco + hachuras diagonais + borda escura (contorno de grafite).
    coord = nos.new("ShaderNodeTexCoord")
    onda = nos.new("ShaderNodeTexWave")
    onda.bands_direction = 'DIAGONAL'
    onda.inputs["Scale"].default_value = 26
    onda.inputs["Distortion"].default_value = 1.5
    ligar(coord.outputs["Object"], onda.inputs["Vector"])
    risco = nos.new("ShaderNodeMapRange")                 # so o topo da onda vira risco
    risco.inputs["From Min"].default_value = 0.62
    risco.inputs["From Max"].default_value = 0.80
    risco.inputs["To Max"].default_value = 0.60
    ligar(onda.outputs["Fac"], risco.inputs["Value"])
    borda = nos.new("ShaderNodeLayerWeight")
    borda.inputs["Blend"].default_value = 0.35
    contorno = nos.new("ShaderNodeMapRange")
    contorno.inputs["From Min"].default_value = 0.30
    contorno.inputs["From Max"].default_value = 0.75
    contorno.inputs["To Max"].default_value = 0.95
    ligar(borda.outputs["Facing"], contorno.inputs["Value"])
    # Linha nas arestas vivas: o no Bevel arredonda a normal so perto das arestas;
    # onde ela difere da normal real, desenhamos um traco escuro (funciona no Cycles).
    chanfro = nos.new("ShaderNodeBevel")
    chanfro.inputs["Radius"].default_value = 0.012
    geometria = nos.new("ShaderNodeNewGeometry")
    diferenca = nos.new("ShaderNodeVectorMath")
    diferenca.operation = 'DOT_PRODUCT'
    ligar(chanfro.outputs["Normal"], diferenca.inputs[0])
    ligar(geometria.outputs["Normal"], diferenca.inputs[1])
    aresta = nos.new("ShaderNodeMapRange")
    aresta.inputs["From Min"].default_value = 0.995
    aresta.inputs["From Max"].default_value = 0.93
    aresta.inputs["To Max"].default_value = 1.0
    ligar(diferenca.outputs["Value"], aresta.inputs["Value"])
    tracos = nos.new("ShaderNodeMath")
    tracos.operation = 'MAXIMUM'
    ligar(risco.outputs["Result"], tracos.inputs[0])
    ligar(contorno.outputs["Result"], tracos.inputs[1])
    grafite = nos.new("ShaderNodeMath")
    grafite.operation = 'MAXIMUM'
    ligar(tracos.outputs["Value"], grafite.inputs[0])
    ligar(aresta.outputs["Result"], grafite.inputs[1])
    for i, no in enumerate([chanfro, geometria, diferenca, aresta, tracos]):
        no.location = (-1700 + 230 * i, -1150)
    papel = nos.new("ShaderNodeMixRGB")
    papel.inputs["Color1"].default_value = (0.93, 0.91, 0.86, 1)     # papel
    papel.inputs["Color2"].default_value = (0.16, 0.17, 0.20, 1)     # grafite
    ligar(grafite.outputs["Value"], papel.inputs["Fac"])
    desenho = nos.new("ShaderNodeBsdfPrincipled")
    desenho.name = desenho.label = "Desenho"
    desenho.inputs["Roughness"].default_value = 1.0
    desenho.inputs["Specular IOR Level"].default_value = 0.0
    ligar(papel.outputs["Color"], desenho.inputs["Base Color"])

    # Fronteira: X local do vazio. Negativo = ja colorido.
    frente_coord = nos.new("ShaderNodeTexCoord")
    frente_coord.object = frente
    eixos = nos.new("ShaderNodeSeparateXYZ")
    ligar(frente_coord.outputs["Object"], eixos.inputs["Vector"])
    cor = nos.new("ShaderNodeMapRange")                   # 1 = colorido, 0 = desenho
    cor.inputs["From Min"].default_value = -0.02
    cor.inputs["From Max"].default_value = 0.02
    cor.inputs["To Min"].default_value = 1.0
    cor.inputs["To Max"].default_value = 0.0
    ligar(eixos.outputs["X"], cor.inputs["Value"])
    mistura = nos.new("ShaderNodeMixShader")
    ligar(cor.outputs["Result"], mistura.inputs["Fac"])
    ligar(desenho.outputs["BSDF"], mistura.inputs[1])
    ligar(pbr.outputs["BSDF"], mistura.inputs[2])

    # Faixa dourada na fronteira (emissao), que o Glare do compositor faz brilhar.
    distancia = nos.new("ShaderNodeMath")
    distancia.operation = 'ABSOLUTE'
    ligar(eixos.outputs["X"], distancia.inputs[0])
    faixa = nos.new("ShaderNodeMapRange")
    faixa.inputs["From Min"].default_value = 0.0
    faixa.inputs["From Max"].default_value = 0.035
    faixa.inputs["To Min"].default_value = 14.0
    faixa.inputs["To Max"].default_value = 0.0
    ligar(distancia.outputs["Value"], faixa.inputs["Value"])
    luz_magica = nos.new("ShaderNodeEmission")
    luz_magica.inputs["Color"].default_value = (1.0, 0.55, 0.08, 1)
    ligar(faixa.outputs["Result"], luz_magica.inputs["Strength"])
    soma = nos.new("ShaderNodeAddShader")
    ligar(mistura.outputs["Shader"], soma.inputs[0])
    ligar(luz_magica.outputs["Emission"], soma.inputs[1])
    ligar(soma.outputs["Shader"], saida.inputs["Surface"])

    # Nos organizados no Shader Editor.
    for i, no in enumerate([coord, onda, risco, borda, contorno, grafite, papel, desenho]):
        no.location = (-1700 + 230 * i, -700 - (140 if no in (borda, contorno) else 0))
    for i, no in enumerate([frente_coord, eixos, cor, distancia, faixa, luz_magica]):
        no.location = (-700 + 200 * i, 1100 if no in (frente_coord, eixos, cor) else 900)
    mistura.location, soma.location, saida.location = (560, 300), (780, 300), (1000, 300)


frente = vazio("Magia_Frente", 0.15)                 # varre a cena junto com o lapis
frente.parent = palco
frente.location = (-3.0, 0, 0)
for nome in ("MAT_Ibmec_PBR", "MAT_Ibmec_Pingo_PBR", "MAT_Borracha_PBR", "MAT_Capa_Papel"):
    magia(nome, frente)

frente_lapis = vazio("Magia_Lapis", 0.05)            # corre ao longo do proprio lapis
frente_lapis.parent = lapis
frente_lapis.rotation_euler.y = math.radians(-90)    # o X do vazio aponta para a ponta
frente_lapis.location = (0, 0, -0.1)
for nome in ("MAT_Madeira_PBR", "MAT_Metal_Escovado", "MAT_Grafite", "MAT_Borracha_Rosa"):
    magia(nome, frente_lapis)

# Faiscas: copias pequenas da estrela decorativa, com emissao.
faisca_mat = ouro.copy()
faisca_mat.name = "MAT_Faisca"
faisca_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.6, 0.1, 1)
faisca_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.5

# -------------------------------------------------------------- 3. iluminacao
# Tres pontos: principal e preenchimento vem da AC04; aqui entra a luz de contorno.
def luz(nome, tipo, posicao, potencia, tamanho, cor, pai=palco):
    dados = bpy.data.lights.new(nome, tipo)
    dados.energy, dados.color = potencia, cor
    if tipo == 'AREA':
        dados.shape, dados.size = 'DISK', tamanho
    else:
        dados.shadow_soft_size = tamanho
    objeto = obj.new(nome, dados)
    objeto.parent = pai
    objeto.location = posicao
    colecao("luzes").objects.link(objeto)
    return objeto


contorno = luz("LUZ_Contorno", 'AREA', (2.2, 2.6, 2.4), 70, 1.0, (1.0, 0.95, 0.9))
contorno.rotation_euler = (Vector((0, 0, 0.3)) - contorno.location).to_track_quat('-Z', 'Y').to_euler()
obj["LUZ_Principal"].data.energy = 200
obj["LUZ_Principal"].data.color = (1.0, 0.90, 0.76)
obj["LUZ_Preenchimento"].data.energy = 22
obj["LUZ_Preenchimento"].data.color = (0.75, 0.86, 1.0)
# Luz pequena presa a estrela: ela ilumina as letras quando chega.
luz_estrela = luz("LUZ_Estrela", 'POINT', (0, 0, 0.22), 0.12, 0.03, (1.0, 0.7, 0.3), pai=estrela)
# A estrela tem um material proprio, com emissao animada: ela acende quando o lapis passa.
ouro_estrela = ouro.copy()
ouro_estrela.name = "MAT_Estrela_Ouro"
estrela.data.materials.clear()
estrela.data.materials.append(ouro_estrela)
brilho_estrela = ouro_estrela.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
ouro_estrela.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.6, 0.12, 1)

# Cenario: folha de caderno. Papel quente com grao fino e uma grade azul bem clara.
arvore_fundo = bpy.data.materials["MAT_Fundo"].node_tree
nos, ligar = arvore_fundo.nodes, arvore_fundo.links.new
fundo = nos["Principled BSDF"]
fundo.inputs["Roughness"].default_value = 0.75
grade_coord = nos.new("ShaderNodeTexCoord")
grade_coord.object = palco                           # grade alinhada com a palavra
escala = nos.new("ShaderNodeMapping")
escala.inputs["Location"].default_value = (0.5, 0.5, 0.5)
escala.inputs["Scale"].default_value = (4, 4, 4)     # uma linha a cada 25 cm
ligar(grade_coord.outputs["Object"], escala.inputs["Vector"])
fracao = nos.new("ShaderNodeVectorMath")
fracao.operation = 'FRACTION'
ligar(escala.outputs["Vector"], fracao.inputs[0])
eixos_grade = nos.new("ShaderNodeSeparateXYZ")
ligar(fracao.outputs["Vector"], eixos_grade.inputs["Vector"])
linhas = []
for eixo_grade in ("X", "Y", "Z"):
    linha = nos.new("ShaderNodeMath")
    linha.operation = 'LESS_THAN'
    linha.inputs[1].default_value = 0.035
    ligar(eixos_grade.outputs[eixo_grade], linha.inputs[0])
    linhas.append(linha)
junta = nos.new("ShaderNodeMath")
junta.operation = 'MAXIMUM'
ligar(linhas[0].outputs["Value"], junta.inputs[0])
ligar(linhas[1].outputs["Value"], junta.inputs[1])
junta2 = nos.new("ShaderNodeMath")
junta2.operation = 'MAXIMUM'
ligar(junta.outputs["Value"], junta2.inputs[0])
ligar(linhas[2].outputs["Value"], junta2.inputs[1])
forca = nos.new("ShaderNodeMath")
forca.operation = 'MULTIPLY'
forca.inputs[1].default_value = 0.30                 # grade discreta
ligar(junta2.outputs["Value"], forca.inputs[0])
folha = nos.new("ShaderNodeMixRGB")
folha.inputs["Color1"].default_value = (0.90, 0.87, 0.80, 1)     # papel
folha.inputs["Color2"].default_value = (0.45, 0.62, 0.85, 1)     # azul da grade
ligar(forca.outputs["Value"], folha.inputs["Fac"])
# Tinta azul: cresce em circulo a partir do vazio Tinta_Centro (a escala dele e o raio).
tinta_centro = vazio("Tinta_Centro", 0.3)
tinta_centro.parent = palco
tinta_centro.location = (0.3, 3.0, 0.3)              # atras da palavra, onde o chao vira parede
tinta_centro.scale = (0.001, 0.001, 0.001)
tinta_coord = nos.new("ShaderNodeTexCoord")
tinta_coord.object = tinta_centro
raio = nos.new("ShaderNodeVectorMath")
raio.operation = 'LENGTH'
ligar(tinta_coord.outputs["Object"], raio.inputs[0])
borrao = nos.new("ShaderNodeTexNoise")               # borda irregular, como respingo
borrao.inputs["Scale"].default_value = 2.2
borrao.inputs["Detail"].default_value = 6
ligar(grade_coord.outputs["Object"], borrao.inputs["Vector"])
irregular = nos.new("ShaderNodeMath")
irregular.operation = 'MULTIPLY_ADD'                 # raio + ruido * 0.5
irregular.inputs[1].default_value = 0.5
ligar(borrao.outputs["Fac"], irregular.inputs[0])
ligar(raio.outputs["Value"], irregular.inputs[2])
pintado = nos.new("ShaderNodeMapRange")              # 1 = pintado, 0 = papel
pintado.inputs["From Min"].default_value = 1.20
pintado.inputs["From Max"].default_value = 1.25
pintado.inputs["To Min"].default_value = 1.0
pintado.inputs["To Max"].default_value = 0.0
ligar(irregular.outputs["Value"], pintado.inputs["Value"])
AZUL = (0.09, 0.45, 0.85)                            # azul-ceu, proximo do azul claro do site Ibmec
parede = nos.new("ShaderNodeMixRGB")
parede.inputs["Color2"].default_value = (*AZUL, 1)
ligar(pintado.outputs["Result"], parede.inputs["Fac"])
ligar(folha.outputs["Color"], parede.inputs["Color1"])
ligar(parede.outputs["Color"], fundo.inputs["Base Color"])
molhado = nos.new("ShaderNodeMapRange")              # tinta fresca brilha mais que o papel
molhado.inputs["To Min"].default_value = 0.75
molhado.inputs["To Max"].default_value = 0.42
ligar(pintado.outputs["Result"], molhado.inputs["Value"])
ligar(molhado.outputs["Result"], fundo.inputs["Roughness"])
grao = nos.new("ShaderNodeTexNoise")
grao.inputs["Scale"].default_value = 900
relevo_papel = nos.new("ShaderNodeBump")
relevo_papel.inputs["Strength"].default_value = 0.08
ligar(grao.outputs["Fac"], relevo_papel.inputs["Height"])
ligar(relevo_papel.outputs["Normal"], fundo.inputs["Normal"])

# ---------------------------------------------------------------- 4. animacao
# --- Plano 1 (1-72): a estrela chega. --------------------------------------
ex, ey, ez = [math.degrees(a) for a in estrela.rotation_euler]
I = (pingo.location.x, 0.0)                        # posicao do "i" no palco
POUSO = (I[0], 0.0, 0.505)

# Trajetoria de meteoro: a cena fica calma, e a estrela desce de uma vez, sem parar,
# acelerando ate acertar o pingo. X e linear e Z acelera (Quad / Ease In): o caminho e uma curva.
INICIO = (1.9, 0.0, 1.95)                           # fora do quadro, no alto a direita
TOQUE = (I[0] + 0.03, 0.0, 0.575)                   # instante em que encosta no pingo
key(estrela, 1, loc=INICIO, rot=(ex, ey, ez + 540), scale=(1, 1, 1))
key(estrela, 42, rot=(ex, ey, ez + 540), interp='LINEAR')        # gira durante a queda
for i in (0, 1):
    chave(estrela, "location", 42, INICIO[i], i, 'LINEAR')
chave(estrela, "location", 42, INICIO[2], 2, 'QUAD', 'EASE_IN')
key(estrela, 76, loc=TOQUE, scale=(1, 1, 1), interp='LINEAR')
key(estrela, 78, loc=(POUSO[0] - 0.035, 0, POUSO[2] - 0.03), rot=(ex, ey, ez),
    scale=(1.22, 0.78, 1))                                       # passa do ponto e amassa
key(estrela, 84, loc=(POUSO[0] + 0.01, 0, POUSO[2] + 0.012), scale=(0.93, 1.10, 1), rot=(ex, ey, ez + 8))
key(estrela, 90, loc=POUSO, scale=(1, 1, 1), rot=(ex, ey, ez - 4))
key(estrela, 96, rot=(ex, ey, ez))
key(estrela, 304, rot=(ex, ey, ez), interp='BACK', easing='EASE_OUT')
key(estrela, 324, rot=(ex, ey, ez - 360))                        # giro de comemoracao
# O lapis passa pela estrela no segundo salto (frames 196-214): ela acende e fica acesa.
for frame, forca_brilho, watts in ((1, 0.0, 0.12), (196, 0.0, 0.12), (205, 2.2, 1.4), (216, 0.7, 0.5)):
    chave(brilho_estrela, "default_value", frame, forca_brilho)
    chave(luz_estrela.data, "energy", frame, watts)

# --- Plano 2 (73-144): troca de lugar. -------------------------------------
p0 = tuple(pingo.location)
key(pingo, 75, loc=p0, scale=(1, 1, 1))
key(pingo, 77, loc=(p0[0], p0[1], p0[2] - 0.012), scale=(1.3, 1.3, 0.6))   # amassado pela estrela
key(pingo, 79, scale=(0.9, 0.9, 1.15))
key(pingo, 83, scale=(1, 1, 1))
bt = borracha.location
topo = (bt.x + 0.03, bt.y, 0.119)                                # em cima da borracha
salto(pingo, 78, 90, (p0[0] - 0.03, p0[1] - 0.03, p0[2]), topo, 0.04)   # derrubado, quase sem subir
salto(pingo, 90, 106, topo, (-0.82, -0.47, 0.034), 0.20)
salto(pingo, 106, 118, (-0.82, -0.47, 0.034), (-0.70, -0.52, 0.034), 0.11)
salto(pingo, 118, 126, (-0.70, -0.52, 0.034), (-0.64, -0.545, 0.034), 0.04)
for i, fim in ((0, -0.585), (1, -0.565)):                        # rola ate parar
    chave(pingo, "location", 126, pingo.location[i], i, 'SINE', 'EASE_OUT')
    chave(pingo, "location", 144, fim, i)
for frame, escala in ((89, (1, 1, 1)), (91, (1.2, 1.2, 0.7)), (94, (1, 1, 1)),
                      (105, (1, 1, 1)), (107, (1.15, 1.15, 0.8)), (110, (1, 1, 1))):
    key(pingo, frame, scale=escala)

# A borracha reage: afunda, da um pulinho e assenta.
b0 = tuple(bt)
br = [math.degrees(a) for a in borracha.rotation_euler]
key(borracha, 89, loc=b0, scale=(1, 1, 1), rot=br)
key(borracha, 92, loc=(b0[0], b0[1], b0[2] - 0.010), scale=(1.06, 1.06, 0.72))
key(borracha, 95, scale=(0.97, 0.97, 1.10))
salto(borracha, 94, 104, b0, b0, 0.07)
key(borracha, 99, rot=(br[0], br[1] + 7, br[2]))
key(borracha, 104, scale=(1, 1, 1), rot=br)
key(borracha, 106, scale=(1.04, 1.04, 0.88))
key(borracha, 110, scale=(1, 1, 1))

# --- Plano 3 (145-240): o lapis levanta, quica e gira. ---------------------
l0 = (lapis.location.x, lapis.location.y, RAIO)
key(lapis, 145, loc=l0, rot=(90, 0, GIRO), scale=ESPESSURA)
key(lapis, 149, rot=(90, 0, GIRO - 7))                           # antecipacao: se mexe
key(lapis, 153, rot=(90, 0, GIRO + 7))
key(lapis, 157, loc=l0, rot=(90, 0, GIRO), interp='BACK', easing='EASE_OUT')
key(lapis, 172, loc=(l0[0], l0[1], 0), rot=(0, 0, 0))            # fica em pe sobre a borracha

giro0 = corpo.rotation_euler.z
paradas = [(l0[0], l0[1], 0), (-1.0, -0.80, 0), (0.05, -0.75, 0), (0.95, -0.55, 0)]
frame = 178
for n in range(3):
    key(lapis, frame - 4, scale=ESPESSURA)
    key(lapis, frame, scale=(1.6, 1.6, 0.82))                    # agacha
    key(lapis, frame + 4, scale=(1.25, 1.25, 1.12))              # estica no ar
    salto(lapis, frame, frame + 16, paradas[n], paradas[n + 1], 0.24)
    # Inclinacao: recua ao agachar, joga o corpo para onde vai e freia ao cair.
    for f, graus in ((frame - 4, 0), (frame, -10), (frame + 3, 32), (frame + 8, 16),
                     (frame + 13, -4), (frame + 16, -16)):
        key(lapis, f, rot=(0, graus, 0))
    # Giro em torno do proprio eixo: uma volta por salto, no corpo do lapis.
    chave(corpo, "rotation_euler", frame, giro0 + math.radians(360 * n), 2, 'LINEAR')
    chave(corpo, "rotation_euler", frame + 16, giro0 + math.radians(360 * (n + 1)), 2)
    key(lapis, frame + 16, scale=(1.6, 1.6, 0.82))               # amassa ao cair
    frame += 18
key(lapis, frame + 2, scale=ESPESSURA, rot=(0, 7, 0))            # frame = 232: balanca e para
key(lapis, frame + 5, rot=(0, 0, 0))

# --- A cor: primeiro sobe pelo lapis, depois varre a cena junto com os saltos. ---
chave(frente_lapis, "location", 148, -0.1, 2, 'LINEAR')
chave(frente_lapis, "location", 172, COMPRIMENTO + 0.1, 2)
chave(frente, "location", 1, -3.0, 0)
chave(frente, "location", 176, -1.75, 0, 'LINEAR')              # encostada na borracha
for n in range(3):
    f = 178 + 18 * n
    chave(frente, "location", f, paradas[n][0] + 0.02, 0, 'LINEAR')
    chave(frente, "location", f + 16, paradas[n + 1][0] + 0.02, 0, 'LINEAR')
chave(frente, "location", 240, 3.0, 0)                           # sai da cena

# Faiscas ao longo do caminho da cor e no impacto da estrela.
def faisca(frame, posicao, tamanho):
    f = obj.new("Faisca", deco1.data.copy())
    f.data.materials.clear()
    f.data.materials.append(faisca_mat)
    colecao("efeitos").objects.link(f)
    f.parent = palco
    f.rotation_mode = 'ZYX'
    f.rotation_euler = deco1.rotation_euler
    x, y, z = posicao
    key(f, 1, scale=(0, 0, 0))
    key(f, frame, loc=(x, y, z), scale=(0, 0, 0), interp='BACK', easing='EASE_OUT')
    key(f, frame + 5, scale=(tamanho, tamanho, tamanho))
    key(f, frame + 16, loc=(x, y, z + 0.10), scale=(0, 0, 0))
    chave(f, "rotation_euler", frame, f.rotation_euler.z, 2, 'LINEAR')
    chave(f, "rotation_euler", frame + 16, f.rotation_euler.z + math.radians(200), 2)


for frame, posicao, tamanho in [
        (77, (I[0] - 0.16, -0.06, 0.60), 0.30), (78, (I[0] + 0.15, -0.06, 0.66), 0.24),
        (79, (I[0] - 0.02, -0.06, 0.74), 0.20),
        (184, (-1.25, -0.25, 0.18), 0.26), (190, (-1.00, -0.30, 0.22), 0.22),
        (199, (-0.80, -0.10, 0.52), 0.28), (203, (-0.50, -0.10, 0.40), 0.22),
        (207, (-0.20, -0.10, 0.50), 0.26), (211, (0.02, -0.10, 0.36), 0.20),
        (218, (0.25, -0.10, 0.48), 0.26), (223, (0.50, -0.10, 0.38), 0.22),
        (228, (0.78, -0.10, 0.46), 0.26)]:
    faisca(frame, posicao, tamanho)

# --- Plano 4 (241-360): a assinatura. --------------------------------------
ESCRITA = (157, 0, GIRO + 533 - 720)                                   # ponta para baixo, inclinado
ponta = Euler([math.radians(g) for g in ESCRITA], 'XYZ').to_matrix() @ Vector((0, 0, 1))


def mao(ponto):
    """Posicao do controle para a ponta do grafite tocar o ponto."""
    return ponto + Vector((0, -0.012, 0)) - ponta * COMPRIMENTO


etapas = [(tracos[0], 248, 276), (tracos[1], 278, 282), (tracos[2], 284, 304)]
inicio = pontos_do_traco(tracos[0], 1)[0]
key(lapis, 232, loc=paradas[3])
key(lapis, 240, loc=(paradas[3][0], paradas[3][1], 0.45), rot=(0, 0, -40))   # sobe primeiro
key(lapis, 248, loc=mao(inicio), rot=ESCRITA, interp='LINEAR')   # depois vira a ponta para baixo
for traco, f0, f1 in etapas:
    chave(traco.data, "bevel_factor_end", 1, 0.0)
    chave(traco.data, "bevel_factor_end", f0, 0.0, interp='LINEAR')
    chave(traco.data, "bevel_factor_end", f1, 1.0)
    passos = (f1 - f0) // 2
    for n, ponto in enumerate(pontos_do_traco(traco, passos)):   # um keyframe a cada 2 frames
        key(lapis, f0 + 2 * n, loc=mao(ponto), interp='LINEAR')
fim = pontos_do_traco(tracos[2], 1)[-1]
key(lapis, 304, loc=mao(fim), rot=ESCRITA)
key(lapis, 310, loc=mao(fim) + Vector((0.12, -0.25, 0.10)), rot=ESCRITA)   # floreio final
descanso = (1.66, -0.95, RAIO)
chave(lapis, "rotation_euler", 324, math.radians(90), 0)         # deita para descansar
for i in (0, 1):
    chave(lapis, "location", 324, descanso[i], i)
chave(lapis, "location", 310, lapis.location.z, 2, 'BOUNCE', 'EASE_OUT')
chave(lapis, "location", 326, RAIO, 2)

# Brilho da assinatura e as duas estrelas decorativas.
chave(emissao, "default_value", 1, 0.25)
chave(emissao, "default_value", 300, 0.25)
chave(emissao, "default_value", 310, 0.7)
chave(emissao, "default_value", 324, 0.3)
for estrelinha, f in ((deco1, 304), (deco2, 309)):
    tamanho = tuple(estrelinha.scale)
    dx, dy, dz = [math.degrees(a) for a in estrelinha.rotation_euler]
    key(estrelinha, 1, scale=(0, 0, 0))
    key(estrelinha, f, scale=(0, 0, 0), rot=(dx, dy, dz + 180), interp='BACK', easing='EASE_OUT')
    key(estrelinha, f + 12, scale=tamanho, rot=(dx, dy, dz))

# --- Final (312-360): o balde vem de tras da camera e pinta o fundo de azul. ---
def simples(nome, cor, rugosidade, metalico=0.0):
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    mat.diffuse_color = (*cor, 1)
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*cor, 1)
    shader.inputs["Roughness"].default_value = rugosidade
    shader.inputs["Metallic"].default_value = metalico
    return mat


def para_efeitos(objeto, nome, pai, mat):
    objeto.name = nome
    for origem in list(objeto.users_collection):
        origem.objects.unlink(objeto)
    colecao("efeitos").objects.link(objeto)
    objeto.parent = pai
    objeto.data.materials.append(mat)
    for face in objeto.data.polygons:
        face.use_smooth = True
    return objeto


tinta = simples("MAT_Tinta", AZUL, 0.3)
esmalte = simples("MAT_Balde", (0.913, 0.413, 0.0), 0.3)       # amarelo Ibmec, para ser lido no fundo claro
arame = simples("MAT_Balde_Alca", (0.6, 0.6, 0.62), 0.35, 1.0)

# Balde (objeto auxiliar): cone truncado; a tampa de cima recebe o material de tinta.
bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.10, radius2=0.135, depth=0.25, location=(0, 0, 0))
balde = para_efeitos(bpy.context.object, "Balde_Tinta", palco, esmalte)
balde.data.materials.append(tinta)
for face in balde.data.polygons:
    if face.normal.z > 0.9:
        face.material_index = 1
        face.use_smooth = False
bpy.ops.mesh.primitive_torus_add(major_radius=0.135, minor_radius=0.008, location=(0, 0, 0))
aro = para_efeitos(bpy.context.object, "Balde_Aro", balde, esmalte)
aro.location = (0, 0, 0.125)
bpy.ops.mesh.primitive_torus_add(major_radius=0.14, minor_radius=0.005, location=(0, 0, 0))
alca = para_efeitos(bpy.context.object, "Balde_Alca", balde, arame)
alca.location = (0, 0, 0.11)
alca.rotation_euler = (math.radians(90), 0, 0)       # aro em pe: a metade de cima e a alca

# Voo do balde: nasce atras da camera, joga a tinta e volta por onde veio.
key(balde, 1, loc=(0.9, -8.0, 2.5), rot=(20, 0, 0))
key(balde, 312, loc=(0.9, -6.3, 1.5), rot=(20, 0, 0))
key(balde, 326, loc=(0.55, -2.7, 0.86), rot=(-70, 0, 15))        # chega inclinando
key(balde, 330, loc=(0.48, -2.55, 0.84), rot=(-118, 0, 20), interp='QUAD', easing='EASE_IN')  # joga
key(balde, 346, loc=(0.9, -6.6, 2.1), rot=(-40, 0, 5))           # recua e sai por cima, sem cobrir a marca

# Gotas grandes de tinta: saem da boca do balde e batem no fundo.
alvos = [(0.3, 3.0, 0.5), (-0.5, 3.3, 0.9), (1.1, 3.4, 1.0), (0.0, 3.6, 1.5),
         (0.7, 2.6, 0.1), (-0.2, 2.4, 0.05), (1.5, 3.0, 0.4)]
for n, destino in enumerate(alvos):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=(0, 0, 0))
    gota = para_efeitos(bpy.context.object, "Tinta_Gota", palco, tinta)
    sai, chega = 327 + n % 3, 333 + n % 4
    tamanho = 0.13 - 0.010 * n
    key(gota, 1, scale=(0, 0, 0))
    key(gota, sai - 1, scale=(0, 0, 0))
    key(gota, sai, scale=(tamanho, tamanho * 1.8, tamanho))
    salto(gota, sai, chega, (0.5, -2.45, 0.9), destino, 0.25)
    key(gota, chega, scale=(tamanho, tamanho * 1.8, tamanho))
    key(gota, chega + 2, scale=(0, 0, 0))                       # some dentro da mancha

# O diafragma fecha no final (f/2.8 -> f/11) para o balde, perto da camera, ficar nitido.
chave(camera.data.dof, "aperture_fstop", 300, 2.8)
chave(camera.data.dof, "aperture_fstop", 318, 11.0)

# A mancha azul cresce depressa e desacelera ate cobrir todo o cenario.
chave(tinta_centro, "scale", 1, (0.001, 0.001, 0.001))
chave(tinta_centro, "scale", 333, (0.001, 0.001, 0.001), interp='QUAD', easing='EASE_OUT')
chave(tinta_centro, "scale", 347, (14, 14, 14))

# --- Camera: poucos keyframes, sempre com a palavra inteira no quadro. -----
#            frame  camera (x, y, z)        alvo (x, y, z)
planos = [(1,   (0.10, -6.3, 1.55),  (0.00, 0, 0.55)),
          (58,  (0.05, -6.0, 1.45),  (-0.05, 0, 0.55)),     # aberta: mostra a queda inteira
          (98,  (-0.45, -4.0, 0.60), (-0.50, 0, 0.34)),     # aproxima com o impacto
          (120, (-0.50, -4.0, 0.56), (-0.50, 0, 0.30)),
          (150, (-0.42, -4.45, 0.62), (-0.42, 0, 0.40)),
          (232, (0.22, -4.5, 0.64),  (0.22, 0, 0.40)),
          (300, (0.72, -4.6, 0.60),  (0.72, 0, 0.30)),
          (344, (0.32, -5.15, 0.70), (0.32, 0, 0.30)),
          (360, (0.32, -5.05, 0.70), (0.32, 0, 0.30))]
camera.rotation_euler = (0, 0, 0)
for frame, posicao, olhar in planos:
    key(camera, frame, loc=posicao)
    key(alvo, frame, loc=olhar)

# ---------------------------------------------------------- 5. render e saida
cena.render.engine = 'CYCLES'
cena.cycles.device = 'GPU'
cena.cycles.samples = 128
cena.cycles.use_denoising = True
cena.render.use_motion_blur = True
cena.render.motion_blur_shutter = 0.4
cena.render.use_persistent_data = True
cena.render.resolution_x, cena.render.resolution_y = 1920, 1080
cena.render.resolution_percentage = 100
cena.view_settings.view_transform = 'AgX'
cena.view_settings.look = 'AgX - Medium High Contrast'
cena.view_settings.exposure = 0.3

# Compositor: no Glare (bloom) para o brilho dourado da assinatura.
cena.use_nodes = True
arvore = cena.node_tree
glare = arvore.nodes.new("CompositorNodeGlare")
glare.glare_type = 'BLOOM'
glare.inputs["Threshold"].default_value = 4.0
glare.inputs["Strength"].default_value = 0.35
glare.inputs["Size"].default_value = 0.3
arvore.links.new(arvore.nodes["Render Layers"].outputs["Image"], glare.inputs["Image"])
# Vinheta suave: escurece um pouco os cantos para segurar o olhar no centro.
elipse = arvore.nodes.new("CompositorNodeEllipseMask")
elipse.mask_width, elipse.mask_height = 0.95, 0.90
desfoque = arvore.nodes.new("CompositorNodeBlur")
desfoque.size_x = desfoque.size_y = 400
desfoque.inputs["Size"].default_value = (400, 400)
arvore.links.new(elipse.outputs["Mask"], desfoque.inputs["Image"])
vinheta = arvore.nodes.new("CompositorNodeMixRGB")
vinheta.blend_type = 'MULTIPLY'
vinheta.inputs["Fac"].default_value = 0.35
arvore.links.new(glare.outputs["Image"], vinheta.inputs[1])
arvore.links.new(desfoque.outputs["Image"], vinheta.inputs[2])
arvore.links.new(vinheta.outputs["Image"], arvore.nodes["Composite"].inputs["Image"])

# Saida: video MP4 com codec H.264 (Render > Render Animation).
cena.render.image_settings.file_format = 'FFMPEG'
cena.render.ffmpeg.format = 'MPEG4'
cena.render.ffmpeg.codec = 'H264'
cena.render.ffmpeg.constant_rate_factor = 'HIGH'
cena.render.filepath = "//AP2_MarceuFilho.mp4"

bpy.data.collections["Ibmec_Conceito"].name = "AP2_Ibmec_Stars"
cena.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath("//../AP2/AP2_MarceuFilho.blend"))
print("AP2 salva.")
