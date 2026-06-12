"""
Gera o PDF de apresentacao da 1a entrega — "Academico".
Saida: ESPECIFICACOES.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Preformatted, KeepTogether,
)
from reportlab.pdfgen import canvas

# ============== CORES ==============
ACCENT = colors.HexColor("#7c5cff")
ACCENT_DARK = colors.HexColor("#5b3df0")
INK = colors.HexColor("#1a1d29")
INK_SOFT = colors.HexColor("#3a3f55")
MUTED = colors.HexColor("#6b7280")
LINE = colors.HexColor("#e5e7eb")
BG_SOFT = colors.HexColor("#f7f7fb")
TABLE_HEADER_BG = colors.HexColor("#1a1d29")
SUCCESS = colors.HexColor("#22c55e")
WARNING = colors.HexColor("#f59e0b")
DANGER = colors.HexColor("#ef4444")

# ============== ESTILOS ==============
styles = getSampleStyleSheet()

style_title = ParagraphStyle(
    "Title", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=28, leading=34,
    textColor=INK, alignment=TA_LEFT, spaceAfter=6,
)
style_subtitle = ParagraphStyle(
    "Subtitle", parent=styles["Normal"],
    fontName="Helvetica", fontSize=14, leading=20,
    textColor=ACCENT, alignment=TA_LEFT, spaceAfter=2,
)
style_meta = ParagraphStyle(
    "Meta", parent=styles["Normal"],
    fontName="Helvetica", fontSize=11, leading=16,
    textColor=MUTED, alignment=TA_LEFT,
)
style_h1 = ParagraphStyle(
    "H1", parent=styles["Heading1"],
    fontName="Helvetica-Bold", fontSize=18, leading=24,
    textColor=INK, spaceBefore=20, spaceAfter=10,
    borderPadding=(0, 0, 6, 0),
)
style_h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=13, leading=18,
    textColor=ACCENT_DARK, spaceBefore=12, spaceAfter=6,
)
style_body = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontName="Helvetica", fontSize=10.5, leading=15,
    textColor=INK_SOFT, alignment=TA_JUSTIFY, spaceAfter=6,
)
style_bullet = ParagraphStyle(
    "Bullet", parent=style_body,
    leftIndent=14, bulletIndent=2, alignment=TA_LEFT, spaceAfter=3,
)
style_code = ParagraphStyle(
    "Code", parent=styles["Code"],
    fontName="Courier", fontSize=8.5, leading=11,
    textColor=INK, backColor=BG_SOFT, borderColor=LINE,
    borderWidth=0.5, borderPadding=8, spaceBefore=4, spaceAfter=10,
    leftIndent=0, rightIndent=0,
)
style_caption = ParagraphStyle(
    "Caption", parent=styles["Italic"],
    fontName="Helvetica-Oblique", fontSize=9, leading=12,
    textColor=MUTED, alignment=TA_CENTER, spaceAfter=10,
)


# ============== HELPER: barras coloridas (cabecalho/rodape) ==============
def on_page(canvas_obj, doc):
    canvas_obj.saveState()
    # barra superior fina com gradiente simulado por 3 retangulos
    page_w, page_h = A4
    canvas_obj.setFillColor(ACCENT)
    canvas_obj.rect(0, page_h - 0.4 * cm, page_w, 0.4 * cm, stroke=0, fill=1)

    # rodape: numero da pagina + projeto
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.drawString(2 * cm, 1.2 * cm, "Academico - Chatbot RAG Academico")
    canvas_obj.drawRightString(page_w - 2 * cm, 1.2 * cm, f"pagina {doc.page}")
    canvas_obj.setStrokeColor(LINE)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(2 * cm, 1.5 * cm, page_w - 2 * cm, 1.5 * cm)
    canvas_obj.restoreState()


def on_cover(canvas_obj, doc):
    canvas_obj.saveState()
    page_w, page_h = A4
    # bloco lateral colorido na capa
    canvas_obj.setFillColor(ACCENT)
    canvas_obj.rect(0, 0, 1.2 * cm, page_h, stroke=0, fill=1)
    # tarja diagonal sutil no topo
    canvas_obj.setFillColor(ACCENT_DARK)
    canvas_obj.rect(0, page_h - 4 * cm, page_w, 0.15 * cm, stroke=0, fill=1)
    canvas_obj.restoreState()


# ============== HELPER: tabela estilizada ==============
def make_table(data, col_widths=None, header_bg=None):
    header_bg = header_bg or TABLE_HEADER_BG
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_SOFT]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
    ])
    t.setStyle(style)
    return t


def p(text, style=None):
    return Paragraph(text, style or style_body)


def bullet(text):
    return Paragraph(f"&bull;&nbsp;&nbsp;{text}", style_bullet)


def code_block(text):
    return Preformatted(text, style_code)


# ============== CONTEUDO ==============
story = []

# ----------- CAPA -----------
story.append(Spacer(1, 4 * cm))
story.append(Paragraph("1&ordf; Entrega", style_subtitle))
story.append(Paragraph("Academico", style_title))
story.append(Paragraph(
    "Chatbot RAG para o curso de Ciencia de Dados e Machine Learning - CEUB",
    ParagraphStyle("CoverSub", parent=style_body, fontSize=13, leading=18,
                   textColor=INK_SOFT, spaceAfter=24)
))

story.append(Spacer(1, 1 * cm))

# bloco de meta-informacao
meta_data = [
    ["Autor", "Matheus Alves"],
    ["Curso", "Ciencia de Dados e Machine Learning (CDML)"],
    ["Instituicao", "CEUB - Centro Universitario de Brasilia"],
    ["Semestre", "1o semestre de 2025"],
    ["Data", "14 de maio de 2026"],
    ["Tipo", "Material de apoio para apresentacao"],
]
meta_table = Table(meta_data, colWidths=[3.5 * cm, 11 * cm])
meta_table.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
    ("TEXTCOLOR", (1, 0), (1, -1), INK),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 0),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
]))
story.append(meta_table)

story.append(Spacer(1, 3.5 * cm))
story.append(Paragraph(
    "Este documento descreve a arquitetura, capacidades e limitacoes do sistema "
    "<b>Academico</b> - um assistente conversacional construido com tecnicas de "
    "Retrieval-Augmented Generation (RAG) e consulta a banco relacional para apoiar "
    "estudantes ao longo da jornada academica.",
    ParagraphStyle("Abstract", parent=style_body, fontSize=10.5, leading=16,
                   textColor=INK_SOFT, alignment=TA_JUSTIFY,
                   leftIndent=10, rightIndent=10, borderColor=ACCENT,
                   borderWidth=0, borderPadding=10, backColor=BG_SOFT)
))

story.append(PageBreak())

# ----------- 1. VISAO GERAL -----------
story.append(Paragraph("1. Visao geral", style_h1))
story.append(p(
    "<b>Academico</b> e um chatbot que ajuda o aluno do curso de Ciencia de Dados e "
    "Machine Learning do CEUB a tirar duvidas sobre o conteudo das disciplinas e a "
    "acompanhar sua vida academica - proximas provas, prazos de entrega, notas e "
    "frequencia. O sistema combina duas tecnicas: <b>Retrieval-Augmented Generation</b> "
    "(RAG) sobre o material textual das materias e <b>consulta direta a um banco "
    "relacional</b> com os dados estruturados do aluno. Um modelo de linguagem (LLM) "
    "recebe esses dois contextos e gera respostas em linguagem natural via streaming."
))
story.append(p(
    "O objetivo desta primeira entrega e demonstrar a arquitetura completa funcionando "
    "ponta a ponta: ingestao da base de conhecimento, persistencia dos dados do aluno, "
    "busca semantica, integracao com LLM e interface web utilizavel."
))

# ----------- 2. STACK -----------
story.append(Paragraph("2. Stack tecnologica", style_h1))
stack_data = [
    ["Camada", "Tecnologia", "Funcao"],
    ["Frontend", "HTML + CSS + JS vanilla + marked.js",
     "Interface dark mode com chat em streaming"],
    ["Backend", "Python 3.10+ com Flask 3",
     "API REST (/, /api/student, /api/chat)"],
    ["Embeddings", "sentence-transformers (MiniLM 384d)",
     "Vetorizacao local da base e das queries"],
    ["Vetor store", "NumPy em memoria",
     "Busca por similaridade do cosseno"],
    ["Dados estruturados", "SQLite",
     "Aluno, disciplinas, matriculas, atividades, notas, frequencia"],
    ["LLM (chat)", "OpenRouter (gpt-4o-mini padrao)",
     "Geracao das respostas em streaming SSE"],
    ["Configuracao", "python-dotenv (.env)",
     "Chaves de API e parametros do sistema"],
]
story.append(make_table(stack_data, col_widths=[3.5 * cm, 5.5 * cm, 7.5 * cm]))

# ----------- 3. ARQUITETURA -----------
story.append(Paragraph("3. Arquitetura", style_h1))
story.append(p(
    "O sistema e construido sobre tres pilares: uma camada de recuperacao semantica "
    "(RAG) que entende o significado das perguntas, uma camada de dados estruturados "
    "que conhece o estado real do aluno, e um LLM que sintetiza ambos em uma resposta "
    "natural. O diagrama abaixo mostra o fluxo:"
))

arch = """      USUARIO
         |
         v  digita pergunta
+-----------------------+
|     index.html        |  UI dark mode, sidebar com materias,
| (browser, JS vanilla) |  chat com streaming token a token
+-----------+-----------+
            | POST /api/chat  { message, history }
            v
+-----------------------+        +------------------------+
|       app.py          |------->| embeddings.npy + chunks|  (RAG)
|      (Flask)          |        |    - NumPy em RAM      |
|                       |------->| student.db (SQLite)    |  (aluno)
| 1) embed da pergunta  |        +------------------------+
| 2) top-5 chunks (cos) |
| 3) contexto do aluno  |
| 4) chama LLM stream   |------->+------------------------+
+-----------+-----------+        |   LLM via OpenRouter   |
            |                    +------------------------+
            | Server-Sent Events
            v
  resposta em streaming"""
story.append(code_block(arch))
story.append(Paragraph("Figura 1. Fluxo arquitetural do sistema.", style_caption))

story.append(Paragraph("Fluxo detalhado de uma mensagem", style_h2))
fluxo = [
    "O frontend envia a pergunta do usuario e o historico recente para <b>/api/chat</b>.",
    "O backend gera o <b>embedding</b> da pergunta usando o modelo local de sentence-transformers.",
    "Compara o vetor da pergunta com os 62 vetores da base via produto interno em vetores normalizados (equivalente matematico a similaridade do cosseno).",
    "Seleciona os <b>5 trechos mais similares</b> com score acima de 0,20.",
    "Consulta o SQLite para montar um bloco de contexto com matriculas, proximas atividades, notas e frequencia do aluno.",
    "Monta o prompt final: <i>system prompt + dados do aluno + chunks recuperados + historico + pergunta</i>.",
    "Chama o LLM com <b>stream=True</b> e repassa os tokens ao frontend via Server-Sent Events.",
    "Ao final, envia tambem as <b>fontes consultadas</b> (arquivo, secao, score), exibidas no UI.",
]
for i, item in enumerate(fluxo, 1):
    story.append(Paragraph(f"<b>{i}.</b>&nbsp;&nbsp;{item}", style_bullet))

story.append(PageBreak())

# ----------- 4. BASE DE CONHECIMENTO -----------
story.append(Paragraph("4. Base de conhecimento", style_h1))
story.append(p(
    "A base e composta por <b>10 arquivos Markdown</b> organizados em "
    "<font face='Courier'>data/knowledge/</font>. A divisao em chunks e feita por "
    "secao do Markdown (separador <font face='Courier'>##</font>), com fallback para "
    "janela deslizante quando uma secao excede 2.200 caracteres."
))
kb_data = [
    ["Arquivo", "Conteudo", "Chunks"],
    ["institucional.md", "CEUB, curso, regras gerais, frequencia, calendario", "9"],
    ["grade-curricular.md", "Visao geral dos 7 semestres, pre-requisitos, trilhas", "10"],
    ["processos-academicos.md", "Aprovacao, trancamento, aproveitamento, TCC", "10"],
    ["disciplinas-1-semestre.md", "ALGA, BDI, BOOTI, ES, ICD, LP (detalhado)", "6"],
    ["disciplinas-2-semestre.md", "BDII, BII, CC, DCDI, FSC", "5"],
    ["disciplinas-3-semestre.md", "BDN, BOOTII, BIII, DCDII, ECD, PE", "6"],
    ["disciplinas-4-semestre.md", "AMML, FBD, OACD, RI", "4"],
    ["disciplinas-5-semestre.md", "APDL, BD NoSQL, BI, PI I", "4"],
    ["disciplinas-6-semestre.md", "APS, DS IA, PI II, VD", "4"],
    ["disciplinas-7-semestre.md", "ED, PLN, PI III, SD", "4"],
    ["TOTAL", "", "62"],
]
story.append(make_table(kb_data, col_widths=[5 * cm, 8.5 * cm, 2.5 * cm]))
story.append(p(
    "Cada chunk tem em media <b>445 caracteres</b> (minimo 32, maximo 977). Os 62 vetores "
    "formam uma matriz <font face='Courier'>62 x 384</font> que cabe em memoria sem "
    "problema - busca em milissegundos."
))

# ----------- 5. DADOS DO ALUNO -----------
story.append(Paragraph("5. Dados estruturados do aluno", style_h1))
story.append(p(
    "O banco SQLite (<font face='Courier'>data/student.db</font>) tem 6 tabelas: "
    "<b>alunos</b> (perfil), <b>disciplinas</b> (catalogo das 31 disciplinas), "
    "<b>matriculas</b> (vinculo aluno-disciplina por semestre), <b>atividades</b> "
    "(provas, trabalhos, listas, projetos com data, peso e status), <b>notas</b> "
    "(notas das atividades corrigidas) e <b>frequencia</b> (aulas dadas e faltas)."
))
story.append(Paragraph("Snapshot atual (aluno: Matheus Alves)", style_h2))
story.append(p(
    "<b>Semestre:</b> 1o &nbsp;&nbsp;&nbsp; "
    "<b>Matriculado em:</b> ALGA, BDI, BOOTI, ES, ICD, LP"
))
story.append(Paragraph("Proximas atividades pendentes:", style_h2))
atividades_data = [
    ["Data", "Tipo", "Disciplina", "Peso", "Descricao"],
    ["10/05", "LISTA", "LP", "10%", "Estruturas de repeticao (while/for)"],
    ["13/05", "PROVA", "ALGA", "40%", "P1 - Vetores, matrizes, determinantes"],
    ["15/05", "TRABALHO", "ICD", "30%", "EDA com dataset Titanic em Jupyter"],
    ["17/05", "PROVA", "BDI", "40%", "P1 - Modelagem ER e SQL basico"],
    ["20/05", "TRABALHO", "ES", "20%", "Diagrama de casos de uso"],
    ["23/05", "PROVA", "LP", "40%", "P1 - Logica e estruturas basicas"],
    ["28/05", "PROJETO", "BOOTI", "25%", "Entrega 1 - Problema + dataset"],
]
story.append(make_table(atividades_data, col_widths=[1.6 * cm, 2 * cm, 2 * cm, 1.4 * cm, 9.5 * cm]))
story.append(p(
    "<b>Frequencia:</b> alerta em <b>Engenharia de Software (ES)</b> com 16,7% de faltas - "
    "proximo do limite de 25% (que reprova por falta). Demais disciplinas dentro da margem segura."
))

story.append(PageBreak())

# ----------- 6. O QUE O CHAT RESPONDE -----------
story.append(Paragraph("6. O que o chat responde", style_h1))
story.append(p(
    "O sistema responde tres tipos de pergunta, classificados pela natureza do dado consultado. "
    "Cada categoria mostra o real valor de combinar RAG com dados estruturados."
))

# 6.1
story.append(Paragraph("6.1. Perguntas de conteudo (puro RAG)", style_h2))
story.append(p(
    "Duvidas sobre o material das disciplinas. O bot busca trechos relevantes na base "
    "de conhecimento e responde com base neles. <i>Cobre todas as 31 disciplinas do curso.</i>"
))
conteudo_data = [
    ["Pergunta do aluno", "O que o bot consulta"],
    ["Explica produto escalar com exemplo", "Trechos de ALGA"],
    ["Diferenca entre 1FN, 2FN e 3FN", "Trechos de BDI (normalizacao)"],
    ["Como funciona o CRISP-DM?", "Trechos de ICD"],
    ["O que e o metodo agil Scrum?", "Trechos de ES"],
    ["Quando vou usar calculo no curso?", "Trechos de CC, AMML, OACD"],
    ["Como funciona PCA?", "Trechos de AMML / ALGA"],
    ["O que e RAG?", "Trechos de RI / PLN (meta!)"],
]
story.append(make_table(conteudo_data, col_widths=[8 * cm, 7.5 * cm]))

# 6.2
story.append(Paragraph("6.2. Perguntas de calendario/situacao (puro SQL)", style_h2))
story.append(p(
    "Duvidas sobre o estado do aluno: provas marcadas, notas, frequencia. "
    "O bot consulta o SQLite diretamente."
))
sql_data = [
    ["Pergunta do aluno", "Resposta esperada"],
    ["Quais provas eu tenho essa semana?", "Lista P1 de ALGA (13/05) e P1 de BDI (17/05)"],
    ["Como ta minha frequencia em ES?", "4 faltas em 24 aulas (16,7%) - atencao ao limite"],
    ["Quais minhas notas ate agora?", "Lista as 6 listas corrigidas com valores"],
    ["Em quais disciplinas estou matriculado?", "Lista as 6 do 1o semestre"],
    ["Qual o peso da proxima entrega?", "Lista 3 de LP, dia 10/05, peso 10%"],
]
story.append(make_table(sql_data, col_widths=[8 * cm, 7.5 * cm]))

# 6.3
story.append(Paragraph("6.3. Perguntas hibridas (RAG + SQL)", style_h2))
story.append(p(
    "<b>Aqui o sistema mostra seu valor real.</b> O bot combina dados estruturados "
    "com conteudo da base para responder de forma personalizada - algo que nem RAG puro "
    "nem SQL puro conseguem."
))
hibrido_data = [
    ["Pergunta do aluno", "O que o bot faz"],
    ["Tenho prova de ALGA daqui 5 dias, me ajuda a revisar",
     "Confirma data via SQL; busca topicos em ALGA via RAG; monta plano de revisao"],
    ["Qual materia to pior e o que estudar?",
     "Calcula menor media via SQL; busca conteudo via RAG; sugere estudo focado"],
    ["Minha proxima prova de BDI cobre o que?",
     "SQL retorna P1 de BDI; RAG traz explicacao de ER e SQL basico"],
    ["Me da um plano de estudos pra essa semana",
     "SQL lista 7 atividades pendentes; RAG traz conteudo de cada; bot organiza cronograma"],
    ["Posso faltar amanha em ES?",
     "SQL mostra 16,7%; RAG traz regra de 25%; bot calcula e alerta"],
]
story.append(make_table(hibrido_data, col_widths=[6.5 * cm, 9 * cm]))

story.append(PageBreak())

# ----------- 7. REGRAS / SYSTEM PROMPT -----------
story.append(Paragraph("7. Comportamento do bot (system prompt)", style_h1))
story.append(p(
    "O comportamento do bot e controlado por um <b>system prompt</b> explicito - um conjunto "
    "de regras inseridas em toda chamada ao LLM antes da pergunta do usuario. Isso reduz "
    "alucinacao e mantem o tom consistente."
))
regras = [
    "<b>Anti-alucinacao:</b> baseia-se EXCLUSIVAMENTE no contexto fornecido. Se nao houver "
    "informacao suficiente, diz 'nao tenho essa informacao'.",
    "<b>Datas e notas:</b> NUNCA inventa datas, notas, prazos ou nomes de disciplinas. "
    "Sempre cita o que esta nos dados estruturados.",
    "<b>Tom:</b> portugues brasileiro, acolhedor e direto - como veterano ajudando calouro.",
    "<b>Formato:</b> markdown (negrito, listas, blocos de codigo) para clareza.",
    "<b>Especificidade:</b> sempre cita a disciplina ou data ao responder.",
    "<b>Pro-atividade:</b> alerta sobre prazos curtos, frequencia critica, notas baixas.",
    "<b>Fallback:</b> em duvida, indica procurar coordenacao ou professor.",
]
for i, r in enumerate(regras, 1):
    story.append(Paragraph(f"<b>{i}.</b>&nbsp;&nbsp;{r}", style_bullet))

# ----------- 8. FUNCIONALIDADES -----------
story.append(Paragraph("8. Funcionalidades implementadas", style_h1))
funcs = [
    "Chat web responsivo com <b>dark mode</b>",
    "Sidebar dinamica com perfil do aluno, disciplinas matriculadas e proximas atividades coloridas por urgencia (verde / amarelo / vermelho)",
    "<b>Streaming token a token</b> via Server-Sent Events - resposta aparece em tempo real",
    "Renderizacao Markdown nas respostas (listas, negrito, blocos de codigo)",
    "Indicacao visual das <b>fontes consultadas</b> (chunks de origem + score de similaridade) abaixo de cada resposta",
    "Historico de conversa mantido no frontend e enviado ao backend nas ultimas 6 mensagens",
    "<b>Prompts sugeridos</b> clicaveis na tela inicial",
    "<b>Atalhos:</b> clicar em uma disciplina ou atividade gera prompt pre-preenchido",
    "Busca vetorial em memoria com filtro de score minimo (0,20)",
    "Backend configuravel: troca de provedor LLM e modelo via <font face='Courier'>.env</font> sem mexer no codigo",
    "Suporte a <b>dois backends de embedding</b>: local (sentence-transformers) e OpenAI (text-embedding-3-small)",
]
for f in funcs:
    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{f}", style_bullet))

# ----------- 9. LIMITACOES -----------
story.append(Paragraph("9. Limitacoes conhecidas", style_h1))
story.append(p(
    "Sao limitacoes reconhecidas que <b>nao comprometem</b> a 1a entrega mas serao "
    "abordadas em iteracoes seguintes:"
))
limits = [
    "<b>Single-user:</b> todo o sistema assume um unico aluno (id=1). Multiusuario exige autenticacao e isolamento de dados.",
    "<b>Historico nao persistido:</b> as conversas so vivem na sessao do navegador. Recarregar a pagina perde o contexto.",
    "<b>Sem re-ranking:</b> a busca usa top-5 cru, sem segunda passada por LLM para reordenar. Funciona bem na base atual mas pode degradar com bases maiores.",
    "<b>Sem avaliacao automatica:</b> ainda nao ha metricas medindo qualidade do retrieval (precision@k, MRR). Material para a proxima entrega.",
    "<b>Datas codificadas no seed:</b> as atividades sao geradas com data_entrega relativa a 'hoje'. Em producao essas datas viriam do sistema academico da instituicao.",
]
for l in limits:
    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{l}", style_bullet))

story.append(PageBreak())

# ----------- 10. PROXIMOS PASSOS -----------
story.append(Paragraph("10. Proximos passos (entregas seguintes)", style_h1))
proximos = [
    "<b>Persistir conversas</b> em SQLite para manter contexto entre sessoes.",
    "Implementar <b>re-ranking</b> com o proprio LLM para melhorar precisao da busca.",
    "Adicionar conjunto de teste anotado e calcular <b>metricas de retrieval</b> (precision@k, recall@k, MRR).",
    "Comparar pelo menos 3 modelos de embedding (MiniLM, multilingual-e5-large, BGE-M3) com metricas concretas - material direto para Probabilidade e Estatistica e Aprendizagem de Maquina.",
    "Estudo de impacto da estrategia de <b>chunking</b> (por secao vs janela deslizante vs por unidade) na qualidade do retrieval.",
    "Roteamento explicito de intencao (conteudo / calendario / hibrido) com classificador.",
    "Deploy em producao (Vercel ou Render) - README ja traz as instrucoes.",
]
for i, item in enumerate(proximos, 1):
    story.append(Paragraph(f"<b>{i}.</b>&nbsp;&nbsp;{item}", style_bullet))

# ----------- 11. ESTRUTURA DE ARQUIVOS -----------
story.append(Paragraph("11. Estrutura de arquivos", style_h1))
estrutura = """.
|-- app.py                  # backend Flask (rotas /, /api/student, /api/chat)
|-- ingest.py               # gera embeddings da base de conhecimento
|-- embeddings.py           # camada de embedding (local ou OpenAI)
|-- seed_db.py              # cria e popula o SQLite do aluno
|-- requirements.txt        # dependencias Python
|-- .env                    # configuracao local (nao vai pro repositorio)
|-- .env.example            # template documentado das variaveis
|-- .gitignore
|-- README.md               # instrucoes de setup e arquitetura
|-- ESPECIFICACOES.md       # este documento em Markdown
|-- data/
|   |-- knowledge/          # 10 arquivos .md com conteudo das disciplinas
|   |-- chunks.json         # 62 chunks com texto e metadados
|   |-- embeddings.npy      # matriz NumPy 62x384 normalizada
|   '-- student.db          # banco do aluno (6 tabelas)
'-- templates/
    '-- index.html          # interface completa (CSS + JS embutidos)"""
story.append(code_block(estrutura))

# ----------- 12. EXECUCAO -----------
story.append(Paragraph("12. Como executar", style_h1))
story.append(p("Cinco comandos sequenciais. Apenas o passo 4 precisa de internet (primeiro download do modelo de embedding, 120MB)."))
exec_cmds = """python -m venv .venv
.venv\\Scripts\\activate                # Windows
pip install -r requirements.txt        # ~5-10 min na primeira vez
python seed_db.py                      # popula o banco do aluno
python ingest.py                       # baixa modelo e gera embeddings
python app.py                          # sobe em http://localhost:5000"""
story.append(code_block(exec_cmds))
story.append(p(
    "O <font face='Courier'>.env</font> ja esta configurado com a chave OpenRouter e o modelo "
    "<font face='Courier'>openai/gpt-4o-mini</font>. Para trocar de modelo (Llama 3.3 70B "
    "gratuito, Gemini Flash, Claude Haiku), basta editar a variavel "
    "<font face='Courier'>CHAT_MODEL</font>."
))

# ----------- CONTRA-CAPA -----------
story.append(PageBreak())
story.append(Spacer(1, 6 * cm))
story.append(Paragraph("Obrigado.", ParagraphStyle(
    "End", parent=style_title, fontSize=36, leading=42,
    textColor=ACCENT_DARK, alignment=TA_CENTER
)))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph(
    "Material de apoio para a apresentacao da 1a entrega.",
    ParagraphStyle("EndSub", parent=style_body, alignment=TA_CENTER,
                   textColor=MUTED, fontSize=12)
))
story.append(Spacer(1, 4 * cm))
story.append(Paragraph(
    "Matheus Alves &nbsp;&middot;&nbsp; CDML &nbsp;&middot;&nbsp; CEUB &nbsp;&middot;&nbsp; 14/05/2026",
    ParagraphStyle("EndSig", parent=style_body, alignment=TA_CENTER,
                   textColor=INK_SOFT, fontSize=10)
))


# ============== GERA O ARQUIVO ==============
doc = SimpleDocTemplate(
    "ESPECIFICACOES.pdf",
    pagesize=A4,
    leftMargin=2.4 * cm, rightMargin=2 * cm,
    topMargin=2 * cm, bottomMargin=2.2 * cm,
    title="Academico - 1a Entrega",
    author="Matheus Alves",
    subject="Especificacoes da 1a entrega - Chatbot RAG Academico",
)


# pagina 1 = capa; demais = on_page normal
def _make_callback():
    def cb(canvas_obj, doc):
        if doc.page == 1:
            on_cover(canvas_obj, doc)
        else:
            on_page(canvas_obj, doc)
    return cb


doc.build(story, onFirstPage=on_cover, onLaterPages=on_page)
print("OK: ESPECIFICACOES.pdf gerado")
