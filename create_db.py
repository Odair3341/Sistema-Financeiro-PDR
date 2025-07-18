from app import app, db
from sqlalchemy import inspect

print("Iniciando create_db.py...")

with app.app_context():
    print("Dentro do contexto da aplicação.")
    # db.drop_all() foi comentado para evitar a perda de dados em cada execução.
    # Se precisar apagar todas as tabelas para um novo início, descomente a linha abaixo.
    # print("Tentando apagar todas as tabelas existentes (db.drop_all())...")
    # db.drop_all()
    # print("db.drop_all() executado.")
    print("Tentando criar todas as tabelas (db.create_all())...")
    db.create_all()
    print("db.create_all() executado. Verificando tabelas...")

    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    print(f"Tabelas existentes após create_all(): {existing_tables}")

    # Opcional: Verificar o tipo de coluna de uma tabela específica
    if "servico" in existing_tables:
        columns = inspector.get_columns('servico')
        for col in columns:
            if col['name'] == 'id':
                print(f"Tipo da coluna 'id' na tabela 'servico': {col['type']}")

    # Explicitamente descartar o engine para limpar o pool de conexões
    db.engine.dispose()
    print("db.engine.dispose() executado para limpar o pool de conexões.")

print("create_db.py finalizado.")