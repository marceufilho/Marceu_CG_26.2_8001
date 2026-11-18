import bpy
import math
from mathutils import Vector

# AC04 - Modelos de Iluminacao. Blender 4.5 LTS.
# Abra AP1/AP1_MarceuFilho.blend e execute este script (Scripting > Run Script).
# Ele salva uma copia em AC4/AC04_MarceuFilho.blend; a AP1 nao e alterada.

cena = bpy.context.scene
marca = bpy.data.objects["Marca_Ibmec"]

# A palavra esta na diagonal da cena. U = direcao da leitura, N = frente.
U = (marca.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
N = Vector((U.y, -U.x, 0))


def P(u, n, z):
    """Ponto da cena: u ao longo da palavra, n para a frente, z para cima."""
    return U * u + N * n + Vector((0, 0, z))


def colecao(nome):
    col = bpy.data.collections.get(nome) or bpy.data.collections.new(nome)
    if col.name not in cena.collection.children:
        cena.collection.children.link(col)
    return col


def mover(objeto, col):
    for origem in list(objeto.users_collection):
        origem.objects.unlink(objeto)
    col.objects.link(objeto)


def apontar(objeto, alvo):
    objeto.rotation_euler = (alvo - objeto.location).to_track_quat('-Z', 'Y').to_euler()


def material(nome, cor, rugosidade, especular=0.5):
    mat = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    mat.use_nodes = True
    mat.diffuse_color = (*cor, 1)
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*cor, 1)
    shader.inputs["Roughness"].default_value = rugosidade
    shader.inputs["Specular IOR Level"].default_value = especular
    return mat


def aplicar(nomes, mat):
    for nome in nomes:
        dados = bpy.data.objects[nome].data
        dados.materials.clear()
        dados.materials.append(mat)


# 1. Cenario: fundo infinito (chao que sobe em curva ate virar parede).
perfil = [(9, 0)]
for i in range(17):
    angulo = math.radians(90 * i / 16)
    perfil.append((-3 - 2 * math.sin(angulo), 2 - 2 * math.cos(angulo)))
perfil.append((-5, 9))
vertices = [P(u, n, z) for n, z in perfil for u in (-14, 14)]
faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(perfil) - 1)]
malha = bpy.data.meshes.new("Cenario_Fundo")
malha.from_pydata(vertices, [], faces)
for face in malha.polygons:
    face.use_smooth = True
fundo = bpy.data.objects.new("Cenario_Fundo", malha)
colecao("cenario").objects.link(fundo)
malha.materials.append(material("MAT_Fundo", (0.80, 0.78, 0.74), 0.9, 0.2))

# 2. Camera principal: perto e baixa, de frente para a palavra.
camera = bpy.data.objects["Camera"]
camera.name = "CAM_Principal"
camera.data.name = "CAM_Principal"
camera.location = P(0.08, 5.1, 0.7)
apontar(camera, P(0.08, 0, 0.36))
camera.data.lens = 50
mover(camera, colecao("cameras"))
cena.camera = camera

# 3. Luzes: principal (Area, quente) e preenchimento (Area grande, fria e fraca).
bpy.data.objects.remove(bpy.data.objects["Light"])


def luz(nome, posicao, alvo, potencia, tamanho, cor):
    dados = bpy.data.lights.new(nome, 'AREA')
    dados.shape = 'DISK'
    dados.energy = potencia
    dados.size = tamanho
    dados.color = cor
    objeto = bpy.data.objects.new(nome, dados)
    objeto.location = posicao
    apontar(objeto, alvo)
    colecao("luzes").objects.link(objeto)
    return objeto


centro = P(0, 0, 0.3)
luz("LUZ_Principal", P(-2.2, 2.6, 3.0), centro, 160, 1.5, (1.0, 0.93, 0.82))
luz("LUZ_Preenchimento", P(3.0, 3.0, 1.4), centro, 35, 4.0, (0.82, 0.90, 1.0))

mundo = cena.world
mundo.use_nodes = True
mundo.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.80, 0.90, 1)
mundo.node_tree.nodes["Background"].inputs[1].default_value = 0.12

# 4. Materiais: um modelo de iluminacao por objeto autoral.
# O Principled BSDF e baseado em fisica; Phong e Blinn-Phong sao aproximacoes visuais.
lambert = material("MAT_Lambert", (0.80, 0.22, 0.22), 1.0, 0.0)       # fosco
phong = material("MAT_Phong", (0.03, 0.45, 0.80), 0.2, 0.5)           # polido
blinn = material("MAT_BlinnPhong", (0.913, 0.413, 0.0), 0.1, 1.0)     # mais polido
# Cores oficiais do logotipo Ibmec (SVG do site ibmec.br):
# letras em azul #002555 e pingo do "i" em amarelo #F5AC00 (valores lineares abaixo).
ibmec = material("MAT_Ibmec", (0.0, 0.0185, 0.0908), 0.45, 0.5)
pingo = material("MAT_Ibmec_Pingo", (0.913, 0.413, 0.0), 0.45, 0.5)
auxiliar = material("MAT_Auxiliar", (0.55, 0.55, 0.55), 0.6, 0.5)

aplicar(["Borracha_Corpo", "Borracha_Capa"], lambert)
aplicar(["Lapis_Corpo", "Lapis_Madeira", "Lapis_Grafite", "Lapis_Ferrule", "Lapis_Borracha"], phong)
aplicar(["Obj_Estrela"], blinn)
aplicar(["Marca_Ibmec"], ibmec)
aplicar(["Marca_Pingo"], pingo)
aplicar(["Texto_Stars", "Estrela_Decorativa_01", "Estrela_Decorativa_02"], auxiliar)

# 5. Camera extra para a imagem comparativa dos tres materiais (mesma luz).
dados = bpy.data.cameras.new("CAM_Comparacao")
dados.lens = 50
comparacao = bpy.data.objects.new("CAM_Comparacao", dados)
comparacao.location = P(-0.72, 3.1, 0.8)
apontar(comparacao, P(-0.72, 0.2, 0.36))
colecao("cameras").objects.link(comparacao)

# 6. Organizacao e render.
antiga = bpy.data.collections.get("Collection")
if antiga and not antiga.all_objects:
    bpy.data.collections.remove(antiga)
bpy.data.collections["AP1_Ibmec_Conceito"].name = "Ibmec_Conceito"

cena.render.engine = 'CYCLES'
cena.cycles.device = 'GPU'
cena.cycles.samples = 128
cena.cycles.use_denoising = True
cena.render.resolution_x = 1920
cena.render.resolution_y = 1080
cena.view_settings.view_transform = 'AgX'
cena.view_settings.look = 'AgX - Medium High Contrast'

bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath("//../AC4/AC04_MarceuFilho.blend"))
print("AC04 salva.")
