import sqlite3
import hashlib
import os

def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def init_db():
    # Conecta ao banco de dados (cria se não existir)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Cria tabela de escolas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS escolas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        endereco TEXT,
        telefone TEXT
    )
    ''')

    # Cria tabela de usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        cpf TEXT PRIMARY KEY,
        senha TEXT NOT NULL,
        escola_id INTEGER,
        tipo_usuario TEXT DEFAULT 'normal',
        FOREIGN KEY (escola_id) REFERENCES escolas (id)
    )
    ''')

    # Cria tabela de livros
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS livros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        autor TEXT NOT NULL,
        editora TEXT,
        ano TEXT,
        categoria TEXT,
        quantidade INTEGER DEFAULT 0,
        localizacao TEXT,
        codigo_interno TEXT,
        observacoes TEXT,
        disponivel INTEGER DEFAULT 1,
        escola_id INTEGER,
        FOREIGN KEY (escola_id) REFERENCES escolas (id)
    )
    ''')

    # Cria tabela de empréstimos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS emprestimos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aluno TEXT NOT NULL,
        turma TEXT NOT NULL,
        telefone TEXT,
        livro_id INTEGER,
        data_emprestimo DATE NOT NULL,
        data_devolucao DATE NOT NULL,
        data_devolvido DATE,
        escola_id INTEGER,
        FOREIGN KEY (livro_id) REFERENCES livros (id),
        FOREIGN KEY (escola_id) REFERENCES escolas (id)
    )
    ''')

    # Insere o usuário super_admin se não existir
    cursor.execute('''
    INSERT OR IGNORE INTO usuarios (cpf, senha, tipo_usuario)
    VALUES (?, ?, ?)
    ''', ('73383058115', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'super_admin'))
    # A senha acima é '123456' criptografada em SHA-256

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Banco de dados inicializado com sucesso!") 
