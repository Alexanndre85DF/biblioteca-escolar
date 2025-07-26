# Biblioteca Escolar - Firebase

Este projeto foi adaptado para usar Firebase Firestore como banco de dados.

## Configuração do Firebase

### 1. Configurar o Firebase Console

1. Acesse [Firebase Console](https://console.firebase.google.com/)
2. Crie um novo projeto ou use o existente
3. Ative o Firestore Database
4. Configure as regras de segurança (use o arquivo `firestore.rules`)

### 2. Baixar a Chave de Serviço

1. No Firebase Console, vá em **Configurações do Projeto** > **Contas de serviço**
2. Clique em **Gerar nova chave privada**
3. Salve o arquivo JSON como `firebase-service-account-key.json` na raiz do projeto

### 3. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com:

```
FLASK_SECRET_KEY=sua_chave_secreta_aqui
FIREBASE_SERVICE_ACCOUNT_KEY=./firebase-service-account-key.json
```

### 4. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 5. Inicializar o Firebase

```bash
python init_firebase.py
```

### 6. Executar o Projeto

```bash
python app.py
```

## Estrutura do Banco de Dados

O Firestore usa coleções e documentos:

- **usuarios**: Usuários do sistema
- **escolas**: Escolas cadastradas
- **livros**: Livros de cada escola
- **emprestimos**: Empréstimos de livros

## Credenciais do Admin

- **CPF**: 01099080150
- **Senha**: 123456
- **Tipo**: super_admin

## Funcionalidades

- ✅ Autenticação de usuários
- ✅ Gerenciamento de escolas
- ✅ Cadastro de livros
- ✅ Controle de empréstimos
- ✅ Relatórios
- ✅ Exportação para Excel
- ✅ Múltiplos usuários com dados isolados

## Deploy no Render

1. Configure as variáveis de ambiente no Render
2. Faça upload do arquivo `firebase-service-account-key.json`
3. Configure o build command e start command
4. Deploy!

## Regras de Segurança

As regras do Firestore garantem que:
- Cada usuário só acesse seus próprios dados
- Super admin pode acessar todos os dados
- Dados são protegidos por autenticação 