# 💎 ControlWise

Sistema de gestão de produtos, estoque, custos e fornecedores desenvolvido em **Python + Streamlit**, com **Supabase** como camada de persistência de dados e armazenamento de imagens.

O ControlWise centraliza o cadastro de produtos e automatiza o acompanhamento de estoque, custos de aquisição, custos de banho/acabamento, preços de venda, margens de lucro e fornecedores — funcionando como uma plataforma de gestão operacional e financeira.

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-funcionalidades)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Arquitetura](#-arquitetura)
- [Modelo de Cálculo do Banho](#-modelo-de-cálculo-do-banho)
- [Cálculo Financeiro](#-cálculo-financeiro)
- [Exportação de Dados](#-exportação-de-dados)
- [Tratamento de Dados e Erros](#-tratamento-de-dados-e-erros)
- [Objetivo do Projeto](#-objetivo-do-projeto)

---

## 🔎 Visão Geral

O sistema é dividido em dois grandes módulos, integrados entre si:

| Módulo | Descrição |
|---|---|
| **Catálogo de Produtos** | Cadastro, edição, exclusão, imagens, filtros, ordenação e métricas financeiras de estoque |
| **Fornecedores de Banho** | Cadastro de fornecedores, preços por grama e classificações de banho/acabamento |

A relação entre os módulos permite que o custo do banho de cada produto seja **calculado e atualizado automaticamente** conforme os preços cadastrados na tabela de fornecedores.

---

## ✨ Funcionalidades

### 🗂️ Catálogo de Produtos
- Listagem completa em tabela (foto, ID, nome, categoria, gênero, estoque, peso, metal, preços, lucro, fornecedor, banho, datas etc.)
- Cadastro de novos produtos com identificação, estoque, valores, fornecedor e dados de banho (opcional)
- Edição com detecção de campos alterados — evita updates desnecessários no Supabase
- Exclusão com zona de perigo, confirmação e remoção automática das imagens associadas

### 🖼️ Gerenciamento de Fotos
- Upload de imagens (JPG, JPEG, PNG, WebP) até **10 MB**
- Editor de recorte integrado com proporção **1:1** (mínimo 500×500 px)
- Geração automática de imagem principal (`800×800`) e miniatura (`200×200`) em **WebP**
- Substituição e exclusão de imagem independente da exclusão do produto
- Visualização ampliada da imagem principal

### 🧪 Sistema de Custos de Banho
- Cálculo automático: **Peso × Preço por grama**
- Busca da combinação **Fornecedor + Metal + Classificação**
- Alerta quando não existe preço cadastrado para a combinação
- Atualização automática do custo do banho quando o preço do fornecedor é alterado

### 💰 Cálculo Financeiro
- Simulação de custo total, lucro e margem antes de salvar o produto
- Invalidação automática da simulação quando algum valor é alterado

### ✅ Validações
- Regras obrigatórias para nome, categoria, estoque, peso, preços e banho
- Preço de venda não pode ser menor que o custo total
- Validação de conjunto completo dos dados de banho (fornecedor + metal + classificação)

### 🔍 Filtros e Ordenação
- Busca geral por nome, ID, categoria e fornecedor
- Filtros de texto (categoria, gênero, metal, fornecedor, banho)
- Filtros numéricos por intervalo (preços, custo do banho, lucro, estoque, peso, classificação)
- Filtro por período de cadastro
- Ordenação por 14 critérios diferentes, crescente ou decrescente

### 📊 Métricas do Estoque
- Produtos encontrados e unidades em estoque
- Custo somado, valor de venda somado e lucro somado do subconjunto filtrado

### 🏭 Fornecedores de Banho
- Cadastro, edição e exclusão de fornecedores
- Cadastro de preços por combinação Fornecedor + Metal + Classificação (1 a 20)
- Proteção contra combinações duplicadas (comparação de metal case-insensitive)
- Confirmação pós-exclusão consultando o Supabase para garantir consistência

### 📤 Exportação
- Exportação de produtos, fornecedores e preços para CSV (UTF-8, separador `;`, decimal `,`, datas em formato brasileiro)

### ⚙️ Infraestrutura da Aplicação
- Seletores dependentes (fornecedor → metal → classificação → preço)
- Cache de dados e recursos via Streamlit (`st.cache_data`, `st.cache_resource`)
- Botão de atualização manual que limpa cache e reconstrói as tabelas
- Controle de estado da interface via `st.session_state`
- Feedback visual de sucesso, aviso e erro
- Tratamento de falhas parciais (ex: produto salvo, mas foto não enviada)

---

## 🛠️ Tecnologias Utilizadas

| Camada | Tecnologia |
|---|---|
| Backend / Lógica | Python |
| Interface | Streamlit |
| Banco de Dados | Supabase |
| Manipulação de Dados | Pandas |
| Processamento de Imagens | Pillow |
| Editor de Recorte | streamlit-cropper |
| Armazenamento de Imagens | Supabase Storage |

---

## 🏗️ Arquitetura

O projeto segue uma arquitetura em camadas, separando interface, regras de negócio e acesso a dados:

```
Interface
    ↓
Features
    ↓
Regras de negócio
    ↓
Services
    ↓
Supabase
```

Estrutura de pastas:

```
pages/
    product_catalog.py
    plating_suppliers.py

src/
    features/
        products/
        plating/

    shared/

    services/
        supabase.py

ui/
    styles.py
```

Essa separação evita concentrar toda a lógica do sistema diretamente nos arquivos das páginas, facilitando manutenção e evolução do projeto.

---

## 🧮 Modelo de Cálculo do Banho

O custo do banho segue a cadeia:

```
Produto → Fornecedor de banho → Metal → Classificação → Preço por grama
```

**Fórmula:**

```
Custo do banho = Peso da peça × Preço do banho por grama
```

**Exemplo:**

```
Peso: 5 g
Preço do banho: R$ 3,00/g
Custo do banho: 5 × 3 = R$ 15,00
```

Se nenhum dado de banho for informado, o custo é `R$ 0,00`. Caso qualquer campo seja preenchido, o conjunto completo (fornecedor, metal e classificação) passa a ser obrigatório.

---

## 💵 Cálculo Financeiro

| Métrica | Fórmula |
|---|---|
| Custo total | Preço de compra + Custo do banho |
| Lucro estimado | Preço de venda − Preço de compra − Custo do banho |
| Margem estimada | (Lucro ÷ Preço de venda) × 100 |

---

## 📁 Exportação de Dados

| Dado | Arquivo gerado |
|---|---|
| Produtos | `produtos_controlwise.csv` |
| Fornecedores | `fornecedores_wisecontrol.csv` |
| Preços de banho | `precos_banho_wisecontrol.csv` |

Todos os arquivos usam encoding UTF-8, separador `;`, decimal `,` e datas no padrão brasileiro.

---

## 🧹 Tratamento de Dados e Erros

- Normalização de preços, quantidades, classificações, datas e textos vindos do Supabase
- Comparação de metais case-insensitive para evitar duplicidade
- Conversão de datas para o fuso `America/Sao_Paulo`, exibidas no formato `dd/mm/aaaa hh:mm`
- Tratamento de falhas secundárias (ex: exclusão de produto bem-sucedida mesmo se a remoção da imagem falhar)
- Mensagens claras de sucesso, aviso e erro para todas as operações críticas

---

## 🎯 Objetivo do Projeto

O ControlWise tem como objetivo evoluir para uma **plataforma centralizada de gestão operacional e financeira**, permitindo acompanhar produtos, estoque, fornecedores e custos em um único ambiente. Sua arquitetura modular permite adicionar novas funcionalidades progressivamente, sem concentrar a lógica de negócio nas páginas da aplicação.

---

<p align="center">Desenvolvido por Rodrigo Gomes</p>
