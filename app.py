from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import hashlib
import io
import pandas as pd
from flask import make_response
import os
from dotenv import load_dotenv
from firebase_config import get_firestore_db
from firebase_admin import auth
import uuid
from datetime import datetime

# Carrega as variáveis de ambiente
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'biblioteca_secret_key')

# Obter instância do Firestore
db = get_firestore_db()

# Função para criptografar senhas
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# Função para obter documento por ID
def get_document_by_id(collection, doc_id):
    doc = db.collection(collection).document(doc_id).get()
    if doc.exists:
        return {'id': doc.id, **doc.to_dict()}
    return None

# Função para obter todos os documentos de uma coleção
def get_all_documents(collection, user_id=None):
    if user_id:
        docs = db.collection(collection).where('user_id', '==', user_id).stream()
    else:
        docs = db.collection(collection).stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]

# Função para buscar usuário por CPF
def get_user_by_cpf(cpf):
    users = db.collection('usuarios').where('cpf', '==', cpf).stream()
    user = next(users, None)
    if user:
        return {'id': user.id, **user.to_dict()}
    return None

# Função para adicionar documento
def add_document(collection, data):
    doc_ref = db.collection(collection).add(data)
    return doc_ref[1].id

# Função para atualizar documento
def update_document(collection, doc_id, data):
    db.collection(collection).document(doc_id).update(data)

# Função para deletar documento
def delete_document(collection, doc_id):
    db.collection(collection).document(doc_id).delete()

# Página de login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cpf = request.form['cpf']
        senha = request.form['senha']
        senha_criptografada = criptografar_senha(senha)

        # Busca o usuário no Firestore
        user = get_user_by_cpf(cpf)

        if user and user['senha'] == senha_criptografada:
            session['usuario_cpf'] = user['cpf']
            session['tipo_usuario'] = user['tipo_usuario']
            
            if user['tipo_usuario'] == 'super_admin':
                flash('Bem-vindo Administrador Geral!', 'success')
            else:
                # Buscar dados da escola se não for super admin
                if 'escola_id' in user:
                    escola = get_document_by_id('escolas', user['escola_id'])
                    if escola:
                        session['escola_id'] = escola['id']
                        session['escola_nome'] = escola['nome']
                        flash(f'Bem-vindo! Você está conectado à {escola["nome"]}', 'success')
                    else:
                        flash('Escola não encontrada!', 'error')
                        return render_template('login.html')
                else:
                    flash('Usuário sem escola associada!', 'error')
                    return render_template('login.html')
            
            return redirect(url_for('index'))
        else:
            flash('CPF ou Senha inválidos!')

    return render_template('login.html')

# Tela inicial depois de logado
@app.route('/index')
def index():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', usuario_cpf=session['usuario_cpf'])

# Tela de cadastro de novos usuários
@app.route('/cadastro_usuario', methods=['GET', 'POST'])
def cadastro_usuario():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        cpf = request.form['cpf']
        senha = request.form['senha']
        senha_criptografada = criptografar_senha(senha)
        
        # Verifica se o CPF já existe
        if get_user_by_cpf(cpf):
            flash('CPF já cadastrado!')
        else:
            data = {
                'cpf': cpf,
                'senha': senha_criptografada,
                'tipo_usuario': 'usuario_normal' # Default para usuário normal
            }
            # Usar CPF como ID do documento
            db.collection('usuarios').document(cpf).set(data)
            flash('Usuário cadastrado com sucesso!')

    
    return render_template('cadastro_usuario.html', usuario_cpf=session.get('usuario_cpf'))


# Tela de alterar senha
@app.route('/alterar_senha', methods=['GET', 'POST'])
def alterar_senha():
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')

        # Remove formatação do CPF
        if cpf:
            cpf = cpf.replace('.', '').replace('-', '')

        # Se o CPF e senha atual foram fornecidos, verifica as credenciais
        if cpf and senha_atual and not nova_senha:
            senha_atual_criptografada = criptografar_senha(senha_atual)
            
            user = get_user_by_cpf(cpf)

            if user and user['senha'] == senha_atual_criptografada:
                session['temp_cpf'] = cpf  # Armazena o CPF temporariamente
                flash('Credenciais verificadas. Por favor, digite sua nova senha.', 'success')
                return render_template('alterar_senha.html', verificado=True)
            else:
                flash('CPF ou senha atual incorretos.')
                return render_template('alterar_senha.html', verificado=False)

        # Se a nova senha foi fornecida, processa a alteração
        elif nova_senha and confirmar_senha and 'temp_cpf' in session:
            if nova_senha == confirmar_senha:
                nova_senha_criptografada = criptografar_senha(nova_senha)
                db.collection('usuarios').document(session['temp_cpf']).update({'senha': nova_senha_criptografada})
                
                session.pop('temp_cpf', None)  # Remove o CPF temporário
                flash('Senha alterada com sucesso!', 'success')
                return redirect(url_for('index'))
            else:
                flash('A nova senha e a confirmação não coincidem.')
                return render_template('alterar_senha.html', verificado=True)

    return render_template('alterar_senha.html', verificado=False)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Cadastro e listagem de livros
@app.route('/livros', methods=['GET', 'POST'])
def livros():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    # Verifica se é super admin ou tem escola associada
    if session.get('tipo_usuario') == 'super_admin':
        user_escola_id = None  # Super admin pode ver todos os livros
    else:
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para gerenciar livros nesta escola.', 'error')
            return redirect(url_for('index'))

    if request.method == 'POST':
        # Obtém os campos obrigatórios
        titulo = request.form['titulo']
        autor = request.form['autor']
        
        # Obtém os campos opcionais com valores padrão
        editora = request.form.get('editora', '')
        ano = request.form.get('ano', '')
        categoria = request.form.get('categoria', '')
        quantidade = request.form.get('quantidade', '0')
        localizacao = request.form.get('localizacao', '')
        codigo_interno = request.form.get('codigo_interno', '')
        observacoes = request.form.get('observacoes', '')

        # Converte quantidade para número se estiver vazio
        if quantidade == '':
            quantidade = '0'

        data = {
            'titulo': titulo,
            'autor': autor,
            'editora': editora,
            'ano': ano,
            'categoria': categoria,
            'quantidade': int(quantidade),
            'localizacao': localizacao,
            'codigo_interno': codigo_interno,
            'observacoes': observacoes,
            'disponivel': True,
            'escola_id': user_escola_id
        }
        
        add_document('livros', data)
        flash('Livro cadastrado com sucesso!', 'success')
        return redirect(url_for('livros'))

    # Busca os livros
    if session.get('tipo_usuario') == 'super_admin':
        # Super admin vê todos os livros
        livros_data = get_all_documents('livros')
    else:
        # Usuário normal vê apenas livros da sua escola
        livros_data = get_all_documents('livros')
        livros_data = [livro for livro in livros_data if livro.get('escola_id') == user_escola_id]
    
    return render_template('livros.html', livros=livros_data, usuario_cpf=session['usuario_cpf'])

# Excluir livro
@app.route('/excluir_livro/<doc_id>')
def excluir_livro(doc_id):
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    # Verifica permissão
    if session.get('tipo_usuario') != 'super_admin':
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para excluir livros nesta escola.', 'error')
            return redirect(url_for('index'))

        # Verifica se o livro pertence à escola do usuário
        livro = get_document_by_id('livros', doc_id)
        if not livro or livro.get('escola_id') != user_escola_id:
            flash('Acesso não autorizado ao livro.', 'error')
            return redirect(url_for('livros'))

    delete_document('livros', doc_id)
    return redirect(url_for('livros'))

# Cadastro e listagem de empréstimos
@app.route('/emprestimos', methods=['GET', 'POST'])
def emprestimos():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    # Verifica se é super admin ou tem escola associada
    if session.get('tipo_usuario') == 'super_admin':
        user_escola_id = None  # Super admin pode ver todos os empréstimos
    else:
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para gerenciar empréstimos nesta escola.', 'error')
            return redirect(url_for('index'))

    if request.method == 'POST':
        # Obtém os campos do formulário
        aluno = request.form['aluno']
        turma = request.form['turma']
        telefone = request.form.get('telefone', '')
        livro_id = request.form['livro_id']
        data_emprestimo = request.form['data_emprestimo']
        data_devolucao = request.form['data_devolucao']

        # Insere o empréstimo
        data = {
            'aluno': aluno,
            'turma': turma,
            'telefone': telefone,
            'livro_id': livro_id,
            'data_emprestimo': datetime.strptime(data_emprestimo, '%Y-%m-%d').isoformat(),
            'data_devolucao': datetime.strptime(data_devolucao, '%Y-%m-%d').isoformat(),
            'escola_id': user_escola_id
        }
        emprestimo_id = add_document('emprestimos', data)
        
        # Atualiza o status do livro para indisponível
        livro = get_document_by_id('livros', livro_id)
        if livro:
            update_document('livros', livro_id, {'disponivel': False})

        flash('Empréstimo cadastrado com sucesso!', 'success')
        return redirect(url_for('emprestimos'))

    # Busca os empréstimos
    if session.get('tipo_usuario') == 'super_admin':
        # Super admin vê todos os empréstimos
        emprestimos_data = get_all_documents('emprestimos')
    else:
        # Usuário normal vê apenas empréstimos da sua escola
        emprestimos_data = get_all_documents('emprestimos')
        emprestimos_data = [emp for emp in emprestimos_data if emp.get('escola_id') == user_escola_id]

    # Busca os livros disponíveis para o formulário
    if session.get('tipo_usuario') == 'super_admin':
        livros_disponiveis = get_all_documents('livros')
    else:
        livros_disponiveis = get_all_documents('livros')
        livros_disponiveis = [livro for livro in livros_disponiveis if livro.get('escola_id') == user_escola_id]

    return render_template('emprestimos.html', emprestimos=emprestimos_data, livros=livros_disponiveis, usuario_cpf=session['usuario_cpf'])

# Baixar empréstimo (devolução)
@app.route('/baixar_emprestimo/<doc_id>', methods=['POST'])
def baixar_emprestimo(doc_id):
    # Verifica se o usuário está logado
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    # Verifica permissão
    if session.get('tipo_usuario') != 'super_admin':
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para baixar empréstimos nesta escola.', 'error')
            return redirect(url_for('emprestimos'))

        # Busca o empréstimo
        emprestimo = get_document_by_id('emprestimos', doc_id)

        # Verifica se o empréstimo existe e pertence à escola logada
        if not emprestimo or emprestimo.get('escola_id') != user_escola_id:
            flash('Acesso não autorizado ao empréstimo.', 'error')
            return redirect(url_for('emprestimos'))
    else:
        emprestimo = get_document_by_id('emprestimos', doc_id)
        if not emprestimo:
            flash('Empréstimo não encontrado.', 'error')
            return redirect(url_for('emprestimos'))

    # Continua o processo de devolução
    data_devolvido = request.form['data_devolvido']

    update_document('emprestimos', doc_id, {'data_devolvido': datetime.strptime(data_devolvido, '%Y-%m-%d').isoformat()})
    update_document('livros', emprestimo['livro_id'], {'disponivel': True})

    flash('Empréstimo baixado com sucesso!', 'success')
    return redirect(url_for('emprestimos'))


# Excluir empréstimo
@app.route('/excluir_emprestimo/<doc_id>')
def excluir_emprestimo(doc_id):
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    # Verifica permissão
    if session.get('tipo_usuario') != 'super_admin':
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para excluir empréstimos nesta escola.', 'error')
            return redirect(url_for('emprestimos'))

        # Verifica se o empréstimo pertence à escola do usuário
        emprestimo = get_document_by_id('emprestimos', doc_id)
        if not emprestimo or emprestimo.get('escola_id') != user_escola_id:
            flash('Acesso não autorizado ao empréstimo.', 'error')
            return redirect(url_for('emprestimos'))

    delete_document('emprestimos', doc_id)
    return redirect(url_for('emprestimos'))

# Tela de relatórios principal
@app.route('/relatorios')
def relatorios():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
    return render_template('relatorios.html', usuario_cpf=session['usuario_cpf'])

# Relatório de livros
@app.route('/relatorios/livros')
def livros_relatorio():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    # Busca os livros
    if session.get('tipo_usuario') == 'super_admin':
        livros_data = get_all_documents('livros')
    else:
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para ver relatórios de livros nesta escola.', 'error')
            return redirect(url_for('index'))
        
        livros_data = get_all_documents('livros')
        livros_data = [livro for livro in livros_data if livro.get('escola_id') == user_escola_id]
    return render_template('livros_relatorio.html', livros=livros_data, usuario_cpf=session['usuario_cpf'])

# Gerenciar escolas
@app.route('/gerenciar_escolas')
def gerenciar_escolas():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
        
    if session.get('tipo_usuario') != 'super_admin':
        flash('Apenas o administrador geral pode gerenciar escolas!', 'error')
        return redirect(url_for('index'))
        
    escolas = get_all_documents('escolas')
    
    return render_template('gerenciar_escolas.html', escolas=escolas)

# Gerenciar usuários
@app.route('/gerenciar_usuarios')
def gerenciar_usuarios():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
        
    if session.get('tipo_usuario') != 'super_admin':
        flash('Apenas o administrador geral pode gerenciar usuários!', 'error')
        return redirect(url_for('index'))
        
    usuarios = get_all_documents('usuarios')
    
    return render_template('gerenciar_usuarios.html', usuarios=usuarios)

# Excluir usuário
@app.route('/excluir_usuario/<cpf>')
def excluir_usuario(cpf):
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
        
    if session.get('tipo_usuario') != 'super_admin':
        flash('Apenas o administrador geral pode excluir usuários!', 'error')
        return redirect(url_for('index'))
        
        user = get_user_by_cpf(cpf)
    if not user:
        flash('Usuário não encontrado!', 'error')
        return redirect(url_for('index'))
        
    # Não permite excluir o super admin
    if user['tipo_usuario'] == 'super_admin':
        flash('Não é possível excluir o administrador geral!', 'error')
        return redirect(url_for('index'))
        
    db.collection('usuarios').document(cpf).delete()
    flash('Usuário excluído com sucesso!', 'success')
        
    return redirect(url_for('gerenciar_usuarios'))

# Excluir escola
@app.route('/excluir_escola/<doc_id>')
def excluir_escola(doc_id):
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
        
    if session.get('tipo_usuario') != 'super_admin':
        flash('Apenas o administrador geral pode excluir escolas!', 'error')
        return redirect(url_for('index'))
        
        escola = get_document_by_id('escolas', doc_id)
    if not escola:
        flash('Escola não encontrada!', 'error')
        return redirect(url_for('index'))
        
    # Exclui todos os usuários da escola
    usuarios = get_all_documents('usuarios')
    for usuario in usuarios:
        if usuario.get('escola_id') == doc_id:
            db.collection('usuarios').document(usuario['id']).delete()
    
    # Exclui todos os livros da escola
    livros = get_all_documents('livros')
    for livro in livros:
        if livro.get('escola_id') == doc_id:
            db.collection('livros').document(livro['id']).delete()
    
    # Exclui todos os empréstimos da escola
    emprestimos = get_all_documents('emprestimos')
    for emprestimo in emprestimos:
        if emprestimo.get('escola_id') == doc_id:
            db.collection('emprestimos').document(emprestimo['id']).delete()
    
    db.collection('escolas').document(doc_id).delete()
        
    flash('Escola e todos os seus dados foram excluídos com sucesso!', 'success')
        
    return redirect(url_for('gerenciar_escolas'))

@app.route('/exportar_livros_excel')
def exportar_livros_excel():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
    
    # Busca os livros
    if session.get('tipo_usuario') == 'super_admin':
        livros_data = get_all_documents('livros')
    else:
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para exportar livros nesta escola.', 'error')
            return redirect(url_for('index'))
        
        livros_data = get_all_documents('livros')
        livros_data = [livro for livro in livros_data if livro.get('escola_id') == user_escola_id]
    df = pd.DataFrame(livros_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Livros')
    output.seek(0)
    return send_file(output, download_name='livros.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/emprestimos_curso')
def emprestimos_curso():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
    
    # Busca os empréstimos
    if session.get('tipo_usuario') == 'super_admin':
        emprestimos_data = get_all_documents('emprestimos')
    else:
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para ver empréstimos em curso nesta escola.', 'error')
            return redirect(url_for('index'))
        
        emprestimos_data = get_all_documents('emprestimos')
        emprestimos_data = [emp for emp in emprestimos_data if emp.get('escola_id') == user_escola_id]
    return render_template('emprestimos_curso.html', emprestimos=emprestimos_data, usuario_cpf=session['usuario_cpf'])

@app.route('/emprestimos_devolvidos')
def emprestimos_devolvidos():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
    
    # Busca os empréstimos
    if session.get('tipo_usuario') == 'super_admin':
        emprestimos_data = get_all_documents('emprestimos')
    else:
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para ver empréstimos devolvidos nesta escola.', 'error')
            return redirect(url_for('index'))
        
        emprestimos_data = get_all_documents('emprestimos')
        emprestimos_data = [emp for emp in emprestimos_data if emp.get('escola_id') == user_escola_id]
    return render_template('emprestimos_devolvidos.html', emprestimos=emprestimos_data, usuario_cpf=session['usuario_cpf'])

@app.route('/exportar_emprestimos_curso_excel')
def exportar_emprestimos_curso_excel():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
    
    # Busca os empréstimos
    if session.get('tipo_usuario') == 'super_admin':
        emprestimos_data = get_all_documents('emprestimos')
    else:
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para exportar empréstimos em curso nesta escola.', 'error')
            return redirect(url_for('index'))
        
        emprestimos_data = get_all_documents('emprestimos')
        emprestimos_data = [emp for emp in emprestimos_data if emp.get('escola_id') == user_escola_id]
    df = pd.DataFrame(emprestimos_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Empréstimos em Curso')
    output.seek(0)
    return send_file(output, download_name='emprestimos_curso.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/exportar_emprestimos_devolvidos_excel')
def exportar_emprestimos_devolvidos_excel():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
    
    # Busca os empréstimos
    if session.get('tipo_usuario') == 'super_admin':
        emprestimos_data = get_all_documents('emprestimos')
    else:
        user_escola_id = session.get('escola_id')
        if not user_escola_id:
            flash('Você não tem permissão para exportar empréstimos devolvidos nesta escola.', 'error')
            return redirect(url_for('index'))
        
        emprestimos_data = get_all_documents('emprestimos')
        emprestimos_data = [emp for emp in emprestimos_data if emp.get('escola_id') == user_escola_id]
    df = pd.DataFrame(emprestimos_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Empréstimos Devolvidos')
    output.seek(0)
    return send_file(output, download_name='emprestimos_devolvidos.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Rodar o servidor
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
