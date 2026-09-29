# Parque Geométrico — AC03

**Aluno:** Marceu Filho  
**Ferramenta:** Blender 4.5 LTS, com Python integrado.

## Arquivos

Os três arquivos ficam diretamente na pasta AC3:

- [AC03_marceuFilho.blend](AC03_marceuFilho.blend): cena e animação.
- [AC03_marceuFilho.py](AC03_marceuFilho.py): script para criar a cena.
- [AC03_marceuFilho.png](AC03_marceuFilho.png): imagem renderizada.

## Explicação da cena

O Parque Geométrico contém quadrado, triângulo, círculo, cubo, cilindro e esfera UV.  
Os objetos estão organizados na coleção `AC03_transformacoes`.  
As formas 2D ficam no plano XY: o quadrado muda de posição, gira em Z e tem escala reduzida.  
O triângulo também foi girado e reduzido, e o círculo foi aumentado.  
Em 3D, o cubo muda de escala e gira em X, Y e Z; a esfera tem escala diferente em Y e Z.  
O Python criou as seis formas, aplicou as transformações e inseriu keyframes nos frames 1 e 120.  
A parte manual com G, R e S no cilindro ainda deve ser feita conforme as instruções abaixo.  
A animação tem 120 frames a 24 fps, com movimento suave, e as rotações usam `math.radians()`.

## Bônus realizado: suavização da animação (easing)

Foi usada a interpolação **Bézier**, nos keyframes do quadrado e do cubo. Isso faz os movimentos começarem devagar, acelerarem no meio e desacelerarem no final, entre os frames 1 e 120. Essa suavização corresponde ao item de variação temporal adicional citado no bônus.

Para conferir, reproduza a animação ou selecione um desses objetos e abra o **Graph Editor** para ver as curvas. Não foi usada hierarquia pai/filho (`parent/child`); portanto, apenas a parte de suavização do bônus foi realizada.


## Questões teóricas

### 1. Qual é a diferença entre translação, rotação e escala?

Translação muda a posição do objeto. Rotação gira o objeto ao redor de um eixo. Escala aumenta ou diminui suas dimensões. A escala pode ser diferente em cada eixo.

### 2. Qual é a diferença entre espaço local e global?

O espaço global usa os eixos fixos da cena. O espaço local usa os eixos do próprio objeto, que acompanham sua rotação. Depois de inclinar um cilindro, mover no Z global move para cima; mover no Z local move na direção inclinada do cilindro. No Blender, com orientação Global, `G Z` usa Z global e `G Z Z` usa Z local.

### 3. Por que rotações em eixos diferentes geram resultados distintos?

Cada eixo define uma direção diferente para o giro. Por exemplo, girar em Z faz um cubo girar em torno do eixo vertical; girar em X faz o cubo tombar. A ordem das rotações também pode mudar a orientação final.

### 4. Por que usar math.radians() em rotation_euler?

`rotation_euler` recebe os ângulos em radianos. `math.radians()` converte graus para essa unidade. Por exemplo, `math.radians(90)` equivale a pi/2 radianos.

### 5. Quando vale mais a pena usar Python?

Quando é preciso repetir ações. Por exemplo, criar dez cubos com a mesma distância entre eles pode ser feito com um laço, evitando repetir os comandos manualmente. Para ajustar rapidamente um único objeto, a interface é prática.
