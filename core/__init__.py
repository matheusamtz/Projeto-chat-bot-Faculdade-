"""Pacote core do Academico - logica de dominio separada do servidor.

Modulos:
  chunking         - quebra dos .md em chunks por secao
  embeddings       - backends de embedding (local/openai)
  vector_store     - busca vetorial em memoria com numpy
  student_data     - acesso ao SQLite com dados do aluno
  intent_classifier- classificador de intencao da pergunta
  llm              - wrapper do cliente OpenAI-compatible
"""
