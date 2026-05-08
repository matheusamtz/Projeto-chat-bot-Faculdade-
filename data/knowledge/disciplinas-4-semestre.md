# Disciplinas do 4º Semestre

## AMML — Aprendizagem de Máquina (Machine Learning)
Carga: 75h. Pré-req: IA. Disciplina central do curso. Aprendizado supervisionado: regressão linear e logística, k-Nearest Neighbors, árvores de decisão, Random Forest, Gradient Boosting (XGBoost, LightGBM), SVM. Aprendizado não supervisionado: k-Means, DBSCAN, hierárquico, PCA, t-SNE. Métricas: acurácia, precisão, recall, F1, AUC-ROC, MAE, MSE, R². Validação cruzada, overfitting/underfitting, regularização (L1, L2), trade-off viés-variância, feature engineering. Ferramenta principal: scikit-learn. Avaliação: provas + projeto final com dataset real, modelagem completa com baseline, modelo principal e comparação por métricas.

## FBD — Fundamentos de Big Data
Carga: 75h. Sem pré-requisito. Conceitos: 5Vs do Big Data (volume, velocidade, variedade, veracidade, valor), arquiteturas distribuídas, Hadoop (HDFS, MapReduce), Apache Spark (RDDs, DataFrames, PySpark), processamento em batch vs streaming, Apache Kafka (introdução), introdução a serviços em nuvem (AWS S3, EMR, Athena; GCP BigQuery; Azure). Trabalho prático: pipeline em PySpark sobre dataset volumoso. Importância: cientistas de dados em empresas grandes lidam com bilhões de linhas — Pandas em uma máquina não dá conta.

## OACD — Otimização Aplicada à Ciência de Dados
Carga: 75h. Sem pré-requisito formal. Programação linear, programação inteira, métodos de otimização contínua, gradiente descendente (batch, estocástico, mini-batch), Adam, otimização convexa, problemas de classificação como otimização, Lagrangianos. Aplicação direta: muito do treinamento de modelos de ML é otimização. Solver: scipy.optimize, CVXPY, e Linear Programming com PuLP.

## RI — Recuperação da Informação
Carga: 75h. Sem pré-requisito. Disciplina diretamente relacionada a sistemas como RAG e mecanismos de busca. Modelo booleano, modelo vetorial (TF-IDF, similaridade do cosseno), BM25, indexação invertida, tokenização e normalização (stopwords, stemming, lematização), avaliação de sistemas de busca (precision@k, recall, MAP, MRR, nDCG), expansão de consulta, ranking, introdução a embeddings densos e busca semântica. Útil para entender por baixo dos panos como funciona um chatbot RAG. Trabalho prático: construir um motor de busca sobre uma coleção de documentos.
