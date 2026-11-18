import bpy

# Render final da AP2 em duas etapas (permite retomar se for interrompido):
#   blender -b AP2_MarceuFilho.blend --python renderizar.py
# 1) quadros PNG em AP2/frames/   2) video MP4 (H.264) montado no sequenciador do Blender.
cena = bpy.context.scene
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'                 # GPU NVIDIA; troque se necessario
prefs.get_devices()
for dispositivo in prefs.devices:
    dispositivo.use = dispositivo.type == 'OPTIX'

cena.render.image_settings.file_format = 'PNG'
cena.render.filepath = "//frames/quadro_"
cena.render.use_overwrite = False                   # nao refaz quadros ja prontos
bpy.ops.render.render(animation=True)

video = bpy.data.scenes.new("Montagem")
video.frame_start, video.frame_end = 1, 360
video.render.fps = 24
video.render.resolution_x, video.render.resolution_y = 1920, 1080
video.view_settings.view_transform = 'Standard'     # os PNG ja estao com o AgX aplicado
tiras = video.sequence_editor_create().sequences
tira = tiras.new_image("quadros", bpy.path.abspath("//frames/quadro_0001.png"), 1, 1)
for n in range(2, 361):
    tira.elements.append(f"quadro_{n:04d}.png")
video.render.image_settings.file_format = 'FFMPEG'
video.render.ffmpeg.format = 'MPEG4'
video.render.ffmpeg.codec = 'H264'
video.render.ffmpeg.constant_rate_factor = 'HIGH'
video.render.filepath = bpy.path.abspath("//AP2_MarceuFilho.mp4")
video.render.use_file_extension = False
bpy.ops.render.render(animation=True, scene="Montagem")
print("Video pronto.")
