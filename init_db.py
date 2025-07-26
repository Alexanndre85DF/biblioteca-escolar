import psycopg2
from psycopg2.extras import DictCursor
import hashlib
import os

def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def init_db():
    from urllib.parse import urlparse
    import ssl

    # Obtém a URL do banco do ambiente
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL is None:
        raise Exception("DATABASE_URL não configurado!")

    # Conecta ao PostgreSQL
    conn = psycopg2.connect(DATABASE_URL, sslmode='require', cursor_factory=DictCursor)
    cursor = conn.cursor()

    # Tabelas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS escolas (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        endereco TEXT,
        telefone TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        cpf TEXT PRIMARY KEY,
        senha TEXT NOT NULL,
        escola_id INTEGER,
        tipo_usuario TEXT DEFAULT 'normal',
        FOREIGN KEY (escola_id) REFERENCES escolas(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS livros (
        id SERIAL PRIMARY KEY,
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
        FOREIGN KEY (escola_id) REFERENCES escolas(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS emprestimos (
        id SERIAL PRIMARY KEY,
        aluno TEXT NOT NULL,
        turma TEXT NOT NULL,
        telefone TEXT,
        livro_id INTEGER,
        data_emprestimo DATE NOT NULL,
        data_devolucao DATE NOT NULL,
        data_devolvido DATE,
        escola_id INTEGER,
        FOREIGN KEY (livro_id) REFERENCES livros(id),
        FOREIGN KEY (escola_id) REFERENCES escolas(id)
    )
    ''')

    # Usuário administrador padrão
    cursor.execute('''
    INSERT INTO usuarios (cpf, senha, tipo_usuario)
    VALUES (%s, %s, %s)
    ON CONFLICT (cpf) DO NOTHING
    ''', (
        '73383058115',
        '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92',  # senha 123456
        'super_admin'
    ))

    conn.commit()
    conn.close()
    print("Banco de dados PostgreSQL inicializado com sucesso!")

if __name__ == '__main__':
    init_db()
