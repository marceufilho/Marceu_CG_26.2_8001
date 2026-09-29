import bpy
import math

# Blender 4.5 LTS. Execute em um arquivo novo: Scripting > Run Script.
# Usa apenas recursos que ja acompanham o Blender.
# Ao executar novamente, substitui apenas a colecao desta atividade.
colecao_antiga = bpy.data.collections.get("AC03_transformacoes")
if colecao_antiga:
    for objeto in list(colecao_antiga.objects):
        bpy.data.objects.remove(objeto, do_unlink=True)
    bpy.data.collections.remove(colecao_antiga)

colecao = bpy.data.collections.new("AC03_transformacoes")
bpy.context.scene.collection.children.link(colecao)


def organizar(objeto, nome, material=None):
    objeto.name = nome
    for origem in list(objeto.users_collection):
        origem.objects.unlink(objeto)
    colecao.objects.link(objeto)
    if material:
        objeto.data.materials.append(material)
    return objeto


def material(nome, cor):
    mat = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    mat.diffuse_color = (*cor, 1)
    mat.use_nodes = True
    shader = next(no for no in mat.node_tree.nodes if no.type == 'BSDF_PRINCIPLED')
    shader.inputs["Base Color"].default_value = (*cor, 1)
    shader.inputs["Roughness"].default_value = 0.65
    return mat


azul = material("AC03_azul", (0.055, 0.32, 0.65))
laranja = material("AC03_laranja", (0.95, 0.32, 0.07))
verde = material("AC03_verde", (0.035, 0.48, 0.32))
claro = material("AC03_fundo", (0.86, 0.88, 0.83))
escuro = material("AC03_texto", (0.035, 0.065, 0.10))

# 1. Formas 2D: todos os vertices ficam no plano XY (Z = 0).
bpy.ops.mesh.primitive_plane_add(size=1.7, location=(-3.8, -2.0, 0))
quadrado = organizar(bpy.context.object, "obj2d_quadrado", azul)
quadrado.scale = (0.85, 0.85, 1)

malha = bpy.data.meshes.new("malha_triangulo")
malha.from_pydata([(-1, -0.7, 0), (1, -0.7, 0), (0, 1, 0)], [], [(0, 1, 2)])
malha.update()
triangulo = bpy.data.objects.new("obj2d_triangulo", malha)
colecao.objects.link(triangulo)
triangulo.data.materials.append(laranja)
triangulo.location = (0, -1.8, 0)
triangulo.rotation_euler.z = math.radians(-15)
triangulo.scale = (0.85, 0.85, 1)

bpy.ops.mesh.primitive_circle_add(vertices=48, radius=0.85, fill_type='NGON',
                                  location=(3.3, -1.8, 0))
circulo = organizar(bpy.context.object, "obj2d_circulo", verde)
circulo.scale = (1.1, 1.1, 1)

# 2. Solidos 3D: posicao, rotacao e escala nos eixos X, Y e Z.
bpy.ops.mesh.primitive_cube_add(size=1.5, location=(-3.3, 1.8, 1.4))
cubo = organizar(bpy.context.object, "obj3d_cubo", azul)
cubo.scale = (0.8, 0.8, 0.8)

bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.7, depth=2,
                                    location=(0, 1.8, 1))
cilindro = organizar(bpy.context.object, "obj3d_cilindro", laranja)
# Este cilindro fica sem animacao 

bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.95,
                                     location=(3.3, 1.8, 1.05))
esfera = organizar(bpy.context.object, "obj3d_esfera_uv", verde)
esfera.scale = (1, 0.85, 1.1)
for face in esfera.data.polygons:
    face.use_smooth = True

# 3. Animacao: 120 frames a 24 fps = 5 segundos.
cena = bpy.context.scene
cena.name = "Parque Geometrico"
cena.frame_start = 1
cena.frame_end = 120
cena.render.fps = 24
cena.render.fps_base = 1

quadrado.keyframe_insert(data_path="location", frame=1)
quadrado.keyframe_insert(data_path="rotation_euler", frame=1)
quadrado.location = (-3.3, -1.8, 0)
quadrado.rotation_euler.z = math.radians(45)
quadrado.keyframe_insert(data_path="location", frame=120)
quadrado.keyframe_insert(data_path="rotation_euler", frame=120)

cubo.keyframe_insert(data_path="scale", frame=1)
cubo.keyframe_insert(data_path="rotation_euler", frame=1)
cubo.scale = (1.1, 0.7, 1.2)
cubo.rotation_euler = (math.radians(25), math.radians(15), math.radians(40))
cubo.keyframe_insert(data_path="scale", frame=120)
cubo.keyframe_insert(data_path="rotation_euler", frame=120)
# A interpolacao Bezier padrao suaviza o inicio e o fim dos movimentos.

# 4. Apresentacao simples: fundo, nomes, camera e uma luz.
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.06))
organizar(bpy.context.object, "cenario_chao", claro)


def texto(conteudo, x, y, tamanho):
    bpy.ops.object.text_add(location=(x, y, -0.035))
    obj = organizar(bpy.context.object, "legenda_" + conteudo, escuro)
    obj.data.body = conteudo
    obj.data.align_x = 'CENTER'
    obj.data.size = tamanho


texto("PARQUE GEOMETRICO", 0, 5.3, 0.55)
texto("Transformacoes 2D e 3D", 0, 4.65, 0.25)
for x, nome in [(-3.3, "QUADRADO"), (0, "TRIANGULO"), (3.3, "CIRCULO")]:
    texto(nome, x, -3.2, 0.24)
for x, nome in [(-3.3, "CUBO"), (0, "CILINDRO"), (3.3, "ESFERA UV")]:
    texto(nome, x, 0.15, 0.24)

bpy.ops.object.camera_add(location=(0, -12, 17))
camera = organizar(bpy.context.object, "camera_cena")
from mathutils import Vector  # Tambem faz parte do Blender.
camera.rotation_euler = (Vector((0, 0.5, 0)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 13.5
cena.camera = camera

bpy.ops.object.light_add(type='AREA', location=(-3, -4, 10))
luz = organizar(bpy.context.object, "luz_principal")
luz.data.energy = 1800
luz.data.shape = 'DISK'
luz.data.size = 7
cena.world = cena.world or bpy.data.worlds.new("Mundo")
cena.world.use_nodes = True
fundo = next(no for no in cena.world.node_tree.nodes if no.type == 'BACKGROUND')
fundo.inputs[0].default_value = (0.7, 0.78, 0.9, 1)
fundo.inputs[1].default_value = 0.4
cena.render.engine = 'CYCLES'
cena.cycles.samples = 32
cena.cycles.use_denoising = True
cena.render.resolution_x = 1200
cena.render.resolution_y = 1000
cena.render.resolution_percentage = 100
cena.render.image_settings.file_format = 'PNG'
cena.view_settings.view_transform = 'AgX'
cena.frame_set(120)

# Objetos de outras colecoes (como o cubo inicial) nao entram no render.
for camada in bpy.context.view_layer.layer_collection.children:
    camada.exclude = camada.collection != colecao

bpy.ops.object.select_all(action='DESELECT')
cilindro.select_set(True)
bpy.context.view_layer.objects.active = cilindro
for tela in bpy.data.screens:
    for area in tela.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.camera = camera
            area.spaces.active.shading.color_type = 'MATERIAL'
            area.spaces.active.overlay.show_extras = False
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
            area.spaces.active.region_3d.view_camera_zoom = 15

print("Parque Geometrico pronto. Pratique G, R e S no cilindro e salve.")
