import bpy
import math

# AC05 - Materiais PBR e Texturas. Blender 4.5 LTS.
# Abra AC4/AC04_MarceuFilho.blend e execute este script (Scripting > Run Script).
# Ele salva uma copia em AC5/AC05_MarceuFilho.blend; a AC04 nao e alterada.

PASTA = bpy.path.abspath("//../AC5/texturas/")
cena = bpy.context.scene


def imagem(mat, arquivo, dado, mapeamento, altura):
    """Cria um no Image Texture. Mapas de dados (rugosidade, normal) usam Non-Color."""
    no = mat.node_tree.nodes.new("ShaderNodeTexImage")
    no.location = (-500, altura)
    no.image = bpy.data.images.load(PASTA + arquivo, check_existing=True)
    if dado:
        no.image.colorspace_settings.name = 'Non-Color'
    mat.node_tree.links.new(mapeamento.outputs["Vector"], no.inputs["Vector"])
    return no


def material_pbr(nome, cor, rugosidade, metalico=0.0, base=None, rug=None, normal=None,
                 escala=(1, 1, 1), relevo=1.0):
    """Principled BSDF com mapas opcionais de cor base, rugosidade e normal."""
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    mat.diffuse_color = (*cor, 1)
    nos, ligar = mat.node_tree.nodes, mat.node_tree.links.new
    shader = nos["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*cor, 1)
    shader.inputs["Roughness"].default_value = rugosidade
    shader.inputs["Metallic"].default_value = metalico
    shader.location, nos["Material Output"].location = (200, 300), (520, 300)

    if base or rug or normal:
        uv = nos.new("ShaderNodeTexCoord")
        mapeamento = nos.new("ShaderNodeMapping")
        mapeamento.inputs["Scale"].default_value = escala
        uv.location, mapeamento.location = (-960, 300), (-750, 300)     # nos organizados
        ligar(uv.outputs["UV"], mapeamento.inputs["Vector"])
    if base:
        ligar(imagem(mat, base, False, mapeamento, 700).outputs["Color"], shader.inputs["Base Color"])
    if rug:
        ligar(imagem(mat, rug, True, mapeamento, 350).outputs["Color"], shader.inputs["Roughness"])
    if normal:
        mapa = nos.new("ShaderNodeNormalMap")
        mapa.inputs["Strength"].default_value = relevo
        mapa.location = (-170, -60)
        ligar(imagem(mat, normal, True, mapeamento, 0).outputs["Color"], mapa.inputs["Color"])
        ligar(mapa.outputs["Normal"], shader.inputs["Normal"])
    return mat


def aplicar(nomes, mat):
    for nome in nomes:
        dados = bpy.data.objects[nome].data
        dados.materials.clear()
        dados.materials.append(mat)


def uv_cilindrico(nome):
    """Projecao cilindrica em torno do eixo Z local: U = angulo, V = altura."""
    malha = bpy.data.objects[nome].data
    uv = malha.uv_layers.active.data
    alturas = [v.co.z for v in malha.vertices]
    base, altura = min(alturas), max(alturas) - min(alturas)
    for face in malha.polygons:
        us = []
        for i in face.loop_indices:
            p = malha.vertices[malha.loops[i].vertex_index].co
            if abs(face.normal.z) > 0.9:                  # tampas: projecao plana
                uv[i].uv = (p.x * 10 + 0.5, p.y * 10 + 0.5)
            else:
                u = math.atan2(p.y, p.x) / (2 * math.pi) + 0.5
                uv[i].uv = (u, (p.z - base) / altura)
                us.append(u)
        if us and max(us) - min(us) > 0.5:                # face que cruza a emenda
            for i in face.loop_indices:
                if uv[i].uv.x < 0.5:
                    uv[i].uv.x += 1


def uv_smart(nome):
    objeto = bpy.data.objects[nome]
    bpy.ops.object.select_all(action='DESELECT')
    objeto.select_set(True)
    bpy.context.view_layer.objects.active = objeto
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')


# 1. Mapas UV dos objetos que recebem textura de imagem.
for nome in ["Lapis_Corpo", "Lapis_Madeira", "Lapis_Ferrule"]:
    uv_cilindrico(nome)
uv_smart("Obj_Estrela")

# 2. Materiais PBR.
# Lapis = MADEIRA (Poly Haven "oak_veneer_01", CC0): cor base + rugosidade + normal.
madeira = material_pbr("MAT_Madeira_PBR", (0.75, 0.55, 0.35), 0.5,
                       base="oak_veneer_01_diff_1k.jpg",
                       rug="oak_veneer_01_rough_1k.jpg",
                       normal="oak_veneer_01_nor_gl_1k.jpg", escala=(0.5, 0.5, 1))
# Ferrule do lapis = METAL escovado (ambientCG "Metal032", CC0).
metal = material_pbr("MAT_Metal_Escovado", (0.8, 0.8, 0.8), 0.3, metalico=1.0,
                     base="Metal032_1K-JPG_Color.jpg",
                     rug="Metal032_1K-JPG_Roughness.jpg",
                     normal="Metal032_1K-JPG_NormalGL.jpg", escala=(1, 0.25, 1), relevo=0.5)
# Estrela = METAL dourado: cor solida, com rugosidade e normal do mesmo metal.
ouro = material_pbr("MAT_Ouro_PBR", (1.0, 0.62, 0.12), 0.25, metalico=1.0,
                    rug="Metal032_1K-JPG_Roughness.jpg",
                    normal="Metal032_1K-JPG_NormalGL.jpg", escala=(0.6, 0.6, 1), relevo=0.3)
# Borracha = material procedural: ruido fino ligado a um no Bump.
borracha = material_pbr("MAT_Borracha_PBR", (0.88, 0.87, 0.83), 0.8)
nos, ligar = borracha.node_tree.nodes, borracha.node_tree.links.new
ruido = nos.new("ShaderNodeTexNoise")
ruido.inputs["Scale"].default_value = 400
ruido.location = (-250, 0)
relevo = nos.new("ShaderNodeBump")
relevo.inputs["Strength"].default_value = 0.15
relevo.location = (-20, 0)
ligar(ruido.outputs["Fac"], relevo.inputs["Height"])
ligar(relevo.outputs["Normal"], nos["Principled BSDF"].inputs["Normal"])

capa = material_pbr("MAT_Capa_Papel", (0.04, 0.53, 0.84), 0.6)       # azul claro do site Ibmec
grafite = material_pbr("MAT_Grafite", (0.03, 0.03, 0.035), 0.35, metalico=0.6)
rosa = material_pbr("MAT_Borracha_Rosa", (0.85, 0.30, 0.33), 0.8)
# Marca: cores oficiais do logotipo, sem textura (identidade visual preservada).
ibmec = material_pbr("MAT_Ibmec_PBR", (0.0, 0.0185, 0.0908), 0.35)   # azul #002555
pingo = material_pbr("MAT_Ibmec_Pingo_PBR", (0.913, 0.413, 0.0), 0.35)  # amarelo #F5AC00

aplicar(["Lapis_Corpo", "Lapis_Madeira"], madeira)
aplicar(["Lapis_Ferrule"], metal)
aplicar(["Lapis_Grafite"], grafite)
aplicar(["Lapis_Borracha"], rosa)
aplicar(["Obj_Estrela", "Estrela_Decorativa_01", "Estrela_Decorativa_02", "Texto_Stars"], ouro)
aplicar(["Borracha_Corpo"], borracha)
aplicar(["Borracha_Capa"], capa)
aplicar(["Marca_Ibmec"], ibmec)
aplicar(["Marca_Pingo"], pingo)

# Remove os materiais de estudo da AC04, agora sem uso.
for mat in list(bpy.data.materials):
    if mat.users == 0:
        bpy.data.materials.remove(mat)

# 3. Ambiente: HDRI de estudio (Poly Haven "studio_small_08", CC0) para os metais refletirem.
nos, ligar = cena.world.node_tree.nodes, cena.world.node_tree.links.new
hdri = nos.new("ShaderNodeTexEnvironment")
hdri.image = bpy.data.images.load(PASTA + "studio_small_08_1k.hdr", check_existing=True)
ligar(hdri.outputs["Color"], nos["Background"].inputs["Color"])
nos["Background"].inputs["Strength"].default_value = 0.25

# 4. Salva com as imagens empacotadas no .blend.
bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath("//../AC5/AC05_MarceuFilho.blend"))
bpy.ops.file.pack_all()
bpy.ops.wm.save_mainfile()
print("AC05 salva.")
