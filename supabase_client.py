import os
from supabase import create_client, Client

# Função para carregar as variáveis - primeiro do ambiente, depois do arquivo
def get_env_vars(env_file="token.env"):
    vars = {}
    
    # Primeiro, tenta pegar do ambiente (Railway/Vercel)
    if os.environ.get("SUPABASE_URL"):
        vars["SUPABASE_URL"] = os.environ.get("SUPABASE_URL")
    if os.environ.get("SUPABASE_KEY"):
        vars["SUPABASE_KEY"] = os.environ.get("SUPABASE_KEY")
    if os.environ.get("DISCORD_TOKEN"):
        vars["DISCORD_TOKEN"] = os.environ.get("DISCORD_TOKEN")
    
    # Se não tiver do ambiente, tenta do arquivo
    if not vars.get("SUPABASE_URL"):
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        vars[key] = value
        except FileNotFoundError:
            if not vars.get("SUPABASE_URL"):
                print(f"Arquivo de ambiente {env_file} não encontrado.")
    
    return vars

# Carrega as variáveis e inicializa o cliente Supabase
env_vars = get_env_vars()

url = env_vars.get("SUPABASE_URL")
key = env_vars.get("SUPABASE_KEY")

supabase: Client = None
if url and key:
    supabase = create_client(url, key)
else:
    print("Credenciais do Supabase não encontradas. O cliente não foi inicializado.")

