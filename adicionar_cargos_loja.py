# Script para adicionar entrega de cargos na loja.py

arquivo = "/data/data/com.termux/files/home/cogs/loja.py"

with open(arquivo, 'r', encoding='utf-8') as f:
    conteudo = f.read()

# Adicionar após "pago = True"
adicionar = '''
            # Entregar cargos automático
            cargos_ids = produto.get("cargos_id", [])
            if cargos_ids:
                for cargo_id in cargos_ids:
                    try:
                        cargo = guild.get_role(cargo_id)
                        if cargo:
                            await comprador.add_roles(cargo, reason=f"Compra de {produto['nome']}")
                    except:
                        pass
'''

conteudo = conteudo.replace(
    "            pago = True",
    "            pago = True" + adicionar
)

with open(arquivo, 'w', encoding='utf-8') as f:
    f.write(conteudo)

print("✅ Cargos automáticos adicionados!")
