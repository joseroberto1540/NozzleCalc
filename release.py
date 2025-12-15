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

    # --- CAMINHO ATUALIZADO PARA A NOVA ARQUITETURA ---
    target_file = os.path.join("src", "config.py")
    
    print(f"\n1. Atualizando {target_file} para {new_version}...")
    
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # MELHORIA: Regex mais flexível com espaços (\s*)
        # Encontra: CURRENT_VERSION = "..." (com qualquer espaçamento no igual)
        new_content = re.sub(
            r'CURRENT_VERSION\s*=\s*".*?"', 
            f'CURRENT_VERSION = "{new_version}"', 
            content
        )
        
        # Verifica se houve mudança (segurança para saber se o regex funcionou)
        if content == new_content:
            print("⚠️ AVISO: A versão não parece ter sido alterada no arquivo. Verifique o formato em src/config.py.")
        
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)
            
    except FileNotFoundError:
        print(f"ERRO CRÍTICO: O arquivo {target_file} não foi encontrado!")
        print("Verifique se a pasta 'src' existe e se o 'config.py' está dentro dela.")
        return

    print("\n2. Executando comandos Git...")
    
    commands = [
        "git add .",  # Adiciona as novas pastas (core, ui, solvers)
        f'git commit -m "Release {tag_name} - Refactor & Update"',
        "git push origin main --force", # CUIDADO: Force push reescreve histórico
        f"git tag {tag_name}",
        f"git push origin {tag_name}"   # Dispara o GitHub Actions
    ]

    for cmd in commands:
        print(f"> {cmd}")
        result = os.system(cmd)
        
        # Lógica de erro
        if result != 0:
            if "commit" in cmd:
                print("⚠️ Aviso: Nada para commitar (talvez apenas a tag mudou?). Continuando...")
            else:
                print(f"❌ ERRO ao executar: {cmd}")
                print("Interrompendo script para evitar inconsistências.")
                return

    print(f"\n✅ SUCESSO! A versão {tag_name} foi enviada.")
    print("Monitore o GitHub Actions para ver o build do executável.")

if __name__ == "__main__":
    release_new_version()