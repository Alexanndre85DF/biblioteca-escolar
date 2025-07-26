import hashlib
from firebase_config import get_firestore_db

def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def init_firebase():
    db = get_firestore_db()
    
    # Criar usuário administrador padrão
    admin_data = {
        'cpf': '01099080150',
        'senha': criptografar_senha('123456'),
        'tipo_usuario': 'super_admin',
        'nome': 'Administrador Geral'
    }
    
    # Verificar se o admin já existe
    admin_doc = db.collection('usuarios').document('01099080150').get()
    if not admin_doc.exists:
        db.collection('usuarios').document('01099080150').set(admin_data)
        print("Usuário administrador criado com sucesso!")
        print("CPF: 01099080150")
        print("Senha: 123456")
    else:
        print("Usuário administrador já existe!")
    
    print("Firebase inicializado com sucesso!")

if __name__ == '__main__':
    init_firebase() 