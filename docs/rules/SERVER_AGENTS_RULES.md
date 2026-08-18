# Regras de Execução — Agentes no Servidor Central

## Agentes
Supervisor, Architect, Coder, Reviewer, Debugger, Researcher, Security

## Contrato JSON
```json
{"action": "list_dir|read_file|write_file|apply_patch|run_cmd|lint_python|finish", "args": {}}
```

## Restrições
- Workspace `/workspace` (sandbox)
- Shell desabilitado por padrão
- write_file/run_cmd exigem aprovação quando configurado
- Comandos proibidos: rm -rf /, mkfs, dd, shutdown, reboot

## Tokens
Toda chamada ao LLM 14B consome tokens do tenant.
