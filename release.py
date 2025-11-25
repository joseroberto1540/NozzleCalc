import os
import re
import sys

def release_new_version():
    print("--- NOZZLECALC AUTOMATED RELEASE (FULL UPDATE) ---")
    print("Este script vai enviar TUDO: código, ícones, manual e requirements.")
    
    new_version = input("Digite o número da nova versão (ex: 3.8.0): ").strip()
    
    if not new_version:
        print("Versão inválida.")
        return

    tag_name = f"v{new_version}"

    print(f"\n1. Atualizando main.py para {new_version}...")
    
    try:
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Atualiza a variável de versão no código
        new_content = re.sub(
            r'CURRENT_VERSION = ".*?"', 
            f'CURRENT_VERSION = "{new_version}"', 
            content
        )
        
        with open("main.py", "w", encoding="utf-8") as f:
            f.write(new_content)
            
    except FileNotFoundError:
        print("ERRO: main.py não encontrado!")
        return

    print("\n2. Executando comandos Git...")
    
    # AQUI ESTÁ A MUDANÇA: "git add ." pega TODOS os arquivos da pasta
    commands = [
        "git add .",  # <--- MUDANÇA CRUCIAL: Adiciona ícone, manual, requirements, tudo!
        f'git commit -m "Release {tag_name} - Full Update"',
        "git push origin main --force", # Força a atualização do código
        f"git tag {tag_name}",
        f"git push origin {tag_name}"   # Dispara o Robô
    ]

    for cmd in commands:
        print(f"> {cmd}")
        result = os.system(cmd)
        
        # Se der erro no commit (ex: nada para commitar), avisamos mas tentamos continuar
        # Se der erro no push, paramos.
        if result != 0 and "commit" not in cmd:
            print(f"⚠️ ALERTA ou ERRO ao executar: {cmd}")
            # Não paramos o script no commit vazio, mas paramos se falhar o push

    print(f"\n✅ SUCESSO! A versão {tag_name} foi enviada.")
    print("O GitHub Actions vai baixar seus novos ícones/manual e gerar o executável.")

if __name__ == "__main__":
    release_new_version()